"""UTC millisecond timeframe helpers."""

from app.engine_market_data.errors import UnsupportedTimeframeError


TIMEFRAME_MILLISECONDS: dict[str, int] = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}
SUPPORTED_TIMEFRAMES = frozenset(TIMEFRAME_MILLISECONDS)


def timeframe_to_milliseconds(timeframe: str) -> int:
    try:
        return TIMEFRAME_MILLISECONDS[timeframe]
    except KeyError as exc:
        raise UnsupportedTimeframeError(f"Unsupported timeframe: {timeframe!r}") from exc


def floor_timestamp_to_timeframe(timestamp_ms: int, timeframe: str) -> int:
    if not isinstance(timestamp_ms, int) or isinstance(timestamp_ms, bool) or timestamp_ms < 0:
        raise ValueError("timestamp_ms must be a non-negative integer")
    duration = timeframe_to_milliseconds(timeframe)
    return timestamp_ms - timestamp_ms % duration


def expected_next_open_time(open_time_ms: int, timeframe: str) -> int:
    if not is_aligned_to_timeframe(open_time_ms, timeframe):
        raise ValueError("open_time_ms must be aligned to the timeframe")
    return open_time_ms + timeframe_to_milliseconds(timeframe)


def is_aligned_to_timeframe(timestamp_ms: int, timeframe: str) -> bool:
    if not isinstance(timestamp_ms, int) or isinstance(timestamp_ms, bool) or timestamp_ms < 0:
        return False
    return timestamp_ms % timeframe_to_milliseconds(timeframe) == 0
