"""Causal freshness classification with explicit boundary availability."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Callable

from app.engine_market_data.timeframe import timeframe_to_milliseconds


LOWER_TIMEFRAMES = frozenset({"1m", "5m", "15m"})


class FreshnessClassification(StrEnum):
    READY = "READY"
    TRANSIENT_NOT_READY = "TRANSIENT_NOT_READY"
    TERMINAL_NOT_READY = "TERMINAL_NOT_READY"


@dataclass(frozen=True, slots=True)
class BoundaryAvailability:
    timeframe: str
    health_state: str
    required_boundary_open_time: int | None
    required_boundary_close_time: int | None
    required_boundary_available: bool
    latest_available_open_time: int | None
    latest_available_close_time: int | None
    lag_candles: int | None
    lag_seconds: float | None
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class FreshnessDecision:
    allowed: bool
    status: str
    classification: str
    reason_code: str | None = None
    reasons: tuple[str, ...] = ()
    timeframe_statuses: dict[str, str] = field(default_factory=dict)
    availability: tuple[BoundaryAvailability, ...] = ()
    missing_timeframes: tuple[str, ...] = ()

    def payload(self) -> dict[str, object]:
        return {
            "classification": self.classification,
            "status": self.status,
            "reason_code": self.reason_code,
            "reasons": list(self.reasons),
            "timeframes": [asdict(item) for item in self.availability],
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FreshnessGate:
    def __init__(self, sync_state_repository: object, required_timeframes: tuple[str, ...], *,
                 require_all_timeframes_ok: bool = True,
                 allow_stale_higher_timeframes: bool = False,
                 clock: Callable[[], datetime] = _utc_now) -> None:
        self.repository = sync_state_repository
        self.required_timeframes = required_timeframes
        self.require_all_timeframes_ok = require_all_timeframes_ok
        self.allow_stale_higher_timeframes = allow_stale_higher_timeframes
        self.clock = clock

    @staticmethod
    def _required_boundary(timeframe: str, primary_boundary_ms: int) -> int:
        duration = timeframe_to_milliseconds(timeframe)
        return (int(primary_boundary_ms) // duration) * duration

    @staticmethod
    def _aware_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("freshness clock and deadline must be timezone-aware")
        return value.astimezone(timezone.utc)

    def check(self, symbol: str, closed_until_ms: int, *,
              deadline_at: datetime | None = None,
              now: datetime | None = None) -> FreshnessDecision:
        checked_at = self._aware_utc(now or self.clock())
        if deadline_at is not None:
            deadline_at = self._aware_utc(deadline_at)
        if int(closed_until_ms) <= 0:
            return FreshnessDecision(
                False, "INVALID_BOUNDARY", FreshnessClassification.TERMINAL_NOT_READY,
                "INVALID_BOUNDARY", ("INVALID_BOUNDARY",),
            )

        rows = self.repository.list_for([symbol], list(self.required_timeframes))
        by_timeframe = {row.timeframe: row for row in rows}
        reasons: list[str] = []
        policy_reasons: list[str] = []
        statuses: dict[str, str] = {}
        availability: list[BoundaryAvailability] = []
        missing: list[str] = []
        persistent_gap = False
        invalid_data = False
        now_ms = int(checked_at.timestamp() * 1000)

        for timeframe in self.required_timeframes:
            try:
                duration = timeframe_to_milliseconds(timeframe)
            except ValueError:
                return FreshnessDecision(
                    False, "UNSUPPORTED_TIMEFRAME", FreshnessClassification.TERMINAL_NOT_READY,
                    "UNSUPPORTED_TIMEFRAME", (f"{timeframe}:UNSUPPORTED_TIMEFRAME",),
                )
            required_close = self._required_boundary(timeframe, closed_until_ms)
            required_open = required_close - duration
            row = by_timeframe.get(timeframe)
            health = str(getattr(row, "status", "MISSING")) if row is not None else "MISSING"
            latest_close = getattr(row, "last_stored_close_boundary_ms", None) if row is not None else None
            latest_open = getattr(row, "last_stored_open_time_ms", None) if row is not None else None
            latest_close = int(latest_close) if latest_close is not None else None
            latest_open = int(latest_open) if latest_open is not None else None
            available = latest_close is not None and latest_close >= required_close
            lag_ms = None if latest_close is None else max(0, required_close - latest_close)
            lag_candles = None if lag_ms is None else lag_ms // duration
            boundary_reason = None if available else f"{timeframe}:BOUNDARY_NOT_READY"
            statuses[timeframe] = health
            if not available:
                missing.append(timeframe)
                reasons.append(boundary_reason)
            if health == "GAP_DETECTED":
                persistent_gap = True
            if latest_close is not None and latest_close > now_ms:
                invalid_data = True
                reasons.append(f"{timeframe}:FUTURE_OR_UNCLOSED_DATA")

            stale_higher_allowed = (
                timeframe not in LOWER_TIMEFRAMES
                and self.allow_stale_higher_timeframes
                and health in {"STALE", "DEGRADED"}
            )
            health_required = timeframe in LOWER_TIMEFRAMES or self.require_all_timeframes_ok
            if health_required and health != "OK" and not stale_higher_allowed:
                policy_reasons.append(f"{timeframe}:STATUS_{health}")
            availability.append(BoundaryAvailability(
                timeframe=timeframe,
                health_state=health,
                required_boundary_open_time=required_open,
                required_boundary_close_time=required_close,
                required_boundary_available=available,
                latest_available_open_time=latest_open,
                latest_available_close_time=latest_close,
                lag_candles=int(lag_candles) if lag_candles is not None else None,
                lag_seconds=lag_ms / 1000 if lag_ms is not None else None,
                reason_code=boundary_reason,
            ))

        if invalid_data:
            reason_code = "FUTURE_OR_UNCLOSED_DATA"
        elif persistent_gap:
            reason_code = "PERSISTENT_GAP"
        else:
            reason_code = None
        if reason_code is not None:
            return FreshnessDecision(
                False, reason_code, FreshnessClassification.TERMINAL_NOT_READY,
                reason_code, tuple(dict.fromkeys(reasons + policy_reasons)), statuses,
                tuple(availability), tuple(missing),
            )

        if missing:
            if deadline_at is not None and checked_at >= deadline_at:
                reason_code = "FRESHNESS_TIMEOUT"
                return FreshnessDecision(
                    False, reason_code, FreshnessClassification.TERMINAL_NOT_READY,
                    reason_code, tuple(dict.fromkeys(reasons + policy_reasons)), statuses,
                    tuple(availability), tuple(missing),
                )
            reason_code = (
                f"{missing[0]}:BOUNDARY_NOT_READY" if len(missing) == 1
                else "MULTIPLE_REQUIRED_BOUNDARIES_NOT_READY"
            )
            return FreshnessDecision(
                False, "WAITING_FOR_REQUIRED_BOUNDARY",
                FreshnessClassification.TRANSIENT_NOT_READY, reason_code,
                tuple(dict.fromkeys(reasons + policy_reasons)), statuses,
                tuple(availability), tuple(missing),
            )

        if policy_reasons:
            return FreshnessDecision(
                False, "FRESHNESS_POLICY_NOT_OK", FreshnessClassification.TERMINAL_NOT_READY,
                "FRESHNESS_POLICY_NOT_OK", tuple(policy_reasons), statuses,
                tuple(availability), (),
            )
        return FreshnessDecision(
            True, "READY", FreshnessClassification.READY, None, (), statuses,
            tuple(availability), (),
        )

    def ok(self, symbol: str, closed_until_ms: int) -> bool:
        return self.check(symbol, closed_until_ms).allowed
