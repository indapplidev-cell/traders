from __future__ import annotations

from dataclasses import dataclass

from .stability_models import (
    ObservationAggregates,
    RuntimeHealthClassification,
    SampleTransport,
    ScheduleValidation,
)


@dataclass(frozen=True, slots=True)
class AcceptanceDecision:
    accepted: bool
    observer_failure: bool
    runtime_failure: bool
    reasons: tuple[str, ...]


def evaluate_acceptance(
    observation: ObservationAggregates,
    schedule: ScheduleValidation,
    *,
    minimum_duration_seconds: float = 4500.0,
) -> AcceptanceDecision:
    reasons: list[str] = []
    observer_reasons: list[str] = []
    runtime_reasons: list[str] = []
    if observation.duration_seconds < minimum_duration_seconds:
        observer_reasons.append("DURATION_GATE_FAILED")
    if not schedule.accepted:
        observer_reasons.append("SCHEDULE_CONTINUITY_FAILED")
    if observation.observer_restarts:
        observer_reasons.append("OBSERVER_RESTARTED")
    if observation.partial_windows_concatenated:
        observer_reasons.append("PARTIAL_WINDOWS_CONCATENATED")
    for result in observation.http_results:
        if result.transport is not SampleTransport.SUCCESS:
            runtime_reasons.append(f"TRANSPORT_{result.transport.value}:{result.route}")
        if (
            result.route.endswith("/health")
            and result.runtime_health
            in {
                RuntimeHealthClassification.DEGRADED,
                RuntimeHealthClassification.UNKNOWN,
            }
        ):
            runtime_reasons.append(
                "RUNTIME_"
                f"{result.runtime_health.value}:"
                f"{result.classification_reason_code.value}:"
                f"{result.classifier_branch_id}:"
                f"{result.route}"
            )
    reasons.extend(observer_reasons)
    reasons.extend(runtime_reasons)
    return AcceptanceDecision(
        accepted=not reasons,
        observer_failure=bool(observer_reasons),
        runtime_failure=bool(runtime_reasons),
        reasons=tuple(reasons),
    )
