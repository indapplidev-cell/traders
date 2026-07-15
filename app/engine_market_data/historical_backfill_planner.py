"""UTC-boundary rolling-window planning and missing-range helpers."""

from dataclasses import dataclass, field
from collections.abc import Sequence

from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import floor_timestamp_to_timeframe, timeframe_to_milliseconds


@dataclass(frozen=True, slots=True)
class BackfillTask:
    symbol: str
    timeframe: str
    limit: int
    start_open_time_ms: int
    end_open_time_ms: int
    latest_closed_open_time_ms: int
    expected_open_times: list[int]
    future_bars_used: bool = False


@dataclass(frozen=True, slots=True)
class HistoricalBackfillPlan:
    now_ms: int
    tasks: list[BackfillTask] = field(default_factory=list)
    future_bars_used: bool = False


@dataclass(frozen=True, slots=True)
class BackfillRange:
    symbol: str
    timeframe: str
    start_time_ms: int
    end_time_ms: int
    expected_count: int


class HistoricalBackfillPlanner:
    def build_plan(
        self,
        symbols: list[str],
        timeframes: list[str],
        now_ms: int,
        limits: dict[str, int],
    ) -> HistoricalBackfillPlan:
        if not isinstance(now_ms, int) or isinstance(now_ms, bool) or now_ms < 0:
            raise ValueError("now_ms must be a non-negative UTC millisecond timestamp")
        tasks: list[BackfillTask] = []
        for symbol in symbols:
            normalized = normalize_market_symbol(symbol)
            for timeframe in timeframes:
                duration = timeframe_to_milliseconds(timeframe)
                limit = limits.get(timeframe, 0)
                if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
                    raise ValueError(f"limit for {timeframe} must be a positive integer")
                latest = floor_timestamp_to_timeframe(now_ms, timeframe) - duration
                start = latest - (limit - 1) * duration
                if latest < 0 or start < 0:
                    raise ValueError("now_ms is too early for the requested rolling window")
                expected = list(range(start, latest + duration, duration))
                tasks.append(BackfillTask(normalized, timeframe, limit, start, latest, latest, expected))
        return HistoricalBackfillPlan(now_ms=now_ms, tasks=tasks)

    def build_task(self, symbol: str, timeframe: str, now_ms: int, limit: int) -> BackfillTask:
        return self.build_plan([symbol], [timeframe], now_ms, {timeframe: limit}).tasks[0]


def group_missing_open_times_into_ranges(
    missing_open_times: Sequence[int],
    timeframe: str,
    symbol: str = "",
) -> list[BackfillRange]:
    """Group exact missing opens; range end is the final candle open timestamp."""
    duration = timeframe_to_milliseconds(timeframe)
    values = sorted(set(missing_open_times))
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 or value % duration for value in values):
        raise ValueError("missing open times must be non-negative and timeframe-aligned")
    ranges: list[BackfillRange] = []
    for value in values:
        if not ranges or value != ranges[-1].end_time_ms + duration:
            ranges.append(BackfillRange(normalize_market_symbol(symbol) if symbol else "", timeframe, value, value, 1))
        else:
            previous = ranges[-1]
            ranges[-1] = BackfillRange(previous.symbol, timeframe, previous.start_time_ms, value,
                                       previous.expected_count + 1)
    return ranges


def split_backfill_range(backfill_range: BackfillRange, max_rest_limit: int) -> list[BackfillRange]:
    if max_rest_limit <= 0 or max_rest_limit > 1000:
        raise ValueError("max_rest_limit must be between 1 and 1000")
    duration = timeframe_to_milliseconds(backfill_range.timeframe)
    batches: list[BackfillRange] = []
    remaining = backfill_range.expected_count
    start = backfill_range.start_time_ms
    while remaining:
        count = min(remaining, max_rest_limit)
        end = start + (count - 1) * duration
        batches.append(BackfillRange(backfill_range.symbol, backfill_range.timeframe, start, end, count))
        start = end + duration
        remaining -= count
    return batches

