from __future__ import annotations

from datetime import datetime, timezone

from .contracts import PRIMARY_STEP_MS, SemanticContract
from .models import ExpectedWindow


def generate_expected_windows(contract: SemanticContract, database_now: datetime) -> tuple[ExpectedWindow, ...]:
    if database_now.tzinfo is None:
        raise ValueError("database clock must be timezone-aware")
    now_ms = int(database_now.astimezone(timezone.utc).timestamp() * 1000)
    grace_ms = contract.missing_run_grace_seconds * 1000
    result = []
    for boundary in range(contract.first_measured_boundary_ms, contract.last_measured_boundary_ms + PRIMARY_STEP_MS, PRIMARY_STEP_MS):
        for symbol in contract.symbols:
            result.append(ExpectedWindow(symbol, contract.primary_timeframe, boundary, now_ms >= boundary + grace_ms))
    return tuple(result)


def expected_candle_keys(window: ExpectedWindow, required_timeframes: tuple[str, ...]) -> tuple[tuple[str, str, int], ...]:
    durations = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
    start = window.closed_until_ms - PRIMARY_STEP_MS
    keys: list[tuple[str, str, int]] = []
    for timeframe in required_timeframes:
        duration = durations[timeframe]
        if duration <= PRIMARY_STEP_MS:
            keys.extend((window.symbol, timeframe, value) for value in range(start, window.closed_until_ms, duration))
        elif window.closed_until_ms % duration == 0:
            keys.append((window.symbol, timeframe, window.closed_until_ms - duration))
    return tuple(keys)
