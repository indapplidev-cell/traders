from app.engine_market_data.candle import Candle
from app.engine_market_data.gap_detector import detect_gap, find_missing_open_times


def make(open_time: int) -> Candle:
    return Candle("BTCUSDT", "1m", open_time, open_time + 59_999, 10, 12, 9, 11, 5, None, None, True, "rest")


def test_adjacent_candles_have_no_gap() -> None:
    assert detect_gap(make(0), make(60_000)) is None


def test_detector_finds_one_and_many_missing_open_times() -> None:
    assert detect_gap(make(0), make(120_000)).missing_open_times == (60_000,)  # type: ignore[union-attr]
    assert find_missing_open_times([make(0), make(240_000)], "1m") == [60_000, 120_000, 180_000]
