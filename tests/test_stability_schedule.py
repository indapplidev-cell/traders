from __future__ import annotations

from app.observability.stability_models import CompletedSample, PhaseName
from app.observability.stability_schedule import (
    NANOSECONDS,
    build_phase_aware_schedule,
    validate_completed_schedule,
)


def plan():
    return build_phase_aware_schedule(
        start_monotonic_ns=100 * NANOSECONDS,
        boundary_monotonic_ns=1900 * NANOSECONDS,
        target_duration_seconds=4560,
    )


def complete(schedule, *, lateness_by_id=None, omit=()):
    lateness_by_id = lateness_by_id or {}
    return [
        CompletedSample(
            item,
            item.scheduled_due_monotonic_ns
            + int(lateness_by_id.get(item.sequence_id, 0) * NANOSECONDS),
            item.scheduled_due_monotonic_ns
            + int(lateness_by_id.get(item.sequence_id, 0) * NANOSECONDS),
            lateness_by_id.get(item.sequence_id, 0),
        )
        for item in schedule
        if item.sequence_id not in omit
    ]


def test_normal_cadence_has_no_gaps():
    schedule = [item for item in plan() if item.phase_name is PhaseName.NORMAL]
    assert validate_completed_schedule(schedule, complete(schedule)).accepted


def test_boundary_cadence_has_no_gaps():
    schedule = [item for item in plan() if item.phase_name is PhaseName.BOUNDARY]
    assert validate_completed_schedule(schedule, complete(schedule)).accepted


def test_normal_to_boundary_has_no_false_gap():
    schedule = plan()
    transition = next(i for i, item in enumerate(schedule) if item.phase_name is PhaseName.BOUNDARY)
    assert validate_completed_schedule(schedule, complete(schedule)).unexplained_sequence_gaps == ()
    assert schedule[transition].phase_id != schedule[transition - 1].phase_id


def test_boundary_to_normal_has_no_false_gap():
    schedule = plan()
    transition = next(
        i for i, item in enumerate(schedule)
        if item.phase_name is PhaseName.NORMAL_AFTER_BOUNDARY
    )
    assert schedule[transition].sequence_id == schedule[transition - 1].sequence_id + 1
    assert validate_completed_schedule(schedule, complete(schedule)).accepted


def test_9885_second_transition_interval_is_not_gap():
    schedule = plan()
    completed = complete(schedule)
    transition = next(
        i for i, item in enumerate(completed)
        if item.schedule.phase_name is PhaseName.BOUNDARY
    )
    previous = completed[transition - 1]
    current = completed[transition]
    completed[transition - 1] = CompletedSample(
        previous.schedule,
        previous.started_monotonic_ns,
        current.completed_monotonic_ns - int(9.885 * NANOSECONDS),
        previous.lateness_seconds,
    )
    assert validate_completed_schedule(schedule, completed).accepted


def test_shorter_transition_interval_is_not_gap():
    schedule = plan()
    assert validate_completed_schedule(schedule, complete(schedule)).accepted


def test_missing_sequence_is_detected():
    schedule = plan()
    validation = validate_completed_schedule(schedule, complete(schedule, omit={12}))
    assert validation.missed_scheduled_samples == (12,)
    assert validation.unexplained_sequence_gaps == ((11, 13),)


def test_excessive_normal_lateness_is_detected():
    schedule = plan()
    normal = next(item for item in schedule if item.phase_name is PhaseName.NORMAL)
    validation = validate_completed_schedule(
        schedule, complete(schedule, lateness_by_id={normal.sequence_id: 10.001})
    )
    assert normal.sequence_id in validation.excessive_lateness_samples


def test_excessive_boundary_lateness_is_detected():
    schedule = plan()
    boundary = next(item for item in schedule if item.phase_name is PhaseName.BOUNDARY)
    validation = validate_completed_schedule(
        schedule, complete(schedule, lateness_by_id={boundary.sequence_id: 4.001})
    )
    assert boundary.sequence_id in validation.excessive_lateness_samples


def test_wall_clock_jump_cannot_affect_monotonic_schedule():
    first = plan()
    second = plan()
    assert first == second


def test_request_duration_does_not_accumulate_schedule_drift():
    schedule = plan()
    normal = [item for item in schedule if item.phase_name is PhaseName.NORMAL]
    due_deltas = [
        (right.scheduled_due_monotonic_ns - left.scheduled_due_monotonic_ns)
        / NANOSECONDS
        for left, right in zip(normal, normal[1:])
    ]
    assert set(due_deltas) == {15.0}


def test_sequence_ids_stable_across_transitions():
    schedule = plan()
    assert [item.sequence_id for item in schedule] == list(range(1, len(schedule) + 1))

