"""Secret-free WAL archive diagnosis and physical continuity contracts.

Raw WAL names are accepted only as internal inputs.  Public results expose
counts and normalized ordinals so operational evidence cannot become a WAL
inventory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re
from typing import Iterable


WAL_SEGMENT = re.compile(r"^(?P<timeline>[0-9A-F]{8})(?P<log>[0-9A-F]{8})(?P<segment>[0-9A-F]{8})$")


class PaperProductionWalArchiveFailureState(StrEnum):
    NO_ACTIVE_FAILURE = "NO_ACTIVE_FAILURE"
    HISTORICAL_FAILURE_ALREADY_RECOVERED = "HISTORICAL_FAILURE_ALREADY_RECOVERED"
    STALE_ACKNOWLEDGEMENT = "STALE_ACKNOWLEDGEMENT"
    RETRY_PENDING = "RETRY_PENDING"
    ARCHIVE_DESTINATION_MISSING_ARTIFACT = "ARCHIVE_DESTINATION_MISSING_ARTIFACT"
    ARCHIVE_SOURCE_PENDING = "ARCHIVE_SOURCE_PENDING"
    ARCHIVE_PUBLICATION_FAILURE = "ARCHIVE_PUBLICATION_FAILURE"
    ARCHIVE_PERMISSION_FAILURE = "ARCHIVE_PERMISSION_FAILURE"
    PHYSICAL_WAL_GAP_RECOVERABLE = "PHYSICAL_WAL_GAP_RECOVERABLE"
    PHYSICAL_WAL_GAP_UNRECOVERABLE = "PHYSICAL_WAL_GAP_UNRECOVERABLE"
    MONITORING_CLASSIFICATION_DEFECT = "MONITORING_CLASSIFICATION_DEFECT"
    SAFE_DIAGNOSIS_UNAVAILABLE = "SAFE_DIAGNOSIS_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class PaperProductionWalArchiveContinuityResult:
    required_range_known: bool
    required_start_ordinal: int | None
    required_end_ordinal: int | None
    required_segment_count: int
    archive_artifact_coverage_count: int
    missing_required_segment_count: int
    source_recoverable_missing_count: int
    base_backup_chain_contiguous: bool
    physical_gap: bool
    unrecoverable_physical_gap: bool


@dataclass(frozen=True, slots=True)
class PaperProductionWalArchiveFailureDiagnosis:
    state: PaperProductionWalArchiveFailureState
    historical_failure_count: int
    active_unresolved_failure_count: int
    failure_retried_and_recovered: bool
    monitoring_classification_defect: bool
    stale_acknowledgement: bool
    retry_pending: bool
    finding_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PaperProductionWalArchiveHealth:
    archive_mode: bool
    wal_level_class: str
    historical_failure_count: int
    active_unresolved_failure_count: int
    pending_archive_count: int
    missing_required_segment_count: int
    physical_gap: bool
    archive_progressing: bool
    last_success_age_seconds: int | None
    base_backup_chain_contiguous: bool
    oldest_recoverable_point: datetime | None
    newest_recoverable_point: datetime | None
    continuous_window_seconds: int
    health: str
    finding_codes: tuple[str, ...]


def wal_segment_identity(name: str) -> tuple[int, int] | None:
    """Return ``(timeline, ordinal)`` for a regular 16 MiB WAL segment."""
    match = WAL_SEGMENT.fullmatch(name)
    if match is None:
        return None
    return (
        int(match.group("timeline"), 16),
        int(match.group("log"), 16) * 256 + int(match.group("segment"), 16),
    )


def wal_lsn_ordinal(lsn: str, *, segment_size_bytes: int = 16 * 1024 * 1024) -> int:
    if segment_size_bytes <= 0 or 0x100000000 % segment_size_bytes:
        raise ValueError("INVALID_WAL_SEGMENT_SIZE")
    match = re.fullmatch(r"([0-9A-F]+)/([0-9A-F]{1,8})", lsn.upper())
    if match is None:
        raise ValueError("INVALID_LSN")
    segments_per_log = 0x100000000 // segment_size_bytes
    return int(match.group(1), 16) * segments_per_log + int(match.group(2), 16) // segment_size_bytes


def inspect_wal_continuity(
    *,
    timeline: int | None,
    base_start_lsn: str | None,
    latest_archived_segment: str | None,
    base_wal_segments: Iterable[str],
    archive_wal_segments: Iterable[str],
    source_wal_segments: Iterable[str] = (),
    segment_size_bytes: int = 16 * 1024 * 1024,
) -> PaperProductionWalArchiveContinuityResult:
    if timeline is None or base_start_lsn is None or latest_archived_segment is None:
        return PaperProductionWalArchiveContinuityResult(False, None, None, 0, 0, 0, 0, False, False, False)
    latest = wal_segment_identity(latest_archived_segment)
    if latest is None or latest[0] != timeline:
        return PaperProductionWalArchiveContinuityResult(False, None, None, 0, 0, 0, 0, False, False, False)
    start = wal_lsn_ordinal(base_start_lsn, segment_size_bytes=segment_size_bytes)
    end = latest[1]
    if end < start:
        return PaperProductionWalArchiveContinuityResult(False, start, end, 0, 0, 0, 0, False, False, False)

    def ordinals(names: Iterable[str]) -> set[int]:
        result: set[int] = set()
        for name in names:
            identity = wal_segment_identity(name)
            if identity is not None and identity[0] == timeline:
                result.add(identity[1])
        return result

    base = ordinals(base_wal_segments)
    archive = ordinals(archive_wal_segments)
    source = ordinals(source_wal_segments)
    required = set(range(start, end + 1))
    missing = required - base - archive
    recoverable = missing & source
    unrecoverable = missing - source
    return PaperProductionWalArchiveContinuityResult(
        True, start, end, len(required), len(required & archive), len(missing),
        len(recoverable), not missing, bool(missing), bool(unrecoverable),
    )


def diagnose_wal_archive_failure(
    *,
    historical_failure_count: int,
    pending_archive_count: int,
    export_backlog_count: int,
    destination_accessible: bool,
    continuity: PaperProductionWalArchiveContinuityResult,
    last_failed_segment: str | None,
    last_archived_segment: str | None,
    failed_artifact_present: bool,
    failed_ack_present: bool,
    publication_error: bool = False,
    permission_error: bool = False,
) -> PaperProductionWalArchiveFailureDiagnosis:
    findings: list[str] = []
    recovered = bool(
        historical_failure_count
        and last_failed_segment
        and last_archived_segment
        and (last_failed_segment == last_archived_segment or failed_artifact_present)
        and continuity.base_backup_chain_contiguous
    )
    if permission_error or not destination_accessible:
        state = PaperProductionWalArchiveFailureState.ARCHIVE_PERMISSION_FAILURE
        findings.append("WAL_ARCHIVE_PERMISSION_FAILURE")
    elif publication_error:
        state = PaperProductionWalArchiveFailureState.ARCHIVE_PUBLICATION_FAILURE
        findings.append("WAL_ARCHIVE_PUBLICATION_FAILURE")
    elif continuity.unrecoverable_physical_gap:
        state = PaperProductionWalArchiveFailureState.PHYSICAL_WAL_GAP_UNRECOVERABLE
        findings.append("WAL_ARCHIVE_PHYSICAL_GAP_UNRECOVERABLE")
    elif continuity.physical_gap and continuity.source_recoverable_missing_count == continuity.missing_required_segment_count:
        state = PaperProductionWalArchiveFailureState.PHYSICAL_WAL_GAP_RECOVERABLE
        findings.append("WAL_ARCHIVE_PHYSICAL_GAP_RECOVERABLE")
    elif pending_archive_count or export_backlog_count:
        state = PaperProductionWalArchiveFailureState.RETRY_PENDING
        findings.append("WAL_ARCHIVE_RETRY_PENDING")
    elif not continuity.required_range_known:
        state = PaperProductionWalArchiveFailureState.SAFE_DIAGNOSIS_UNAVAILABLE
        findings.append("WAL_ARCHIVE_SAFE_DIAGNOSIS_UNAVAILABLE")
    elif historical_failure_count and recovered and failed_ack_present:
        state = PaperProductionWalArchiveFailureState.STALE_ACKNOWLEDGEMENT
        findings.extend(("WAL_ARCHIVE_STALE_ACKNOWLEDGEMENT", "WAL_ARCHIVE_HISTORICAL_FAILURE_RECOVERED"))
    elif historical_failure_count and recovered:
        state = PaperProductionWalArchiveFailureState.HISTORICAL_FAILURE_ALREADY_RECOVERED
        findings.append("WAL_ARCHIVE_HISTORICAL_FAILURE_RECOVERED")
    elif historical_failure_count and continuity.base_backup_chain_contiguous:
        state = PaperProductionWalArchiveFailureState.MONITORING_CLASSIFICATION_DEFECT
        findings.append("WAL_ARCHIVE_MONITORING_CLASSIFICATION_DEFECT")
    else:
        state = PaperProductionWalArchiveFailureState.NO_ACTIVE_FAILURE
    active = int(state not in {
        PaperProductionWalArchiveFailureState.NO_ACTIVE_FAILURE,
        PaperProductionWalArchiveFailureState.HISTORICAL_FAILURE_ALREADY_RECOVERED,
        PaperProductionWalArchiveFailureState.STALE_ACKNOWLEDGEMENT,
        PaperProductionWalArchiveFailureState.MONITORING_CLASSIFICATION_DEFECT,
    })
    if not active:
        findings.append("WAL_ARCHIVE_HEALTHY")
    return PaperProductionWalArchiveFailureDiagnosis(
        state, historical_failure_count, active, recovered,
        state is PaperProductionWalArchiveFailureState.MONITORING_CLASSIFICATION_DEFECT,
        state is PaperProductionWalArchiveFailureState.STALE_ACKNOWLEDGEMENT,
        state is PaperProductionWalArchiveFailureState.RETRY_PENDING,
        tuple(dict.fromkeys(findings)),
    )


def build_wal_archive_health(
    *,
    archive_mode: bool,
    wal_level_class: str,
    diagnosis: PaperProductionWalArchiveFailureDiagnosis,
    continuity: PaperProductionWalArchiveContinuityResult,
    pending_archive_count: int,
    archive_progressing: bool,
    last_success_age_seconds: int | None,
    oldest_recoverable_point: datetime | None,
    newest_recoverable_point: datetime | None,
) -> PaperProductionWalArchiveHealth:
    window = 0
    if oldest_recoverable_point and newest_recoverable_point:
        window = max(0, int((newest_recoverable_point - oldest_recoverable_point).total_seconds()))
    healthy = all((archive_mode, wal_level_class == "REPLICA_OR_HIGHER", diagnosis.active_unresolved_failure_count == 0,
                   pending_archive_count == 0, continuity.base_backup_chain_contiguous, archive_progressing))
    findings = list(diagnosis.finding_codes)
    if healthy and window < 86400:
        findings.append("PITR_WINDOW_ACCUMULATING")
    return PaperProductionWalArchiveHealth(
        archive_mode, wal_level_class, diagnosis.historical_failure_count,
        diagnosis.active_unresolved_failure_count, pending_archive_count,
        continuity.missing_required_segment_count, continuity.physical_gap,
        archive_progressing, last_success_age_seconds,
        continuity.base_backup_chain_contiguous, oldest_recoverable_point,
        newest_recoverable_point, window, "PASS" if healthy else "FAIL",
        tuple(dict.fromkeys(findings)),
    )


def validate_fresh_progression(
    *, snapshot_a_time: datetime, snapshot_b_time: datetime,
    window_a_seconds: int, window_b_seconds: int,
    newest_a_ordinal: int, newest_b_ordinal: int,
) -> bool:
    return (
        snapshot_b_time > snapshot_a_time
        and window_b_seconds >= window_a_seconds
        and newest_b_ordinal >= newest_a_ordinal
        and (newest_b_ordinal > newest_a_ordinal or snapshot_b_time > snapshot_a_time)
    )


__all__ = [name for name in globals() if not name.startswith("_")]
