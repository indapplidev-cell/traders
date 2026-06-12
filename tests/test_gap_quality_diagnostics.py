import json

from app.diagnostics.gap_quality_diagnostics import GapQualityDiagnostics


def test_gap_quality_diagnostics_ok_when_no_gaps() -> None:
    payload = GapQualityDiagnostics().analyze(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        end_date="2025-01-10",
        gap_count=0,
    )

    assert payload["gap_severity"] == "OK"
    assert payload["dataset_safe_for_training"] is True
    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_gap_quality_diagnostics_small_gap_is_minor_or_moderate() -> None:
    payload = GapQualityDiagnostics().analyze(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        end_date="2025-01-10",
        gap_count=2,
        missing_open_times=[
            "2025-01-03T10:00:00+00:00",
            "2025-01-03T10:15:00+00:00",
        ],
    )

    assert payload["gap_severity"] in {"MINOR", "MODERATE"}
    assert payload["largest_gap_minutes"] >= 15


def test_gap_quality_diagnostics_marks_79_gaps_as_not_clean() -> None:
    payload = GapQualityDiagnostics().analyze(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        end_date="2026-06-12",
        gap_count=79,
    )

    assert payload["gap_severity"] in {"HIGH", "MODERATE"}
    assert payload["dataset_safe_for_training"] is False or "gap_quality_not_clean" in payload["warnings"]


def test_gap_quality_diagnostics_large_gap_becomes_high_or_critical() -> None:
    payload = GapQualityDiagnostics().analyze(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        end_date="2025-01-10",
        gap_count=120,
        missing_open_times=[
            f"2025-01-05T{hour:02d}:{minute:02d}:00+00:00"
            for hour in range(0, 12)
            for minute in (0, 15, 30, 45)
        ],
    )

    assert payload["gap_severity"] in {"HIGH", "CRITICAL"}
    assert payload["largest_gap_minutes"] >= 180
