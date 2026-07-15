"""Deterministic UTC boundary-to-candle synchronization plan."""

from dataclasses import dataclass

from app.engine_market_data.market_symbol import normalize_market_symbol
from app.engine_market_data.timeframe import timeframe_to_milliseconds


SYNC_PLAN = {
    "15m": {"on_boundary": "15m", "required": {"15m": 1, "5m": 3, "1m": 15}},
    "1h": {"on_boundary": "1h", "required": {"1h": 1}},
    "4h": {"on_boundary": "4h", "required": {"4h": 1}},
    "1d": {"on_boundary": "1d", "required": {"1d": 1}},
}


@dataclass(frozen=True, slots=True)
class SyncTask:
    symbol: str
    boundary_timeframe: str
    target_timeframe: str
    expected_open_times: list[int]


def expected_open_times_for_boundary(boundary_timeframe: str, target_timeframe: str,
                                     boundary_open_time_ms: int) -> list[int]:
    try: required = SYNC_PLAN[boundary_timeframe]["required"]
    except KeyError as exc: raise ValueError(f"unsupported boundary timeframe {boundary_timeframe!r}") from exc
    if target_timeframe not in required: raise ValueError("target timeframe is not part of this boundary plan")
    boundary_duration = timeframe_to_milliseconds(boundary_timeframe)
    target_duration = timeframe_to_milliseconds(target_timeframe)
    if boundary_open_time_ms < 0 or boundary_open_time_ms % boundary_duration:
        raise ValueError("boundary open time must be UTC timeframe-aligned")
    count = int(required[target_timeframe])
    result = [boundary_open_time_ms + index * target_duration for index in range(count)]
    if result and result[-1] + target_duration > boundary_open_time_ms + boundary_duration:
        raise ValueError("sync plan exceeds boundary window")
    return result


def build_sync_tasks_for_boundary(symbol: str, boundary_timeframe: str,
                                  boundary_open_time_ms: int, plan: dict | None = None) -> list[SyncTask]:
    active_plan = plan or SYNC_PLAN
    if boundary_timeframe not in active_plan: raise ValueError("unsupported boundary timeframe")
    symbol = normalize_market_symbol(symbol)
    return [SyncTask(symbol, boundary_timeframe, target,
        expected_open_times_for_boundary(boundary_timeframe, target, boundary_open_time_ms))
        for target in active_plan[boundary_timeframe]["required"]]
