"""Causal freshness classification with deadline-driven retry diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Callable

from app.engine_market_data.timeframe import timeframe_to_milliseconds


CANONICAL_TIMEFRAME_ORDER = ("1m", "5m", "15m", "1h", "4h", "1d")
LOWER_TIMEFRAMES = frozenset({"1m", "5m", "15m"})
_TIMEFRAME_RANK = {timeframe: index for index, timeframe in enumerate(CANONICAL_TIMEFRAME_ORDER)}


class FreshnessClassification(StrEnum):
    READY = "READY"
    WAITING_RETRYABLE = "WAITING_RETRYABLE"
    TERMINAL_NOT_READY = "TERMINAL_NOT_READY"


class FreshnessBlockingKind(StrEnum):
    BOUNDARY_NOT_READY = "BOUNDARY_NOT_READY"
    HEALTH_STATUS_NOT_OK = "HEALTH_STATUS_NOT_OK"
    FATAL_CONTRACT_ERROR = "FATAL_CONTRACT_ERROR"


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
class FreshnessBlockingReason:
    timeframe: str | None
    kind: FreshnessBlockingKind
    code: str
    health_status: str | None
    required_boundary_ms: int | None
    available_boundary_ms: int | None
    retryable: bool


@dataclass(frozen=True, slots=True)
class FreshnessDecision:
    allowed: bool
    status: str
    classification: FreshnessClassification
    reason_code: str | None = None
    reasons: tuple[str, ...] = ()
    timeframe_statuses: dict[str, str] = field(default_factory=dict)
    availability: tuple[BoundaryAvailability, ...] = ()
    missing_timeframes: tuple[str, ...] = ()
    waiting_timeframes: tuple[str, ...] = ()
    blocking_reasons: tuple[FreshnessBlockingReason, ...] = ()

    def payload(self) -> dict[str, object]:
        return {
            "classification": self.classification.value,
            "readiness_classification": self.classification.value,
            "status": self.status,
            "reason_code": self.reason_code,
            "reasons": list(self.reasons),
            "waiting_timeframes": list(self.waiting_timeframes),
            "blocking_reasons": [asdict(item) for item in self.blocking_reasons],
            "timeframes": [asdict(item) for item in self.availability],
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_timeframes(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values), key=lambda value: (_TIMEFRAME_RANK.get(value, len(_TIMEFRAME_RANK)), value)))


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

    @staticmethod
    def _terminal_contract_error(status: str, reason: str, *,
                                 blocking_reasons: tuple[FreshnessBlockingReason, ...] = ()) -> FreshnessDecision:
        return FreshnessDecision(
            False, status, FreshnessClassification.TERMINAL_NOT_READY,
            reason, (reason,), blocking_reasons=blocking_reasons,
        )

    def check(self, symbol: str, closed_until_ms: int, *,
              deadline_at: datetime | None = None,
              now: datetime | None = None) -> FreshnessDecision:
        checked_at = self._aware_utc(now or self.clock())
        if deadline_at is not None:
            deadline_at = self._aware_utc(deadline_at)
        if int(closed_until_ms) <= 0:
            return self._terminal_contract_error("INVALID_BOUNDARY", "INVALID_BOUNDARY")

        rows = self.repository.list_for([symbol], list(self.required_timeframes))
        by_timeframe = {row.timeframe: row for row in rows}
        blockers: list[FreshnessBlockingReason] = []
        statuses: dict[str, str] = {}
        availability: list[BoundaryAvailability] = []
        missing: list[str] = []
        fatal_reason: str | None = None
        now_ms = int(checked_at.timestamp() * 1000)

        for timeframe in self.required_timeframes:
            try:
                duration = timeframe_to_milliseconds(timeframe)
            except ValueError:
                blocker = FreshnessBlockingReason(
                    timeframe, FreshnessBlockingKind.FATAL_CONTRACT_ERROR,
                    "UNSUPPORTED_TIMEFRAME", None, None, None, False,
                )
                return self._terminal_contract_error(
                    "UNSUPPORTED_TIMEFRAME", "UNSUPPORTED_TIMEFRAME",
                    blocking_reasons=(blocker,),
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
                blockers.append(FreshnessBlockingReason(
                    timeframe, FreshnessBlockingKind.BOUNDARY_NOT_READY,
                    "BOUNDARY_NOT_READY", health, required_close, latest_close, True,
                ))
            if latest_close is not None and latest_close > now_ms:
                fatal_reason = "FUTURE_OR_UNCLOSED_DATA"
                blockers.append(FreshnessBlockingReason(
                    timeframe, FreshnessBlockingKind.FATAL_CONTRACT_ERROR,
                    fatal_reason, health, required_close, latest_close, False,
                ))

            stale_higher_allowed = (
                timeframe not in LOWER_TIMEFRAMES
                and self.allow_stale_higher_timeframes
                and health in {"STALE", "DEGRADED"}
            )
            health_required = timeframe in LOWER_TIMEFRAMES or self.require_all_timeframes_ok
            if health_required and health != "OK" and not stale_higher_allowed:
                blockers.append(FreshnessBlockingReason(
                    timeframe, FreshnessBlockingKind.HEALTH_STATUS_NOT_OK,
                    f"STATUS_{health}", health, required_close, latest_close, True,
                ))
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

        reasons = tuple(dict.fromkeys(
            f"{item.timeframe}:{item.code}" if item.timeframe else item.code
            for item in blockers
        ))
        missing_timeframes = _canonical_timeframes(missing)
        waiting_timeframes = _canonical_timeframes([
            item.timeframe for item in blockers if item.retryable and item.timeframe is not None
        ])
        blocker_values = tuple(blockers)
        availability_values = tuple(availability)

        if fatal_reason is not None:
            return FreshnessDecision(
                False, fatal_reason, FreshnessClassification.TERMINAL_NOT_READY,
                fatal_reason, reasons, statuses, availability_values,
                missing_timeframes, waiting_timeframes, blocker_values,
            )

        if blockers:
            if deadline_at is not None and checked_at >= deadline_at:
                terminal_reason = "FRESHNESS_DEADLINE_EXCEEDED"
                return FreshnessDecision(
                    False, terminal_reason, FreshnessClassification.TERMINAL_NOT_READY,
                    terminal_reason, reasons, statuses, availability_values,
                    missing_timeframes, waiting_timeframes, blocker_values,
                )

            health_codes = {item.code for item in blockers if item.kind == FreshnessBlockingKind.HEALTH_STATUS_NOT_OK}
            if "STATUS_GAP_DETECTED" in health_codes:
                status = reason_code = "PERSISTENT_GAP"
            elif missing_timeframes:
                status = "WAITING_FOR_REQUIRED_BOUNDARY"
                reason_code = (
                    f"{missing_timeframes[0]}:BOUNDARY_NOT_READY"
                    if len(missing_timeframes) == 1
                    else "MULTIPLE_REQUIRED_BOUNDARIES_NOT_READY"
                )
            else:
                status = reason_code = "FRESHNESS_POLICY_NOT_OK"
            return FreshnessDecision(
                False, status, FreshnessClassification.WAITING_RETRYABLE,
                reason_code, reasons, statuses, availability_values,
                missing_timeframes, waiting_timeframes, blocker_values,
            )

        return FreshnessDecision(
            True, "READY", FreshnessClassification.READY, None, (), statuses,
            availability_values, (), (), (),
        )

    def ok(self, symbol: str, closed_until_ms: int) -> bool:
        return self.check(symbol, closed_until_ms).allowed
