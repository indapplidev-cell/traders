"""Deterministic boundary-aware health reconstruction for the read-only API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


TIMEFRAME_GRACE_SECONDS: Mapping[str, int] = {
    "1m": 10,
    "5m": 15,
    "15m": 20,
    "1h": 60,
    "4h": 90,
    "1d": 120,
}

_TERMINAL_RUN_STATUSES = {
    "SKIPPED_FRESHNESS_NOT_OK",
    "SKIPPED_FRESHNESS_TIMEOUT",
    "MODULE_ERROR",
    "ERROR",
}
_REAL_BLOCKING_HEALTH = {
    "DEGRADED",
    "ERROR",
    "GAP_DETECTED",
    "MISSING",
    "NOT_AVAILABLE",
    "OFFLINE",
    "RECOVERING",
    "STALE",
    "UNKNOWN",
}


@dataclass(frozen=True, slots=True)
class BoundaryHealthDecision:
    status: str
    timing_state: str
    reason_code: str
    operational: bool
    ready: bool
    acceptance_blocking: bool
    market_data_status: str
    orchestrator_status: str


def _blocking(status: str, timing_state: str, reason_code: str, *, error: bool = False) -> BoundaryHealthDecision:
    service_status = "ERROR" if error else status
    return BoundaryHealthDecision(
        status=status,
        timing_state=timing_state,
        reason_code=reason_code,
        operational=False,
        ready=False,
        acceptance_blocking=True,
        market_data_status=service_status,
        orchestrator_status=service_status,
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("health policy clock must be timezone-aware")
    return value.astimezone(timezone.utc)


def evaluate_boundary_health(
    run: object | None,
    *,
    candle_available: bool,
    now: datetime,
) -> BoundaryHealthDecision:
    """Apply real-blocker > boundary-state > workflow-label > UNKNOWN precedence."""

    checked_at = _utc(now)
    if not candle_available:
        return _blocking("NOT_AVAILABLE", "UNKNOWN", "MARKET_DATA_NOT_AVAILABLE")
    if run is None:
        return _blocking("UNKNOWN", "UNKNOWN", "ORCHESTRATOR_STATE_NOT_AVAILABLE")

    run_status = str(getattr(run, "status", "") or "").upper()
    error_code = str(getattr(run, "error_code", "") or "").upper()
    if run_status in _TERMINAL_RUN_STATUSES or error_code:
        return _blocking(
            "ERROR",
            "DEGRADED",
            error_code or run_status or "ORCHESTRATOR_ERROR",
            error=True,
        )

    payload_value = getattr(run, "last_freshness_payload", None)
    payload = payload_value if isinstance(payload_value, Mapping) else {}
    timeframes_value = payload.get("timeframes")
    blockers_value = payload.get("blocking_reasons")
    timeframes = timeframes_value if isinstance(timeframes_value, list) else []
    blockers = blockers_value if isinstance(blockers_value, list) else []

    for item in timeframes:
        if not isinstance(item, Mapping):
            return _blocking("UNKNOWN", "UNKNOWN", "INVALID_FRESHNESS_PAYLOAD")
        health = str(item.get("health_state") or "").upper()
        if health in _REAL_BLOCKING_HEALTH:
            reason = str(item.get("reason_code") or f"STATUS_{health}")
            return _blocking("DEGRADED", "DEGRADED", reason)

    for item in blockers:
        if not isinstance(item, Mapping):
            return _blocking("UNKNOWN", "UNKNOWN", "INVALID_FRESHNESS_PAYLOAD")
        kind = str(item.get("kind") or "").upper()
        code = str(item.get("code") or "FRESHNESS_BLOCKING_EVIDENCE").upper()
        health = str(item.get("health_status") or "").upper()
        if kind in {"FATAL_CONTRACT_ERROR", "HEALTH_STATUS_NOT_OK"} or health in _REAL_BLOCKING_HEALTH:
            return _blocking("DEGRADED", "DEGRADED", code)

    classification = str(payload.get("classification") or payload.get("readiness_classification") or "").upper()
    payload_status = str(payload.get("status") or "").upper()
    if classification == "TERMINAL_NOT_READY" or payload_status in {
        "FRESHNESS_DEADLINE_EXCEEDED",
        "PERSISTENT_GAP",
        "FUTURE_OR_UNCLOSED_DATA",
        "INVALID_BOUNDARY",
        "UNSUPPORTED_TIMEFRAME",
    }:
        return _blocking("DEGRADED", "DEADLINE_EXPIRED", payload_status or "FRESHNESS_NOT_READY")

    if timeframes and all(
        isinstance(item, Mapping)
        and item.get("required_boundary_available") is True
        and str(item.get("health_state") or "").upper() == "OK"
        for item in timeframes
    ):
        return BoundaryHealthDecision(
            "OK", "CURRENT", "CURRENT", True, True, False, "OK", "OK"
        )

    missing = [
        item
        for item in timeframes
        if isinstance(item, Mapping) and item.get("required_boundary_available") is False
    ]
    if missing and classification == "WAITING_RETRYABLE" and payload_status == "WAITING_FOR_REQUIRED_BOUNDARY":
        now_ms = int(checked_at.timestamp() * 1000)
        within_grace = True
        for item in missing:
            timeframe = str(item.get("timeframe") or "")
            health = str(item.get("health_state") or "").upper()
            boundary = item.get("required_boundary_close_time")
            grace = TIMEFRAME_GRACE_SECONDS.get(timeframe)
            if (
                health != "OK"
                or not isinstance(boundary, int)
                or isinstance(boundary, bool)
                or grace is None
                or now_ms > boundary + grace * 1000
            ):
                within_grace = False
                break
        boundary_blockers_only = bool(blockers) and all(
            isinstance(item, Mapping)
            and str(item.get("kind") or "").upper() == "BOUNDARY_NOT_READY"
            and str(item.get("code") or "").upper() == "BOUNDARY_NOT_READY"
            for item in blockers
        )
        missing_timeframes = {str(item.get("timeframe") or "") for item in missing}
        blocker_timeframes = {
            str(item.get("timeframe") or "")
            for item in blockers
            if isinstance(item, Mapping)
        }
        boundary_blockers_complete = missing_timeframes == blocker_timeframes
        if not boundary_blockers_only or not boundary_blockers_complete:
            return _blocking("UNKNOWN", "UNKNOWN", "INCOMPLETE_BOUNDARY_EVIDENCE")
        if within_grace:
            return BoundaryHealthDecision(
                "OK",
                "WITHIN_GRACE",
                "BOUNDARY_WITHIN_GRACE",
                True,
                True,
                False,
                "OK",
                "OK",
            )
        return _blocking("DEGRADED", "DEADLINE_EXPIRED", "BOUNDARY_GRACE_EXPIRED")

    freshness_status = str(getattr(run, "market_data_freshness_status", "") or "").upper()
    if run_status == "COMPLETED" and freshness_status in {"OK", "READY"}:
        return BoundaryHealthDecision(
            "OK", "CURRENT", "CURRENT", True, True, False, "OK", "OK"
        )

    return _blocking("UNKNOWN", "UNKNOWN", "INSUFFICIENT_AUTHORITATIVE_HEALTH_STATE")
