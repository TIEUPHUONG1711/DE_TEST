"""Focused tests for the four business report answers."""

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "src"))

from report import (
    analyze_daily_errors,
    analyze_errors_by_service,
    analyze_top_error_types,
    generate_report,
    save_report,
)


def test_service_and_top_error_analysis() -> None:
    dataframe = pd.DataFrame(
        [
            {"level": "ERROR", "service": "payment-api", "error_type": "ConnTimeout"},
            {"level": "ERROR", "service": "payment-api", "error_type": "ConnTimeout"},
            {"level": "ERROR", "service": "web-portal", "error_type": "HTTP 502"},
            {"level": "INFO", "service": "auth-service", "error_type": None},
        ]
    )

    service_result = analyze_errors_by_service(dataframe)
    top_result = analyze_top_error_types(dataframe)

    assert service_result["service_with_most_errors"] == "payment-api"
    assert service_result["error_count"] == 2
    assert top_result["top_error_types"][0] == {
        "error_type": "ConnTimeout",
        "service": "payment-api",
        "error_count": 2,
    }


def test_iqr_detects_daily_error_spike() -> None:
    daily_counts = [2, 2, 2, 2, 2, 3, 20]
    rows = []
    for day_number, count in enumerate(daily_counts, start=1):
        rows.extend(
            {
                "level": "ERROR",
                "event_date": date(2026, 7, day_number),
            }
            for _ in range(count)
        )
    dataframe = pd.DataFrame(rows)

    result = analyze_daily_errors(dataframe)

    assert result["anomaly_method"] == "IQR"
    assert result["anomalies"] == [
        {"date": "2026-07-07", "error_count": 20}
    ]


def test_generate_and_save_report(tmp_path: Path) -> None:
    dataframe = pd.DataFrame(
        [
            {
                "level": "ERROR",
                "service": "payment-api",
                "event_date": date(2026, 7, 27),
                "error_type": "ConnTimeout",
            }
        ]
    )
    quality_report = {
        "raw_record_count": 2,
        "clean_record_count": 1,
        "dropped_record_count": 1,
        "fixed_record_count": 0,
        "rejection_breakdown": {"malformed_json": 1},
        "fix_breakdown": {},
        "accounting_check": {"expected_raw_count": 2, "passed": True},
    }
    output_path = tmp_path / "analysis.json"

    report = generate_report(dataframe, quality_report)
    save_report(report, output_path)
    saved_report = json.loads(output_path.read_text(encoding="utf-8"))

    assert saved_report["verification"]["total_error_records"] == 1
    assert saved_report["question_4"]["dropped_records"] == 1
