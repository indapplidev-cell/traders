"""Fail-closed production backup/PITR catalog, retention, and health controls.

The module contains no credentials or connection URIs.  Production execution
is delegated to the bounded CLI in ``scripts/production_backup.py``; these
objects own validation, atomic metadata publication, retention safety, and the
future PAPER recovery gate.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Final, Iterable, Mapping, Sequence


POSTGRESQL_MAJOR: Final = 16
PRODUCTION_SCHEMA_HEAD: Final = "0008_engine_orchestrator_freshness_retry"
TARGET_RPO: Final = timedelta(minutes=15)
TARGET_RTO: Final = timedelta(hours=2)
MAX_LOGICAL_BACKUP_AGE: Final = timedelta(hours=24)
MIN_VALID_LOGICAL_BACKUPS: Final = 2
MIN_PITR_WINDOW: Final = timedelta(hours=24)
RESTORE_REHEARSAL_CADENCE: Final = timedelta(days=30)
PITR_REHEARSAL_CADENCE: Final = timedelta(days=90)
PROJECT_OPERATOR_ROLE: Final = "TRADERS_LOCAL_OPERATOR"
RECOVERY_APPROVAL_ROLE: Final = "TRADERS_LOCAL_OPERATOR"
CATALOG_LIMIT: Final = 128
RETENTION_DELETE_BATCH: Final = 8
MIN_FREE_BYTES: Final = 2 * 1024**3
TASK_BASE_HEAD: Final = "3e4ec00ee2a6f7a24dceb93f00f14a8890e0fd34"
TASK_BASE_TREE: Final = "ff790a81f9b017ed21825f488c9811e040172c33"
REQUIRED_EVIDENCE_HASHES: Final[Mapping[str, str]] = {
    "SECURITY_REMEDIATION_RETRY": "afce8eae9d58135a3d9d1e5591cbb0ede5546a90030a9885fb9427d4e6edeaa0",
    "SINGLE_CYCLE_CANARY_RETRY_02": "c9ef780f6c16e1a06564d4b879c416df609821dae9ccf141949bceefa44b22b4",
    "BOUNDED_SEQUENCE_CANARY": "d97cab0ec98de5cbab640da5548789efbd5a3bc4f8335cc2b51e4f9ed1618776",
    "OPERATOR_CONTROLLED_RUNNER": "18e7b78381c0bc0de043c96c870c35ebbcb7cfb665f233bd1d5a23d6fee517db",
    "PRODUCTION_RUNTIME_READINESS_REVIEW": "7754627e41a7e78078674602caad8cf66231297008727c1b4deb5718b206e1ad",
    "BACKUP_RESTORE_RECONCILIATION_READINESS": "0c3ec914a435bf5f6da8d616e2375190bcec80066e6e63c9b1b4474bf67734ec",
    "PRODUCTION_BACKUP_PITR_INFRASTRUCTURE_REMEDIATION": "344611241bef7a19c911026c66d953d153fbaf843794a9fde00b8fe01a1448fc",
}
ARTIFACT_ID = re.compile(r"^(logical|base)-[0-9]{8}T[0-9]{6}Z-[a-f0-9]{8}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(root: Path) -> tuple[str, int]:
    digest = sha256()
    total = 0
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise ValueError("EMPTY_BASE_BACKUP")
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        size = path.stat().st_size
        total += size
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(size.to_bytes(8, "big"))
        digest.update(bytes.fromhex(file_sha256(path)))
    return digest.hexdigest(), total


@dataclass(frozen=True, slots=True)
class RecoveryPolicy:
    target_rpo_minutes: int = 15
    target_rto_minutes: int = 120
    max_logical_backup_age_hours: int = 24
    min_valid_logical_backups: int = 2
    min_pitr_window_hours: int = 24
    restore_rehearsal_cadence_days: int = 30
    pitr_rehearsal_cadence_days: int = 90
    operator_role: str = PROJECT_OPERATOR_ROLE
    recovery_approval_role: str = RECOVERY_APPROVAL_ROLE
    two_person_approval_required_for_paper: bool = False

    def __post_init__(self) -> None:
        numeric = (
            self.target_rpo_minutes,
            self.target_rto_minutes,
            self.max_logical_backup_age_hours,
            self.min_valid_logical_backups,
            self.min_pitr_window_hours,
            self.restore_rehearsal_cadence_days,
            self.pitr_rehearsal_cadence_days,
        )
        if any(isinstance(value, bool) or value <= 0 for value in numeric):
            raise ValueError("INVALID_RECOVERY_POLICY")
        if self.operator_role != PROJECT_OPERATOR_ROLE:
            raise ValueError("INVALID_OPERATOR_ROLE")
        if self.recovery_approval_role != RECOVERY_APPROVAL_ROLE:
            raise ValueError("INVALID_APPROVAL_ROLE")


POLICY: Final = RecoveryPolicy()


@dataclass(frozen=True, slots=True)
class BackupManifest:
    artifact_id: str
    artifact_type: str
    created_at: str
    postgresql_major: int
    source_class: str
    source_alembic_head: str
    format: str
    size_bytes: int
    sha256: str
    tool_version: str
    verification_status: str
    retention_class: str
    relative_path: str
    restore_list_valid: bool = False
    recovery_anchor_valid: bool = False
    wal_start: str = "UNRECORDED"
    wal_stop: str = "UNRECORDED"

    def __post_init__(self) -> None:
        if not ARTIFACT_ID.fullmatch(self.artifact_id):
            raise ValueError("INVALID_ARTIFACT_ID")
        if self.artifact_type not in {"LOGICAL", "BASE"}:
            raise ValueError("INVALID_ARTIFACT_TYPE")
        parse_utc(self.created_at)
        if self.postgresql_major != POSTGRESQL_MAJOR:
            raise ValueError("POSTGRES_MAJOR_MISMATCH")
        if self.source_class != "PRODUCTION":
            raise ValueError("SOURCE_NOT_PRODUCTION")
        if self.source_alembic_head != PRODUCTION_SCHEMA_HEAD:
            raise ValueError("SOURCE_SCHEMA_MISMATCH")
        if self.size_bytes <= 0 or not SHA256.fullmatch(self.sha256):
            raise ValueError("INVALID_INTEGRITY_METADATA")
        if self.verification_status != "PUBLISHED":
            raise ValueError("UNVERIFIED_ARTIFACT")
        if self.retention_class != "PAPER_FIRST_MILESTONE_24H_MINIMUM":
            raise ValueError("INVALID_RETENTION_CLASS")
        posix = PurePosixPath(self.relative_path)
        windows = PureWindowsPath(self.relative_path)
        if posix.is_absolute() or windows.is_absolute() or ".." in posix.parts:
            raise ValueError("UNSAFE_RELATIVE_PATH")
        if self.artifact_type == "LOGICAL" and not self.restore_list_valid:
            raise ValueError("LOGICAL_RESTORE_LIST_REQUIRED")
        if self.artifact_type == "BASE" and not self.recovery_anchor_valid:
            raise ValueError("BASE_RECOVERY_ANCHOR_REQUIRED")

    def to_json(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_json(cls, value: Mapping[str, object]) -> "BackupManifest":
        expected = set(cls.__dataclass_fields__)
        if set(value) != expected:
            raise ValueError("MANIFEST_SHAPE_MISMATCH")
        return cls(**value)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class CatalogHealth:
    healthy: bool
    verified_entries: int
    valid_logical_backups: int
    valid_base_backups: int
    missing_artifacts: tuple[str, ...]
    checksum_mismatches: tuple[str, ...]
    orphan_manifests: tuple[str, ...]
    unmanifested_artifacts: tuple[str, ...]
    error_code: str


@dataclass(frozen=True, slots=True)
class RetentionDecision:
    candidates: tuple[str, ...]
    protected: tuple[str, ...]
    dry_run_required: bool
    bounded: bool


@dataclass(frozen=True, slots=True)
class BackupPitrHealth:
    ready: bool
    logical_backup_count: int
    last_valid_logical_backup_age_seconds: int | None
    logical_backup_bootstrap_exception: bool
    valid_base_backup: bool
    wal_archive_progressing: bool
    wal_archive_failure_count: int
    pitr_window_seconds: int
    catalog_healthy: bool
    destination_free_space_bytes: int
    last_restore_rehearsal_age_seconds: int | None
    last_pitr_rehearsal_age_seconds: int | None
    failed_gates: tuple[str, ...]


def atomic_json_write(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".in_progress")
    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with temporary.open("wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def load_manifest(path: Path) -> BackupManifest:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("MANIFEST_NOT_OBJECT")
    return BackupManifest.from_json(value)


def load_catalog(root: Path) -> tuple[BackupManifest, ...]:
    path = root / "catalog" / "catalog.json"
    if not path.exists():
        return ()
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {"schema", "entries"}:
        raise ValueError("CATALOG_SHAPE_MISMATCH")
    if value["schema"] != "TRADERS_ML_BACKUP_CATALOG_V1":
        raise ValueError("CATALOG_SCHEMA_MISMATCH")
    entries = value["entries"]
    if not isinstance(entries, list) or len(entries) > CATALOG_LIMIT:
        raise ValueError("CATALOG_BOUNDS_FAILURE")
    manifests = tuple(BackupManifest.from_json(entry) for entry in entries)
    if len({item.artifact_id for item in manifests}) != len(manifests):
        raise ValueError("DUPLICATE_ARTIFACT_ID")
    return manifests


def publish_manifest(root: Path, manifest: BackupManifest) -> None:
    entries = list(load_catalog(root))
    if any(item.artifact_id == manifest.artifact_id for item in entries):
        raise ValueError("DUPLICATE_ARTIFACT_ID")
    artifact = root / manifest.relative_path
    if not artifact.exists():
        raise ValueError("ARTIFACT_MISSING")
    actual_hash, actual_size = (
        tree_sha256(artifact) if artifact.is_dir()
        else (file_sha256(artifact), artifact.stat().st_size)
    )
    if actual_hash != manifest.sha256 or actual_size != manifest.size_bytes:
        raise ValueError("ARTIFACT_INTEGRITY_MISMATCH")
    manifest_path = root / "catalog" / "manifests" / f"{manifest.artifact_id}.json"
    atomic_json_write(manifest_path, manifest.to_json())
    entries.append(manifest)
    entries.sort(key=lambda item: (item.created_at, item.artifact_id))
    if len(entries) > CATALOG_LIMIT:
        raise ValueError("CATALOG_LIMIT_REQUIRES_RETENTION")
    atomic_json_write(
        root / "catalog" / "catalog.json",
        {"schema": "TRADERS_ML_BACKUP_CATALOG_V1", "entries": [item.to_json() for item in entries]},
    )


def catalog_health(root: Path) -> CatalogHealth:
    try:
        entries = load_catalog(root)
    except (OSError, ValueError, json.JSONDecodeError):
        return CatalogHealth(False, 0, 0, 0, (), (), (), (), "CATALOG_INVALID")
    missing: list[str] = []
    mismatches: list[str] = []
    orphan: list[str] = []
    unmanifested: list[str] = []
    ids = {item.artifact_id for item in entries}
    for item in entries:
        artifact = root / item.relative_path
        manifest_path = root / "catalog" / "manifests" / f"{item.artifact_id}.json"
        if not artifact.exists():
            missing.append(item.artifact_id)
            continue
        if not manifest_path.is_file():
            orphan.append(item.artifact_id)
            continue
        try:
            if load_manifest(manifest_path) != item:
                mismatches.append(item.artifact_id)
                continue
            actual_hash, actual_size = (
                tree_sha256(artifact) if artifact.is_dir()
                else (file_sha256(artifact), artifact.stat().st_size)
            )
            if actual_hash != item.sha256 or actual_size != item.size_bytes:
                mismatches.append(item.artifact_id)
        except (OSError, ValueError, json.JSONDecodeError):
            mismatches.append(item.artifact_id)
    manifest_root = root / "catalog" / "manifests"
    if manifest_root.exists():
        orphan.extend(
            path.stem for path in manifest_root.glob("*.json") if path.stem not in ids
        )
    governed = {(root / item.relative_path).resolve() for item in entries}
    for directory in (root / "logical", root / "base"):
        if directory.exists():
            unmanifested.extend(
                path.name for path in directory.iterdir()
                if ".in_progress" not in path.name and path.resolve() not in governed
            )
    failures = missing or mismatches or orphan or unmanifested
    valid = len(entries) - len(set(missing + mismatches + orphan))
    return CatalogHealth(
        not failures, max(0, valid),
        sum(item.artifact_type == "LOGICAL" for item in entries if item.artifact_id not in missing + mismatches + orphan),
        sum(item.artifact_type == "BASE" for item in entries if item.artifact_id not in missing + mismatches + orphan),
        tuple(sorted(set(missing))), tuple(sorted(set(mismatches))),
        tuple(sorted(set(orphan))), tuple(sorted(set(unmanifested))),
        "NONE" if not failures else "CATALOG_INCONSISTENT",
    )


def retention_plan(
    entries: Sequence[BackupManifest], *, now: datetime, max_age: timedelta = timedelta(days=35)
) -> RetentionDecision:
    ordered = sorted(entries, key=lambda item: (item.created_at, item.artifact_id))
    logical = [item for item in ordered if item.artifact_type == "LOGICAL"]
    bases = [item for item in ordered if item.artifact_type == "BASE"]
    protected = {item.artifact_id for item in logical[-MIN_VALID_LOGICAL_BACKUPS:]}
    if bases:
        protected.add(bases[-1].artifact_id)
    cutoff = now.astimezone(timezone.utc) - max_age
    candidates = [
        item.artifact_id for item in ordered
        if item.artifact_id not in protected and parse_utc(item.created_at) < cutoff
    ][:RETENTION_DELETE_BATCH]
    return RetentionDecision(tuple(candidates), tuple(sorted(protected)), True, True)


def apply_retention(root: Path, decision: RetentionDecision, *, dry_run_ack: bool) -> tuple[str, ...]:
    if not dry_run_ack or not decision.dry_run_required or not decision.bounded:
        raise ValueError("RETENTION_DRY_RUN_ACK_REQUIRED")
    entries = list(load_catalog(root))
    governed = {item.artifact_id: item for item in entries}
    if any(item not in governed or item in decision.protected for item in decision.candidates):
        raise ValueError("RETENTION_TARGET_NOT_SAFE")
    deleted: list[str] = []
    for artifact_id in decision.candidates[:RETENTION_DELETE_BATCH]:
        item = governed[artifact_id]
        artifact = root / item.relative_path
        if artifact.is_dir():
            for child in sorted(artifact.rglob("*"), reverse=True):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
            artifact.rmdir()
        elif artifact.exists():
            artifact.unlink()
        manifest_path = root / "catalog" / "manifests" / f"{artifact_id}.json"
        if manifest_path.exists():
            manifest_path.unlink()
        deleted.append(artifact_id)
    retained = [item for item in entries if item.artifact_id not in deleted]
    atomic_json_write(
        root / "catalog" / "catalog.json",
        {"schema": "TRADERS_ML_BACKUP_CATALOG_V1", "entries": [item.to_json() for item in retained]},
    )
    return tuple(deleted)


def evaluate_health(
    *, root: Path, now: datetime, wal_archive_progressing: bool,
    wal_archive_failure_count: int, pitr_window: timedelta,
    last_restore_rehearsal: datetime | None, last_pitr_rehearsal: datetime | None,
) -> BackupPitrHealth:
    health = catalog_health(root)
    entries = load_catalog(root) if health.healthy else ()
    logical = [item for item in entries if item.artifact_type == "LOGICAL"]
    bases = [item for item in entries if item.artifact_type == "BASE"]
    age = None if not logical else int((now - max(parse_utc(item.created_at) for item in logical)).total_seconds())
    bootstrap = len(logical) == 1 and age is not None and age <= int(MAX_LOGICAL_BACKUP_AGE.total_seconds())
    free = os.statvfs(root).f_bavail * os.statvfs(root).f_frsize if hasattr(os, "statvfs") else 0
    if os.name == "nt":
        import shutil
        free = shutil.disk_usage(root).free
    failed: list[str] = []
    if not health.healthy:
        failed.append("CATALOG_INCONSISTENT")
    if not logical:
        failed.append("NO_VALID_LOGICAL_BACKUP")
    elif age is None or age > int(MAX_LOGICAL_BACKUP_AGE.total_seconds()):
        failed.append("LOGICAL_BACKUP_TOO_OLD")
    if len(logical) < MIN_VALID_LOGICAL_BACKUPS and not bootstrap:
        failed.append("MIN_LOGICAL_BACKUPS_NOT_MET")
    if not bases:
        failed.append("BASE_BACKUP_MISSING")
    if not wal_archive_progressing:
        failed.append("WAL_ARCHIVE_NOT_PROGRESSING")
    if wal_archive_failure_count:
        failed.append("WAL_ARCHIVE_FAILURE")
    if pitr_window < MIN_PITR_WINDOW:
        failed.append("PITR_WINDOW_BELOW_TARGET")
    if free < MIN_FREE_BYTES:
        failed.append("BACKUP_DESTINATION_LOW_SPACE")
    if last_restore_rehearsal is None:
        failed.append("RESTORE_REHEARSAL_MISSING")
    if last_pitr_rehearsal is None:
        failed.append("PITR_REHEARSAL_MISSING")
    return BackupPitrHealth(
        not failed, len(logical), age, bootstrap, bool(bases),
        wal_archive_progressing, wal_archive_failure_count,
        int(pitr_window.total_seconds()), health.healthy, free,
        None if last_restore_rehearsal is None else int((now - last_restore_rehearsal).total_seconds()),
        None if last_pitr_rehearsal is None else int((now - last_pitr_rehearsal).total_seconds()),
        tuple(failed),
    )


def future_paper_enablement_gate(health: BackupPitrHealth, *, reconciliation_available: bool) -> bool:
    return health.ready and reconciliation_available


def safe_artifact_id(kind: str, now: datetime, nonce: str) -> str:
    if kind not in {"logical", "base"} or not re.fullmatch(r"[a-f0-9]{8}", nonce):
        raise ValueError("INVALID_ARTIFACT_ID_INPUT")
    return f"{kind}-{now.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}-{nonce}"


__all__ = [name for name in globals() if not name.startswith("_")]
