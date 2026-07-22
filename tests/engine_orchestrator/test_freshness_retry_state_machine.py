from datetime import timedelta

import pytest

from app.engine_orchestrator.freshness_gate import FreshnessClassification
from tests.engine_orchestrator.test_freshness_retry_gate import NOW, Repo, decision


@pytest.mark.parametrize("health", [
    "RECOVERING", "GAP_DETECTED", "PERSISTENT_GAP", "STALE", "DEGRADED",
    "DISCONNECTED", "ERROR", "NOT_CONFIGURED", "MISSING",
])
def test_recoverable_health_states_wait_before_deadline(health):
    value = decision(Repo(status={"1h": health}))
    assert value.classification == FreshnessClassification.WAITING_RETRYABLE
    assert value.waiting_timeframes == ("1h",)
    assert f"1h:STATUS_{health}" in value.reasons


@pytest.mark.parametrize("health", ["RECOVERING", "GAP_DETECTED", "PERSISTENT_GAP"])
def test_recoverable_health_states_terminalize_only_at_deadline(health):
    value = decision(Repo(status={"1h": health}), deadline=NOW)
    assert value.classification == FreshnessClassification.TERMINAL_NOT_READY
    assert value.reason_code == "FRESHNESS_DEADLINE_EXCEEDED"
    assert value.waiting_timeframes == ("1h",)


def test_boundary_only_blocker_is_waiting_and_includes_timeframe():
    value = decision(Repo(missing=("1h",)))
    assert value.classification == FreshnessClassification.WAITING_RETRYABLE
    assert value.waiting_timeframes == ("1h",)


def test_status_and_boundary_reasons_dedupe_waiting_timeframe():
    value = decision(Repo(missing=("1h",), status={"1h": "GAP_DETECTED"}))
    assert value.reasons == ("1h:BOUNDARY_NOT_READY", "1h:STATUS_GAP_DETECTED")
    assert value.waiting_timeframes == ("1h",)


def test_multiple_blockers_use_canonical_timeframe_order():
    timeframes = ("1d", "1h", "1m", "4h", "15m", "5m")
    statuses = {timeframe: "RECOVERING" for timeframe in timeframes}
    value = decision(Repo(status=statuses), timeframes)
    assert value.waiting_timeframes == ("1m", "5m", "15m", "1h", "4h", "1d")


def test_ready_has_no_waiting_timeframes_or_blockers():
    value = decision(Repo())
    assert value.classification == FreshnessClassification.READY
    assert value.waiting_timeframes == ()
    assert value.blocking_reasons == ()


def test_explicit_future_contract_violation_is_terminal_before_deadline():
    value = decision(Repo(latest_override={"1h": int((NOW + timedelta(hours=1)).timestamp() * 1000)}))
    assert value.classification == FreshnessClassification.TERMINAL_NOT_READY
    assert value.reason_code == "FUTURE_OR_UNCLOSED_DATA"


def test_non_strict_higher_stale_policy_stays_ready_but_lower_policy_is_unchanged():
    from app.engine_orchestrator.freshness_gate import FreshnessGate

    higher = FreshnessGate(
        Repo(status={"1h": "STALE"}), ("15m", "1h"),
        require_all_timeframes_ok=False, allow_stale_higher_timeframes=True,
        clock=lambda: NOW,
    ).check("BTCUSDT", 1_768_176_000_000, deadline_at=NOW + timedelta(seconds=150))
    lower = FreshnessGate(
        Repo(status={"15m": "STALE"}), ("15m", "1h"),
        require_all_timeframes_ok=False, allow_stale_higher_timeframes=True,
        clock=lambda: NOW,
    ).check("BTCUSDT", 1_768_176_000_000, deadline_at=NOW + timedelta(seconds=150))
    assert higher.classification == FreshnessClassification.READY
    assert lower.classification == FreshnessClassification.WAITING_RETRYABLE


def test_strict_higher_status_policy_remains_blocking():
    value = decision(Repo(status={"1h": "STALE"}))
    assert value.classification == FreshnessClassification.WAITING_RETRYABLE
    assert value.waiting_timeframes == ("1h",)
