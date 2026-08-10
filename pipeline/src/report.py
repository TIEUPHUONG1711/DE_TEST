"""Answer the four business questions from the clean dataset."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def load_inputs(
    parquet_path: Path, quality_report_path: Path
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load the clean dataset and its cleaning statistics."""
    dataframe = pd.read_parquet(parquet_path)
    quality_report = json.loads(
        quality_report_path.read_text(encoding="utf-8")
    )
    return dataframe, quality_report


#Service nào có nhiều lỗi (level=ERROR) nhất trong 7 ngày?
def analyze_errors_by_service(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Answer which service has the most ERROR records."""
    counts = (
        dataframe.loc[dataframe["level"].eq("ERROR")]
        .groupby("service")
        .size()
        .sort_values(ascending=False)
    )
    ranking = [
        {"service": str(service), "error_count": int(count)}
        for service, count in counts.items()
    ]
    return {
        "service_with_most_errors": ranking[0]["service"],
        "error_count": ranking[0]["error_count"],
        "service_ranking": ranking,
    }

#Số lượng lỗi theo ngày của toàn hệ thống — ngày nào bất thường?
def analyze_daily_errors(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Count ERROR records by UTC date and detect IQR outliers."""
    counts = (
        dataframe.loc[dataframe["level"].eq("ERROR")]
        .groupby("event_date")
        .size()
        .sort_index()
    )

    q1 = float(counts.quantile(0.25))
    q3 = float(counts.quantile(0.75))
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    anomalies = counts[(counts < lower_bound) | (counts > upper_bound)]

    return {
        "daily_error_counts": {
            str(date): int(count) for date, count in counts.items()
        },
        "anomaly_method": "IQR",
        "iqr_details": {
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
        },
        "anomalies": [
            {"date": str(date), "error_count": int(count)}
            for date, count in anomalies.items()
        ],
        "limitation": (
            "Only seven days are available; production anomaly detection "
            "needs a longer baseline and seasonality checks."
        ),
    }

#Top 3 loại lỗi (message/error code) phổ biến nhất, thuộc service nào?
def analyze_top_error_types(dataframe: pd.DataFrame) -> dict[str, Any]:
    """Return the three most common error type and service pairs."""
    top_three = (
        dataframe.loc[dataframe["level"].eq("ERROR")]
        .groupby(["error_type", "service"])
        .size()
        .sort_values(ascending=False)
        .head(3)
    )
    return {
        "top_error_types": [
            {
                "error_type": str(error_type),
                "service": str(service),
                "error_count": int(count),
            }
            for (error_type, service), count in top_three.items()
        ]
    }

#Có bao nhiêu bản ghi bị loại/sửa trong bước làm sạch, thuộc những loại vấn đề gì?
def get_cleaning_statistics(
    quality_report: dict[str, Any],
) -> dict[str, Any]:
    """Use the quality report as the single source of cleaning metrics."""
    return {
        "raw_records": quality_report["raw_record_count"],
        "clean_records": quality_report["clean_record_count"],
        "dropped_records": quality_report["dropped_record_count"],
        "fixed_records": quality_report["fixed_record_count"],
        "rejection_breakdown": quality_report["rejection_breakdown"],
        "fix_breakdown": quality_report["fix_breakdown"],
        "accounting_check": quality_report["accounting_check"],
    }


def generate_report(
    dataframe: pd.DataFrame, quality_report: dict[str, Any]
) -> dict[str, Any]:
    """Generate all answers and verify independent ERROR totals agree."""
    question_1 = analyze_errors_by_service(dataframe)
    question_2 = analyze_daily_errors(dataframe)

    service_total = sum(
        item["error_count"] for item in question_1["service_ranking"]
    )
    daily_total = sum(question_2["daily_error_counts"].values())
    if service_total != daily_total:
        raise ValueError("ERROR totals by service and by date do not match.")

    return {
        "question_1": question_1,
        "question_2": question_2,
        "question_3": analyze_top_error_types(dataframe),
        "question_4": get_cleaning_statistics(quality_report),
        "verification": {
            "total_error_records": service_total,
            "service_total_matches_daily_total": True,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_report(report: dict[str, Any], output_path: Path) -> None:
    """Write the report as readable JSON and verify it can be read back."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    json.loads(output_path.read_text(encoding="utf-8"))


def main() -> None:
    parquet_path = Path("pipeline/output/cleaned_logs.parquet")
    quality_report_path = Path("pipeline/results/data_quality_report.json")
    output_path = Path("pipeline/results/analysis_results.json")

    dataframe, quality_report = load_inputs(parquet_path, quality_report_path)
    report = generate_report(dataframe, quality_report)
    save_report(report, output_path)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nAnalysis report written: {output_path}")


if __name__ == "__main__":
    main()
