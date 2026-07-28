from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .stability_models import (
    CompletedSample,
    PhaseName,
    ScheduledSample,
    ScheduleValidation,
)


NANOSECONDS = 1_000_000_000


@dataclass(frozen=True, slots=True)
class Phase:
    phase_id: int
    name: PhaseName
    anchor_monotonic_ns: int
    end_monotonic_ns: int | None
    cadence_seconds: float
    tolerance_seconds: float


def _phase_samples(
    phase: Phase,
    *,
    final_due_monotonic_ns: int,
    sequence_start: int,
) -> list[ScheduledSample]:
    cadence_ns = int(phase.cadence_seconds * NANOSECONDS)
    phase_end = (
        final_due_monotonic_ns
        if phase.end_monotonic_ns is None
        else min(phase.end_monotonic_ns, final_due_monotonic_ns)
    )
    samples: list[ScheduledSample] = []
    sample_index = 0
    while True:
        due = phase.anchor_monotonic_ns + sample_index * cadence_ns
        if due > phase_end:
            break
        if phase.end_monotonic_ns is not None and due >= phase.end_monotonic_ns:
            break
        samples.append(
            ScheduledSample(
                sequence_id=sequence_start + len(samples),
                phase_id=phase.phase_id,
                phase_name=phase.name,
                scheduled_due_monotonic_ns=due,
                cadence_seconds=phase.cadence_seconds,
                tolerance_seconds=phase.tolerance_seconds,
            )
        )
        sample_index += 1
    return samples


def build_phase_aware_schedule(
    *,
    start_monotonic_ns: int,
    boundary_monotonic_ns: int,
    target_duration_seconds: float,
    normal_cadence_seconds: float = 15.0,
    boundary_cadence_seconds: float = 2.0,
    normal_tolerance_seconds: float = 10.0,
    boundary_tolerance_seconds: float = 4.0,
) -> tuple[ScheduledSample, ...]:
    boundary_start = boundary_monotonic_ns - 30 * NANOSECONDS
    boundary_end = boundary_monotonic_ns + 180 * NANOSECONDS
    if boundary_start <= start_monotonic_ns:
        raise ValueError("boundary phase must start after observation start")
    target_ns = start_monotonic_ns + int(target_duration_seconds * NANOSECONDS)
    normal_after_span = max(0, target_ns - boundary_end)
    normal_cadence_ns = int(normal_cadence_seconds * NANOSECONDS)
    # The final scheduled sample must be at or after the requested target.
    final_due = boundary_end + (
        (normal_after_span + normal_cadence_ns - 1) // normal_cadence_ns
    ) * normal_cadence_ns
    phases = (
        Phase(
            1,
            PhaseName.NORMAL,
            start_monotonic_ns,
            boundary_start,
            normal_cadence_seconds,
            normal_tolerance_seconds,
        ),
        Phase(
            2,
            PhaseName.BOUNDARY,
            boundary_start,
            boundary_end,
            boundary_cadence_seconds,
            boundary_tolerance_seconds,
        ),
        Phase(
            3,
            PhaseName.NORMAL_AFTER_BOUNDARY,
            boundary_end,
            None,
            normal_cadence_seconds,
            normal_tolerance_seconds,
        ),
    )
    schedule: list[ScheduledSample] = []
    for phase in phases:
        schedule.extend(
            _phase_samples(
                phase,
                final_due_monotonic_ns=final_due,
                sequence_start=len(schedule) + 1,
            )
        )
    return tuple(schedule)


def validate_completed_schedule(
    scheduled: Iterable[ScheduledSample],
    completed: Iterable[CompletedSample],
) -> ScheduleValidation:
    expected = tuple(scheduled)
    actual = tuple(completed)
    expected_ids = {item.sequence_id for item in expected}
    actual_ids = {item.schedule.sequence_id for item in actual}
    missed = tuple(sorted(expected_ids - actual_ids))
    ordered_ids = [item.schedule.sequence_id for item in actual]
    gaps = tuple(
        (left, right)
        for left, right in zip(ordered_ids, ordered_ids[1:])
        if right != left + 1
    )
    excessive = tuple(
        item.schedule.sequence_id
        for item in actual
        if item.lateness_seconds > item.schedule.tolerance_seconds
    )
    normal_lateness = [
        item.lateness_seconds
        for item in actual
        if item.schedule.phase_name is not PhaseName.BOUNDARY
    ]
    boundary_lateness = [
        item.lateness_seconds
        for item in actual
        if item.schedule.phase_name is PhaseName.BOUNDARY
    ]
    return ScheduleValidation(
        missed_scheduled_samples=missed,
        unexplained_sequence_gaps=gaps,
        excessive_lateness_samples=excessive,
        max_normal_lateness_seconds=max(normal_lateness, default=0.0),
        max_boundary_lateness_seconds=max(boundary_lateness, default=0.0),
    )

