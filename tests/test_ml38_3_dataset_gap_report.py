from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.diagnostics.dataset_gap_report import DatasetGapReportBuilder


def _candle(open_time: datetime) -> SimpleNamespace:
    return SimpleNamespace(open_time=open_time)


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2025, 1, 1, hour, minute, tzinfo=timezone.utc)


def test_clean_15m_candles_have_no_training_gaps() -> None:
    candles = [_candle(_dt(0, 0)), _candle(_dt(0, 15)), _candle(_dt(0, 30)), _candle(_dt(0, 45))]

    payload = DatasetGapReportBuilder().build(
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        start_at=_dt(0, 0),
        end_at=_dt(1, 0),
        start_date="2025-01-01",
        end_date="2025-01-01",
    )

    assert payload["effective_gap_count_for_training"] == 0
    assert payload["gap_severity_for_training"] == "OK"
    assert payload["training_safe"] is True
    assert payload["root_cause_hint"] == "clean"


def test_one_internal_missing_candle_is_reported() -> None:
    candles = [_candle(_dt(0, 0)), _candle(_dt(0, 15)), _candle(_dt(0, 45))]

    payload = DatasetGapReportBuilder().build(
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        start_at=_dt(0, 0),
        end_at=_dt(1, 0),
        start_date="2025-01-01",
        end_date="2025-01-01",
    )

    assert payload["internal_missing_candle_count"] == 1
    assert payload["effective_gap_count_for_training"] == 1
    assert payload["gap_ranges"][0]["missing_slots"] == 1
    assert payload["root_cause_hint"] == "internal_missing_candles"


def test_two_contiguous_missing_candles_are_grouped() -> None:
    candles = [_candle(_dt(0, 0)), _candle(_dt(0, 45))]

    payload = DatasetGapReportBuilder().build(
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        start_at=_dt(0, 0),
        end_at=_dt(1, 0),
        start_date="2025-01-01",
        end_date="2025-01-01",
    )

    assert payload["internal_missing_candle_count"] == 2
    assert payload["gap_ranges"][0]["missing_slots"] == 2
    assert payload["largest_gap_minutes"] == 30


def test_duplicate_timestamp_is_reported() -> None:
    candles = [_candle(_dt(0, 0)), _candle(_dt(0, 0)), _candle(_dt(0, 15)), _candle(_dt(0, 30)), _candle(_dt(0, 45))]

    payload = DatasetGapReportBuilder().build(
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        start_at=_dt(0, 0),
        end_at=_dt(1, 0),
        start_date="2025-01-01",
        end_date="2025-01-01",
    )

    assert payload["duplicate_candle_count"] == 1


def test_out_of_order_input_is_reported_but_sorted_for_gap_ranges() -> None:
    candles = [_candle(_dt(0, 15)), _candle(_dt(0, 0)), _candle(_dt(0, 30)), _candle(_dt(0, 45))]

    payload = DatasetGapReportBuilder().build(
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        start_at=_dt(0, 0),
        end_at=_dt(1, 0),
        start_date="2025-01-01",
        end_date="2025-01-01",
    )

    assert payload["out_of_order_count"] == 1
    assert payload["effective_gap_count_for_training"] == 0


def test_trailing_incomplete_current_day_is_not_training_gap() -> None:
    candles = [_candle(_dt(0, 0)), _candle(_dt(0, 15))]

    payload = DatasetGapReportBuilder().build(
        candles=candles,
        symbol="BTCUSDT",
        interval="15m",
        start_at=_dt(0, 0),
        end_at=_dt(1, 0),
        start_date="2025-01-01",
        end_date="2025-01-01",
    )

    assert payload["trailing_incomplete_count"] == 2
    assert payload["effective_gap_count_for_training"] == 0
    assert payload["training_safe"] is True
