from datetime import datetime, timezone

from app.data.candle_gap_checker import CandleGapChecker


def test_candle_gap_checker_accepts_continuous_series() -> None:
    checker = CandleGapChecker()
    candles = [
        {"open_time": datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)},
        {"open_time": datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc)},
        {"open_time": datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc)},
    ]

    result = checker.check(
        candles=candles,
        interval="15m",
        start_at=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        end_at=datetime(2025, 1, 1, 0, 45, tzinfo=timezone.utc),
        symbol="BTCUSDT",
    )

    assert result["is_valid"] is True
    assert result["gap_count"] == 0
    assert result["duplicate_count"] == 0
    assert result["misaligned_count"] == 0


def test_candle_gap_checker_detects_gaps_duplicates_and_misalignment() -> None:
    checker = CandleGapChecker()
    candles = [
        {"open_time": datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)},
        {"open_time": datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc)},
        {"open_time": datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc)},
        {"open_time": datetime(2025, 1, 1, 0, 50, tzinfo=timezone.utc)},
    ]

    result = checker.check(
        candles=candles,
        interval="15m",
        start_at=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
        end_at=datetime(2025, 1, 1, 1, 0, tzinfo=timezone.utc),
        symbol="BTCUSDT",
    )

    assert result["is_valid"] is False
    assert result["duplicate_count"] == 1
    assert result["gap_count"] == 2
    assert result["misaligned_count"] == 1
    assert "2025-01-01T00:30:00+00:00" in result["missing_open_times"]
    assert "2025-01-01T00:45:00+00:00" in result["missing_open_times"]
