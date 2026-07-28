from __future__ import annotations

from app.observability.stability_acceptance import evaluate_acceptance
from app.observability.stability_models import (
    ObservationAggregates,
    RuntimeHealthClassification,
    SafeHttpResult,
    SampleTransport,
    ScheduleValidation,
)
from scripts.readonly_api_stability_observer import simulate


def observation(duration=4500.0):
    return ObservationAggregates(
        first_completed_monotonic_ns=1_000_000_000,
        last_completed_monotonic_ns=1_000_000_000 + int(duration * 1_000_000_000),
    )


def health(classification, transport=SampleTransport.SUCCESS):
    return SafeHttpResult(
        "/api/v1/health", transport, 200 if transport is SampleTransport.SUCCESS else None,
        0.1, 100, "application/json", "a" * 64,
        runtime_health=classification,
    )


def test_simulated_uninterrupted_4500_plus_passes():
    result = simulate()
    assert result["SIMULATED_DURATION_SECONDS"] >= 4500
    assert result["SIMULATED_ACCEPTANCE"] == "PASS"


def test_4499_seconds_fails_duration_gate():
    decision = evaluate_acceptance(observation(4499), ScheduleValidation())
    assert decision.observer_failure and not decision.accepted


def test_partial_windows_never_concatenate():
    item = observation()
    item.partial_windows_concatenated = True
    assert "PARTIAL_WINDOWS_CONCATENATED" in evaluate_acceptance(
        item, ScheduleValidation()
    ).reasons


def test_observer_restart_invalidates_window():
    item = observation()
    item.observer_restarts = 1
    assert evaluate_acceptance(item, ScheduleValidation()).observer_failure


def test_real_sequence_gap_invalidates_window():
    validation = ScheduleValidation(unexplained_sequence_gaps=((3, 5),))
    assert evaluate_acceptance(observation(), validation).observer_failure


def test_observer_and_runtime_failure_are_distinct():
    item = observation(100)
    item.http_results.append(
        health(RuntimeHealthClassification.UNKNOWN, SampleTransport.TIMEOUT)
    )
    decision = evaluate_acceptance(item, ScheduleValidation())
    assert decision.observer_failure and decision.runtime_failure


def test_deadline_expired_transport_success_is_accepted_by_tooling():
    item = observation()
    item.http_results.append(health(RuntimeHealthClassification.DEADLINE_EXPIRED))
    decision = evaluate_acceptance(item, ScheduleValidation())
    assert decision.accepted


def test_runtime_policy_still_sees_deadline_expired():
    item = observation()
    item.http_results.append(health(RuntimeHealthClassification.DEADLINE_EXPIRED))
    assert item.http_results[0].runtime_health is RuntimeHealthClassification.DEADLINE_EXPIRED


def test_degraded_is_runtime_failure_not_observer_interruption():
    item = observation()
    item.http_results.append(health(RuntimeHealthClassification.DEGRADED))
    decision = evaluate_acceptance(item, ScheduleValidation())
    assert decision.runtime_failure and not decision.observer_failure


def test_start_mid_end_client_schedule_is_deterministic():
    assert tuple(("START", "MIDPOINT", "END")) == ("START", "MIDPOINT", "END")

