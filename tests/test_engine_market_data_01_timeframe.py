import pytest

from app.engine_market_data.errors import UnsupportedTimeframeError
from app.engine_market_data.timeframe import (
    expected_next_open_time, floor_timestamp_to_timeframe,
    is_aligned_to_timeframe, timeframe_to_milliseconds,
)


@pytest.mark.parametrize("timeframe,expected", [("1m", 60_000), ("5m", 300_000), ("15m", 900_000)])
def test_supported_timeframe_duration_and_next_open(timeframe: str, expected: int) -> None:
    assert timeframe_to_milliseconds(timeframe) == expected
    assert expected_next_open_time(0, timeframe) == expected


def test_floor_and_alignment() -> None:
    assert floor_timestamp_to_timeframe(901_234, "15m") == 900_000
    assert is_aligned_to_timeframe(900_000, "15m") is True
    assert is_aligned_to_timeframe(900_001, "15m") is False


def test_unknown_timeframe_is_rejected() -> None:
    with pytest.raises(UnsupportedTimeframeError):
        timeframe_to_milliseconds("2m")
