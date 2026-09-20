"""Dependency-light, canonical WAL/PITR lineage observation.

Recovery supervision must be able to verify backup durability even when an
unrelated trading-profile configuration is fail-closed.  This module therefore
contains no HTTP, ORM, strategy, risk, or trading-profile imports.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config.yaml_authority import RUNTIME_POLICY
from app.engine_safety.production_wal_archive import inspect_wal_continuity, wal_segment_identity


MINIMUM_PITR_WINDOW_SECONDS = RUNTIME_POLICY.paper_readiness.minimum_pitr_window_seconds
MAX_WAL_DAEMON_AGE_SECONDS = RUNTIME_POLICY.paper_readiness.wal_daemon_max_age_seconds
MAX_ARTIFACT_FUTURE_SKEW_SECONDS = RUNTIME_POLICY.paper_readiness.artifact_future_skew_tolerance_seconds
MAX_JSON_BYTES = 16 * 1024
_START_WAL = re.compile(r"^START WAL LOCATION: (?P<lsn>[0-9A-F]+/[0-9A-F]+) \(file (?P<file>[0-9A-F]{24})\)$", re.MULTILINE)
_START_TIMELINE = re.compile(r"^START TIMELINE: (?P<timeline>[0-9]+)$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class PitrLineageObservation:
    wal_ready: bool = False
    pitr_ready: bool = False
    lineage_valid: bool = False
    lineage_start: datetime | None = None
    lineage_end: datetime | None = None
    contiguous_duration_seconds: int = 0
    physical_gap: bool | None = None
    wal_state: str = "DEGRADED"
    wal_reason_code: str = "WAL_ARCHIVE_DESTINATION_UNAVAILABLE"
    pitr_state: str = "NOT_EVALUATED"
    pitr_reason_code: str = "PITR_VERIFICATION_PENDING"


def _json_object(path: Path, *, attempts: int = 3) -> dict[str, object]:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            if not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
                raise ValueError("PRODUCTION_OBSERVATION_ARTIFACT_INVALID")
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("PRODUCTION_OBSERVATION_ARTIFACT_INVALID")
            return value
        except (OSError, ValueError, json.JSONDecodeError) as error:
            last = error
            if attempt + 1 < attempts:
                time.sleep(0.01)
    assert last is not None
    raise last


def pitr_lineage(root: Path, now: datetime) -> PitrLineageObservation:
    """Return the same fail-closed durability facts for API and supervisor."""
    try:
        daemon = _json_object(root / "catalog" / "wal_ack_daemon_state.json")
        updated = datetime.fromisoformat(str(daemon["updated_at"]).replace("Z", "+00:00"))
        daemon_ready = (
            daemon.get("schema") in {"TRADERS_ML_WAL_ACK_DAEMON_STATE_V1", "TRADERS_ML_WAL_ACK_DAEMON_STATE_V2"}
            and daemon.get("status") == "RUNNING" and daemon.get("error_class") == "NONE"
            and daemon.get("export_backlog_count") == 0 and daemon.get("pending_archive_status_count") == 0
            and -MAX_ARTIFACT_FUTURE_SKEW_SECONDS <= (now - updated.astimezone(timezone.utc)).total_seconds() <= MAX_WAL_DAEMON_AGE_SECONDS
        )
        catalog = _json_object(root / "catalog" / "catalog.json")
        entries = catalog.get("entries")
        if catalog.get("schema") != "TRADERS_ML_BACKUP_CATALOG_V1" or not isinstance(entries, list):
            return PitrLineageObservation(pitr_state="BLOCKED", pitr_reason_code="PITR_BASE_BACKUP_INVALID")
        bases = [item for item in entries if isinstance(item, dict) and item.get("artifact_type") == "BASE" and item.get("source_class") == "PRODUCTION" and item.get("verification_status") == "PUBLISHED" and item.get("recovery_anchor_valid") is True]
        if not bases:
            return PitrLineageObservation(pitr_state="BLOCKED", pitr_reason_code="PITR_BASE_BACKUP_INVALID")
        base = max(bases, key=lambda item: str(item.get("created_at", "")))
        base_path = root / str(base.get("relative_path", ""))
        label = (base_path / "backup_label").read_text(encoding="utf-8")
        start, timeline = _START_WAL.search(label), _START_TIMELINE.search(label)
        archive = tuple(path.name for path in (root / "wal_archive").iterdir() if path.is_file() and wal_segment_identity(path.name) is not None)
        base_wal = tuple(path.name for path in (base_path / "pg_wal").iterdir() if path.is_file() and wal_segment_identity(path.name) is not None)
        if start is None or timeline is None or not archive:
            return PitrLineageObservation()
        latest = max(archive, key=lambda name: wal_segment_identity(name) or (-1, -1))
        continuity = inspect_wal_continuity(timeline=int(timeline.group("timeline")), base_start_lsn=start.group("lsn"), latest_archived_segment=latest, base_wal_segments=base_wal, archive_wal_segments=archive)
        oldest = datetime.fromisoformat(str(base["created_at"]).replace("Z", "+00:00"))
        newest = datetime.fromtimestamp((root / "wal_archive" / latest).stat().st_mtime, timezone.utc)
        window = max(0, int((newest - oldest.astimezone(timezone.utc)).total_seconds()))
        wal_ready = daemon_ready and continuity.base_backup_chain_contiguous
        lineage_valid = continuity.base_backup_chain_contiguous and not continuity.physical_gap
        wal_reason = "WAL_ARCHIVE_READY" if daemon_ready else ("WAL_ARCHIVE_STALE" if (now - updated.astimezone(timezone.utc)).total_seconds() > MAX_WAL_DAEMON_AGE_SECONDS else "WAL_ARCHIVER_FAILURE")
        pitr_ready = wal_ready and lineage_valid and window >= MINIMUM_PITR_WINDOW_SECONDS
        return PitrLineageObservation(wal_state="READY" if wal_ready else "DEGRADED", wal_reason_code=wal_reason if continuity.base_backup_chain_contiguous else "PITR_WAL_GAP", pitr_state="BLOCKED" if continuity.physical_gap else ("READY" if pitr_ready else "DEGRADED"), pitr_reason_code="PITR_WAL_GAP" if continuity.physical_gap else ("PITR_RECOVERY_READY" if pitr_ready else (wal_reason if not daemon_ready else "PITR_VERIFICATION_PENDING")), wal_ready=wal_ready, pitr_ready=pitr_ready, lineage_valid=lineage_valid, lineage_start=oldest.astimezone(timezone.utc), lineage_end=newest, contiguous_duration_seconds=window, physical_gap=continuity.physical_gap)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return PitrLineageObservation()
