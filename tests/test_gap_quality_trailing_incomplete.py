import json

from app.diagnostics.gap_quality_diagnostics import GapQualityDiagnostics


def test_trailing_incomplete_current_day_gaps_are_excluded_from_training_gap_count() -> None:
    missing_open_times = [
        f"2026-06-12T{hour:02d}:{minute:02d}:00+00:00"
        for hour in range(12, 24)
        for minute in (0, 15, 30, 45)
    ]

    payload = GapQualityDiagnostics().analyze(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        end_date="2026-06-12",
        gap_count=len(missing_open_times),
        missing_open_times=missing_open_times,
        last_open_time="2026-06-12T11:45:00+00:00",
    )

    assert payload["real_gap_count"] == 0
    assert payload["trailing_incomplete_count"] == len(missing_open_times)
    assert payload["effective_gap_count_for_training"] == 0
    assert payload["gap_severity_for_training"] in {"OK", "MINOR"}
    assert payload["dataset_safe_for_training"] is True
    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_historical_gaps_are_not_hidden_by_trailing_incomplete_range_detection() -> None:
    historical_missing = [
        "2026-06-10T02:00:00+00:00",
        "2026-06-10T02:15:00+00:00",
        "2026-06-10T02:30:00+00:00",
        "2026-06-10T02:45:00+00:00",
        "2026-06-10T03:00:00+00:00",
        "2026-06-10T03:15:00+00:00",
        "2026-06-10T03:30:00+00:00",
        "2026-06-10T03:45:00+00:00",
        "2026-06-10T04:00:00+00:00",
        "2026-06-10T04:15:00+00:00",
    ]
    trailing_missing = [
        f"2026-06-12T{hour:02d}:{minute:02d}:00+00:00"
        for hour in range(12, 24)
        for minute in (0, 15, 30, 45)
    ]
    payload = GapQualityDiagnostics().analyze(
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        end_date="2026-06-12",
        gap_count=len(historical_missing) + len(trailing_missing),
        missing_open_times=historical_missing + trailing_missing,
        last_open_time="2026-06-12T11:45:00+00:00",
    )

    assert payload["real_gap_count"] == len(historical_missing)
    assert payload["trailing_incomplete_count"] == len(trailing_missing)
    assert payload["effective_gap_count_for_training"] == len(historical_missing)
    assert payload["gap_severity_for_training"] in {"MODERATE", "HIGH"}
    json.dumps(payload, ensure_ascii=False, sort_keys=True)
