"""Causal freshness check against market_data_sync_state."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engine_market_data.timeframe import timeframe_to_milliseconds


LOWER_TIMEFRAMES = frozenset({"1m", "5m", "15m"})


@dataclass(frozen=True, slots=True)
class FreshnessDecision:
    allowed: bool
    status: str
    reasons: tuple[str, ...] = ()
    timeframe_statuses: dict[str, str] = field(default_factory=dict)


class FreshnessGate:
    def __init__(self, sync_state_repository: object, required_timeframes: tuple[str, ...], *,
                 require_all_timeframes_ok: bool = True,
                 allow_stale_higher_timeframes: bool = False) -> None:
        self.repository = sync_state_repository
        self.required_timeframes = required_timeframes
        self.require_all_timeframes_ok = require_all_timeframes_ok
        self.allow_stale_higher_timeframes = allow_stale_higher_timeframes

    @staticmethod
    def _required_boundary(timeframe: str, primary_boundary_ms: int) -> int:
        duration = timeframe_to_milliseconds(timeframe)
        return (int(primary_boundary_ms) // duration) * duration

    def check(self, symbol: str, closed_until_ms: int) -> FreshnessDecision:
        rows = self.repository.list_for([symbol], list(self.required_timeframes))
        by_timeframe = {row.timeframe: row for row in rows}
        reasons: list[str] = []
        statuses: dict[str, str] = {}
        for timeframe in self.required_timeframes:
            row = by_timeframe.get(timeframe)
            if row is None:
                statuses[timeframe] = "MISSING"
                reasons.append(f"{timeframe}:MISSING_STATE")
                continue
            status = str(row.status)
            statuses[timeframe] = status
            higher_lag_allowed = (
                timeframe not in LOWER_TIMEFRAMES
                and self.allow_stale_higher_timeframes
                and status in {"STALE", "DEGRADED"}
            )
            must_be_ok = timeframe in LOWER_TIMEFRAMES or self.require_all_timeframes_ok
            if status != "OK" and not (higher_lag_allowed and must_be_ok):
                reasons.append(f"{timeframe}:STATUS_{status}")
            required_boundary = self._required_boundary(timeframe, closed_until_ms)
            stored_boundary = getattr(row, "last_stored_close_boundary_ms", None)
            if stored_boundary is None or int(stored_boundary) < required_boundary:
                reasons.append(f"{timeframe}:BOUNDARY_NOT_READY")
        return FreshnessDecision(
            allowed=not reasons,
            status="OK" if not reasons else "NOT_OK",
            reasons=tuple(reasons),
            timeframe_statuses=statuses,
        )

    def ok(self, symbol: str, closed_until_ms: int) -> bool:
        return self.check(symbol, closed_until_ms).allowed
