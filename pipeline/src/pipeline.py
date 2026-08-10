"""Local pipeline: ingest, profile, validate, and clean JSONL logs."""

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_FIELDS = ("timestamp", "service", "level", "message", "request_id")
ALL_FIELDS = REQUIRED_FIELDS + ("trace_id",)
VALID_SERVICES = {
    "auth-service",
    "payment-api",
    "web-portal",
    "batch-report",
    "notification-worker",
}
VALID_LEVELS = {"INFO", "WARN", "ERROR"}


def calculate_sha256(path: Path) -> str:
    """Return a checksum that identifies the exact input file."""
    checksum = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def ingest_jsonl(
    input_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """Read JSONL line by line and keep malformed lines as parse errors."""
    records: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    raw_line_count = 0

    with input_path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            raw_line_count += 1
            text = raw_line.strip()

            if not text:
                parse_errors.append(
                    {"source_line_number": line_number, "issue": "empty_line"}
                )
                continue

            try:
                record = json.loads(text)
            except json.JSONDecodeError as error:
                parse_errors.append(
                    {
                        "source_line_number": line_number,
                        "issue": "malformed_json",
                        "detail": error.msg,
                    }
                )
                continue

            if not isinstance(record, dict):
                parse_errors.append(
                    {
                        "source_line_number": line_number,
                        "issue": "invalid_json_type",
                    }
                )
                continue

            record["source_line_number"] = line_number
            records.append(record)

    return records, parse_errors, raw_line_count


def _missing_mask(series: pd.Series) -> pd.Series:
    """Return True for null, empty, or whitespace-only values."""
    return (
        series.isna()
        | series.astype("string").str.strip().eq("").fillna(False)
    )


def profile_records(
    records: list[dict[str, Any]],
    parse_errors: list[dict[str, Any]],
    raw_line_count: int,
    input_path: Path,
) -> dict[str, Any]:
    """Describe the parsed data without changing or removing records."""
    dataframe = pd.DataFrame(records).drop(
        columns=["source_line_number"], errors="ignore"
    )

    missing_by_field = {}
    for field in ALL_FIELDS:
        if field in dataframe:
            missing_by_field[field] = int(_missing_mask(dataframe[field]).sum())
        else:
            missing_by_field[field] = len(dataframe)

    timestamps = pd.to_datetime(
        dataframe["timestamp"], format="mixed", errors="coerce", utc=True
    )
    valid_timestamps = timestamps.dropna()
    records_by_date = (
        valid_timestamps.dt.strftime("%Y-%m-%d")
        .value_counts()
        .sort_index()
        .to_dict()
    )

    level_counts = (
        dataframe["level"].fillna("<MISSING>").value_counts().to_dict()
    )
    service_counts = dataframe["service"].value_counts().to_dict()
    top_messages = dataframe["message"].value_counts().head(10).to_dict()
    top_error_messages = (
        dataframe.loc[dataframe["level"].eq("ERROR"), "message"]
        .value_counts()
        .head(10)
        .to_dict()
    )

    return {
        "input_file": input_path.as_posix(),
        "input_sha256": calculate_sha256(input_path),
        "raw_line_count": raw_line_count,
        "parsed_record_count": len(dataframe),
        "parse_error_count": len(parse_errors),
        "columns": dataframe.columns.tolist(),
        "data_types": {name: str(dtype) for name, dtype in dataframe.dtypes.items()},
        "missing_by_field": missing_by_field,
        "service_counts": {str(k): int(v) for k, v in service_counts.items()},
        "level_counts": {str(k): int(v) for k, v in level_counts.items()},
        "exact_duplicate_count": int(dataframe.duplicated().sum()),
        "invalid_timestamp_count": int(timestamps.isna().sum()),
        "timestamp_range_utc": {
            "minimum": valid_timestamps.min().isoformat(),
            "maximum": valid_timestamps.max().isoformat(),
        },
        "records_by_utc_date": {
            str(k): int(v) for k, v in records_by_date.items()
        },
        "trace_id_presence": {
            "present": len(dataframe) - missing_by_field["trace_id"],
            "missing": missing_by_field["trace_id"],
        },
        "top_messages": {str(k): int(v) for k, v in top_messages.items()},
        "top_error_messages": {
            str(k): int(v) for k, v in top_error_messages.items()
        },
    }


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _duplicate_key(record: dict[str, Any]) -> str:
    """Create a stable key without the internal source line number."""
    source_fields = {
        key: value for key, value in record.items() if key != "source_line_number"
    }
    return json.dumps(source_fields, sort_keys=True, ensure_ascii=False)


def validate_and_clean(
    records: list[dict[str, Any]],
    parse_errors: list[dict[str, Any]],
    raw_line_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply the documented Fix/Drop/Keep rules in one readable pass."""
    cleaned_records: list[dict[str, Any]] = []
    rejected_samples: list[dict[str, Any]] = []
    fixed_samples: list[dict[str, Any]] = []
    fixed_line_numbers: set[int] = set()
    rejection_counts = Counter(error["issue"] for error in parse_errors)
    fix_counts: Counter[str] = Counter()
    seen: set[str] = set()

    rejected_samples.extend(parse_errors[:5])

    for source_record in records:
        line_number = source_record["source_line_number"]
        duplicate_key = _duplicate_key(source_record)

        if duplicate_key in seen:
            rejection_counts["exact_duplicate"] += 1
            if len(rejected_samples) < 5:
                rejected_samples.append(
                    {"source_line_number": line_number, "issue": "exact_duplicate"}
                )
            continue
        seen.add(duplicate_key)

        record = source_record.copy()
        fixes: list[str] = []

        # Trim text safely. This does not change its meaning.
        for field in ALL_FIELDS:
            if isinstance(record.get(field), str):
                stripped = record[field].strip()
                if stripped != record[field]:
                    fixes.append(f"trim_{field}")
                record[field] = stripped

        # A successful heartbeat with a missing level is treated as INFO.
        if _is_missing(record.get("level")) and record.get("message") == "Heartbeat ok":
            record["level"] = "INFO"
            fixes.append("missing_level_to_info")

        # Required fields must be non-empty strings after the safe fix above.
        invalid_required_field = next(
            (
                field
                for field in REQUIRED_FIELDS
                if _is_missing(record.get(field))
                or not isinstance(record.get(field), str)
            ),
            None,
        )
        if invalid_required_field:
            reason = f"invalid_{invalid_required_field}"
            rejection_counts[reason] += 1
            if len(rejected_samples) < 5:
                rejected_samples.append(
                    {"source_line_number": line_number, "issue": reason}
                )
            continue

        # Timestamp must be ISO-8601 and include Z or an explicit UTC offset.
        try:
            parsed_timestamp = datetime.fromisoformat(
                record["timestamp"].replace("Z", "+00:00")
            )
            timestamp_is_valid = (
                parsed_timestamp.tzinfo is not None
                and parsed_timestamp.utcoffset() is not None
            )
        except ValueError:
            timestamp_is_valid = False

        if not timestamp_is_valid:
            rejection_counts["invalid_timestamp"] += 1
            if len(rejected_samples) < 5:
                rejected_samples.append(
                    {"source_line_number": line_number, "issue": "invalid_timestamp"}
                )
            continue

        # Normalize known categorical values, then validate them.
        normalized_service = record["service"].lower()
        normalized_level = record["level"].upper()
        if normalized_service != record["service"]:
            fixes.append("normalize_service")
        if normalized_level != record["level"]:
            fixes.append("normalize_level")
        record["service"] = normalized_service
        record["level"] = normalized_level

        if record["service"] not in VALID_SERVICES:
            rejection_counts["invalid_service"] += 1
            continue
        if record["level"] not in VALID_LEVELS:
            rejection_counts["invalid_level"] += 1
            continue

        # trace_id is optional; missing or non-string values become null.
        if _is_missing(record.get("trace_id")):
            record["trace_id"] = None
        elif not isinstance(record["trace_id"], str):
            record["trace_id"] = None
            fixes.append("invalid_trace_id_to_null")

        cleaned_records.append(record)
        if fixes:
            fixed_line_numbers.add(line_number)
            fix_counts.update(fixes)
            if len(fixed_samples) < 5:
                fixed_samples.append(
                    {"source_line_number": line_number, "fixes": fixes}
                )

    dropped_count = sum(rejection_counts.values())
    fixed_record_count = len(fixed_line_numbers)

    report = {
        "raw_record_count": raw_line_count,
        "clean_record_count": len(cleaned_records),
        "dropped_record_count": dropped_count,
        "fixed_record_count": fixed_record_count,
        "unchanged_record_count": len(cleaned_records) - fixed_record_count,
        "rejection_breakdown": dict(sorted(rejection_counts.items())),
        "fix_breakdown": dict(sorted(fix_counts.items())),
        "accounting_check": {
            "expected_raw_count": len(cleaned_records) + dropped_count,
            "passed": raw_line_count == len(cleaned_records) + dropped_count,
        },
        "rejected_samples": rejected_samples,
        "fixed_samples": fixed_samples,
    }
    return cleaned_records, report


def extract_error_fields(message: str, level: str) -> tuple[str | None, str | None]:
    """Extract a stable error type and optional code from an ERROR message."""
    if level != "ERROR":
        return None, None

    type_match = re.match(r"^ERR\s+(HTTP\s+\d+|[A-Za-z]+)", message)
    error_type = type_match.group(1) if type_match else "UNKNOWN"

    code_match = re.search(r"\bcode=([A-Za-z0-9_-]+)", message)
    if code_match:
        error_code = code_match.group(1)
    elif error_type.startswith("HTTP "):
        error_code = error_type.split()[1]
    else:
        error_code = None

    return error_type, error_code


def transform_and_save(
    cleaned_records: list[dict[str, Any]], output_path: Path
) -> pd.DataFrame:
    """Normalize the clean schema, write Parquet, and verify it can be read."""
    dataframe = pd.DataFrame(cleaned_records)

    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], utc=True)
    dataframe["event_date"] = dataframe["timestamp"].dt.date

    error_fields = [
        extract_error_fields(message, level)
        for message, level in zip(dataframe["message"], dataframe["level"])
    ]
    dataframe["error_type"] = pd.Series(
        [value[0] for value in error_fields], dtype="string"
    )
    dataframe["error_code"] = pd.Series(
        [value[1] for value in error_fields], dtype="string"
    )

    for field in ("service", "level", "message", "request_id", "trace_id"):
        dataframe[field] = dataframe[field].astype("string")
    dataframe["source_line_number"] = dataframe["source_line_number"].astype("int64")

    column_order = [
        "timestamp",
        "event_date",
        "service",
        "level",
        "message",
        "request_id",
        "trace_id",
        "error_type",
        "error_code",
        "source_line_number",
    ]
    dataframe = dataframe[column_order]

    if dataframe["timestamp"].isna().any():
        raise ValueError("Clean data still contains invalid timestamps.")
    duplicate_columns = [
        column for column in column_order if column != "source_line_number"
    ]
    if dataframe.duplicated(subset=duplicate_columns).any():
        raise ValueError("Clean data still contains duplicate records.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_parquet(output_path, index=False, engine="pyarrow")

    saved_dataframe = pd.read_parquet(output_path, engine="pyarrow")
    if len(saved_dataframe) != len(dataframe):
        raise ValueError("Parquet row count does not match the clean dataset.")

    return dataframe


def save_json(data: dict[str, Any], output_path: Path) -> None:
    """Write a dictionary as readable UTF-8 JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    input_path = Path("data/app_logs_7days.jsonl")
    output_path = Path("pipeline/output/cleaned_logs.parquet")
    quality_report_path = Path("pipeline/results/data_quality_report.json")
    records, parse_errors, raw_line_count = ingest_jsonl(input_path)
    profile = profile_records(records, parse_errors, raw_line_count, input_path)
    cleaned_records, quality_report = validate_and_clean(
        records, parse_errors, raw_line_count
    )
    quality_report.update(
        {
            "input_file": input_path.as_posix(),
            "input_sha256": profile["input_sha256"],
            "parsed_record_count": len(records),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    save_json(quality_report, quality_report_path)
    transformed_data = transform_and_save(cleaned_records, output_path)

    print("Profiling result:")
    print(json.dumps(profile, indent=2, ensure_ascii=False))
    print("\nCleaning result:")
    print(json.dumps(quality_report, indent=2, ensure_ascii=False))
    print(f"\nParquet written: {output_path}")
    print(f"Quality report written: {quality_report_path}")
    print(f"Rows: {len(transformed_data)}, columns: {len(transformed_data.columns)}")


if __name__ == "__main__":
    main()
