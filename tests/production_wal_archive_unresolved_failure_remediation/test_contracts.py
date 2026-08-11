from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.engine_safety.production_wal_archive import (
    PaperProductionWalArchiveFailureState as State,
    build_wal_archive_health,
    diagnose_wal_archive_failure,
    inspect_wal_continuity,
    validate_fresh_progression,
    wal_lsn_ordinal,
    wal_segment_identity,
)


def segment(ordinal: int, timeline: int = 1) -> str:
    return f"{timeline:08X}{ordinal // 256:08X}{ordinal % 256:08X}"


@pytest.mark.parametrize("case", range(1200))
def test_deterministic_continuity_and_failure_matrix(case: int) -> None:
    start = 256 + case % 31
    width = 1 + case % 7
    required = [segment(value) for value in range(start, start + width)]
    gap_index = case % width
    gap = bool(case & 1)
    recoverable = gap and bool(case & 2)
    archive = required.copy()
    missing_name = archive.pop(gap_index) if gap else None
    source = [missing_name] if recoverable and missing_name else []
    continuity = inspect_wal_continuity(
        timeline=1,
        base_start_lsn=f"{start // 256:X}/{(start % 256) * 0x1000000:X}",
        latest_archived_segment=required[-1],
        base_wal_segments=(),
        archive_wal_segments=archive,
        source_wal_segments=source,
    )
    assert continuity.required_range_known
    assert continuity.required_segment_count == width
    assert continuity.missing_required_segment_count == int(gap)
    assert continuity.source_recoverable_missing_count == int(recoverable)
    assert continuity.base_backup_chain_contiguous is (not gap)
    diagnosis = diagnose_wal_archive_failure(
        historical_failure_count=65,
        pending_archive_count=0,
        export_backlog_count=0,
        destination_accessible=True,
        continuity=continuity,
        last_failed_segment=required[-1],
        last_archived_segment=required[-1],
        failed_artifact_present=not gap,
        failed_ack_present=False,
    )
    expected = (
        State.PHYSICAL_WAL_GAP_RECOVERABLE if recoverable
        else State.PHYSICAL_WAL_GAP_UNRECOVERABLE if gap
        else State.HISTORICAL_FAILURE_ALREADY_RECOVERED
    )
    assert diagnosis.state is expected
    assert diagnosis.active_unresolved_failure_count == int(gap)


def test_wal_identity_and_lsn_validation() -> None:
    assert wal_segment_identity("000000010000000A000000FF") == (1, 2815)
    assert wal_segment_identity("unsafe") is None
    assert wal_lsn_ordinal("A/FF000000") == 2815
    with pytest.raises(ValueError, match="INVALID_LSN"):
        wal_lsn_ordinal("not-an-lsn")


def complete_continuity():
    return inspect_wal_continuity(
        timeline=1, base_start_lsn="1/0", latest_archived_segment=segment(257),
        base_wal_segments=(segment(256),), archive_wal_segments=(segment(257),),
    )


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    (
        ({"pending_archive_count": 1}, State.RETRY_PENDING),
        ({"export_backlog_count": 1}, State.RETRY_PENDING),
        ({"destination_accessible": False}, State.ARCHIVE_PERMISSION_FAILURE),
        ({"permission_error": True}, State.ARCHIVE_PERMISSION_FAILURE),
        ({"publication_error": True}, State.ARCHIVE_PUBLICATION_FAILURE),
    ),
)
def test_active_failure_precedence(kwargs, expected) -> None:
    values = dict(
        historical_failure_count=65, pending_archive_count=0,
        export_backlog_count=0, destination_accessible=True,
        continuity=complete_continuity(), last_failed_segment=segment(257),
        last_archived_segment=segment(257), failed_artifact_present=True,
        failed_ack_present=False, publication_error=False, permission_error=False,
    )
    values.update(kwargs)
    result = diagnose_wal_archive_failure(**values)
    assert result.state is expected
    assert result.active_unresolved_failure_count == 1


def test_stale_acknowledgement_and_historical_counter_are_not_active() -> None:
    result = diagnose_wal_archive_failure(
        historical_failure_count=82, pending_archive_count=0,
        export_backlog_count=0, destination_accessible=True,
        continuity=complete_continuity(), last_failed_segment=segment(257),
        last_archived_segment=segment(257), failed_artifact_present=True,
        failed_ack_present=True,
    )
    assert result.state is State.STALE_ACKNOWLEDGEMENT
    assert result.historical_failure_count == 82
    assert result.active_unresolved_failure_count == 0


def test_monitoring_false_positive_is_distinct_from_history() -> None:
    result = diagnose_wal_archive_failure(
        historical_failure_count=82, pending_archive_count=0,
        export_backlog_count=0, destination_accessible=True,
        continuity=complete_continuity(), last_failed_segment=segment(258),
        last_archived_segment=segment(257), failed_artifact_present=False,
        failed_ack_present=False,
    )
    assert result.state is State.MONITORING_CLASSIFICATION_DEFECT
    assert result.monitoring_classification_defect
    assert result.active_unresolved_failure_count == 0


def test_health_pass_does_not_require_24_hours() -> None:
    continuity = complete_continuity()
    diagnosis = diagnose_wal_archive_failure(
        historical_failure_count=82, pending_archive_count=0,
        export_backlog_count=0, destination_accessible=True,
        continuity=continuity, last_failed_segment=segment(257),
        last_archived_segment=segment(257), failed_artifact_present=True,
        failed_ack_present=False,
    )
    now = datetime.now(timezone.utc)
    health = build_wal_archive_health(
        archive_mode=True, wal_level_class="REPLICA_OR_HIGHER",
        diagnosis=diagnosis, continuity=continuity, pending_archive_count=0,
        archive_progressing=True, last_success_age_seconds=3,
        oldest_recoverable_point=now - timedelta(hours=3),
        newest_recoverable_point=now,
    )
    assert health.health == "PASS"
    assert health.continuous_window_seconds == 10800
    assert "PITR_WINDOW_ACCUMULATING" in health.finding_codes


def test_fresh_snapshot_progression_and_same_snapshot_rejection() -> None:
    a = datetime(2026, 8, 11, 10, tzinfo=timezone.utc)
    b = a + timedelta(seconds=10)
    assert validate_fresh_progression(
        snapshot_a_time=a, snapshot_b_time=b, window_a_seconds=100,
        window_b_seconds=110, newest_a_ordinal=1, newest_b_ordinal=2,
    )
    assert not validate_fresh_progression(
        snapshot_a_time=a, snapshot_b_time=a, window_a_seconds=100,
        window_b_seconds=100, newest_a_ordinal=1, newest_b_ordinal=1,
    )


def test_safe_diagnosis_unavailable_fails_closed() -> None:
    continuity = inspect_wal_continuity(
        timeline=None, base_start_lsn=None, latest_archived_segment=None,
        base_wal_segments=(), archive_wal_segments=(),
    )
    result = diagnose_wal_archive_failure(
        historical_failure_count=0, pending_archive_count=0,
        export_backlog_count=0, destination_accessible=True,
        continuity=continuity, last_failed_segment=None,
        last_archived_segment=None, failed_artifact_present=False,
        failed_ack_present=False,
    )
    assert result.state is State.SAFE_DIAGNOSIS_UNAVAILABLE
    assert result.active_unresolved_failure_count == 1
