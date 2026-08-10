"""Focused tests for the three pipeline steps."""

import json
import sys
from pathlib import Path

import pytest
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "src"))

from pipeline import (
    extract_error_fields,
    ingest_jsonl,
    profile_records,
    transform_and_save,
    validate_and_clean,
)


def test_ingest_keeps_good_lines_after_malformed_json(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.jsonl"
    input_path.write_text(
        '\n'.join([
            json.dumps({"message": "first"}),
            '{"message": "truncated',
            json.dumps({"message": "third"}),
        ]),
        encoding="utf-8",
    )

    records, errors, raw_count = ingest_jsonl(input_path)

    assert raw_count == 3
    assert len(records) == 2
    assert len(errors) == 1
    assert errors[0]["issue"] == "malformed_json"
    assert records[1]["source_line_number"] == 3


@pytest.mark.parametrize(
    ("content", "expected_issue"),
    [("\n", "empty_line"), ('["not", "an", "object"]', "invalid_json_type")],
)
def test_ingest_reports_other_invalid_lines(
    tmp_path: Path, content: str, expected_issue: str
) -> None:
    input_path = tmp_path / "invalid.jsonl"
    input_path.write_text(content, encoding="utf-8")

    records, errors, _ = ingest_jsonl(input_path)

    assert records == []
    assert errors[0]["issue"] == expected_issue


def test_ingest_raises_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ingest_jsonl(tmp_path / "missing.jsonl")


def test_profile_reports_main_quality_metrics(tmp_path: Path) -> None:
    input_path = tmp_path / "profile.jsonl"
    input_path.write_text("fixture", encoding="utf-8")
    records = [
        {
            "timestamp": "2026-07-27T00:00:00Z",
            "service": "auth-service",
            "level": "INFO",
            "message": "Heartbeat ok",
            "request_id": "req-1",
            "trace_id": "trace-1",
            "source_line_number": 1,
        },
        {
            "timestamp": "2026-07-27T00:00:00Z",
            "service": "auth-service",
            "level": "INFO",
            "message": "Heartbeat ok",
            "request_id": "req-1",
            "trace_id": "trace-1",
            "source_line_number": 2,
        },
        {
            "timestamp": "not-a-date",
            "service": "payment-api",
            "message": "Heartbeat ok",
            "request_id": "req-2",
            "source_line_number": 3,
        },
    ]

    profile = profile_records(records, [], 3, input_path)

    assert profile["parsed_record_count"] == 3
    assert profile["exact_duplicate_count"] == 1
    assert profile["invalid_timestamp_count"] == 1
    assert profile["missing_by_field"]["level"] == 1
    assert profile["trace_id_presence"] == {"present": 2, "missing": 1}


def test_validate_and_clean_applies_all_core_rules() -> None:
    valid = {
        "timestamp": "2026-07-27T00:00:00Z",
        "service": "auth-service",
        "level": "INFO",
        "message": "Session created",
        "request_id": "req-1",
        "source_line_number": 1,
    }
    records = [
        valid,
        {**valid, "source_line_number": 2},
        {
            "timestamp": "not-a-date",
            "service": "payment-api",
            "level": "ERROR",
            "message": "ERR ConnTimeout",
            "request_id": "req-2",
            "source_line_number": 3,
        },
        {
            "timestamp": "2026-07-27T01:00:00Z",
            "service": "auth-service",
            "message": "Heartbeat ok",
            "request_id": "req-3",
            "source_line_number": 4,
        },
    ]
    parse_errors = [{"source_line_number": 5, "issue": "malformed_json"}]

    cleaned, report = validate_and_clean(records, parse_errors, raw_line_count=5)

    assert len(cleaned) == 2
    assert cleaned[1]["level"] == "INFO"
    assert report["clean_record_count"] == 2
    assert report["dropped_record_count"] == 3
    assert report["fixed_record_count"] == 1
    assert report["rejection_breakdown"] == {
        "exact_duplicate": 1,
        "invalid_timestamp": 1,
        "malformed_json": 1,
    }
    assert report["accounting_check"]["passed"] is True


def test_cleaning_does_not_modify_source_record() -> None:
    source = {
        "timestamp": " 2026-07-27T00:00:00Z ",
        "service": " AUTH-SERVICE ",
        "message": " Heartbeat ok ",
        "request_id": " req-1 ",
        "source_line_number": 1,
    }

    cleaned, report = validate_and_clean([source], [], raw_line_count=1)

    assert source["service"] == " AUTH-SERVICE "
    assert "level" not in source
    assert cleaned[0]["service"] == "auth-service"
    assert cleaned[0]["level"] == "INFO"
    assert report["fixed_record_count"] == 1


@pytest.mark.parametrize(
    ("message", "level", "expected"),
    [
        ("ERR HTTP 502 upstream=payment-api", "ERROR", ("HTTP 502", "502")),
        ("ERR PaymentDeclined txn=t1 code=51", "ERROR", ("PaymentDeclined", "51")),
        ("Session created", "INFO", (None, None)),
    ],
)
def test_extract_error_fields(
    message: str, level: str, expected: tuple[str | None, str | None]
) -> None:
    assert extract_error_fields(message, level) == expected


def test_transform_writes_readable_parquet(tmp_path: Path) -> None:
    cleaned_records = [
        {
            "timestamp": "2026-07-27T07:00:00+07:00",
            "service": "payment-api",
            "level": "ERROR",
            "message": "ERR PaymentDeclined txn=t1 code=51",
            "request_id": "req-1",
            "trace_id": None,
            "source_line_number": 1,
        },
        {
            "timestamp": "2026-07-27T01:00:00Z",
            "service": "auth-service",
            "level": "INFO",
            "message": "Session created",
            "request_id": "req-2",
            "trace_id": "trace-2",
            "source_line_number": 2,
        },
    ]
    output_path = tmp_path / "cleaned.parquet"

    dataframe = transform_and_save(cleaned_records, output_path)

    assert output_path.is_file()
    assert len(dataframe) == 2
    assert str(dataframe["timestamp"].dtype) == "datetime64[ns, UTC]"
    assert dataframe.loc[0, "event_date"].isoformat() == "2026-07-27"
    assert dataframe.loc[0, "error_type"] == "PaymentDeclined"
    assert dataframe.loc[0, "error_code"] == "51"
    assert pd.isna(dataframe.loc[1, "error_type"])
