"""Bounded, no-secret production WAL archive diagnosis and retry utility."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_safety.production_backup import atomic_json_write, load_catalog, parse_utc
from app.engine_safety.production_wal_archive import (
    PaperProductionWalArchiveContinuityResult,
    PaperProductionWalArchiveFailureDiagnosis,
    build_wal_archive_health,
    diagnose_wal_archive_failure,
    inspect_wal_continuity,
    wal_segment_identity,
)
from scripts.production_backup import CONTAINER, SAFE_ROOT, OperationFailure, sync_wal
from app.config.yaml_authority import RUNTIME_POLICY
from app.engine_safety.recovery_state import RecoveryState


DB_USER = "traders_ml"
DB_NAME = "traders_ml"
SEGMENT_RE = re.compile(r"^[0-9A-F]{24}$")
HOST_ACK_ARCHIVE_COMMAND = (
    "if [ -f /var/lib/postgresql/wal_export/%f ]; then "
    "cmp -s %p /var/lib/postgresql/wal_export/%f; else "
    "mkdir -p /var/lib/postgresql/wal_export && "
    "cp %p /var/lib/postgresql/wal_export/%f; fi || exit 1; "
    "i=0; while [ $i -lt 300 ] && "
    "[ ! -f /var/lib/postgresql/wal_export/%f.ack ]; do "
    "sleep 1; i=$((i+1)); done; "
    "test -f /var/lib/postgresql/wal_export/%f.ack"
)
_DAEMON_POLICY = RUNTIME_POLICY.wal_ack_daemon
DAEMON_STATE_WRITE_ATTEMPTS = _DAEMON_POLICY.state_write_attempts
DAEMON_STATE_WRITE_RETRY_SECONDS = _DAEMON_POLICY.state_write_retry_seconds
WINDOWS_AUTOSTART_TASK = "TradersML-WALAckDaemon"
WINDOWS_STARTUP_LAUNCHER = "TradersML-WALAckDaemon.vbs"
SUPERVISOR_LOCK = "wal_recovery_supervisor.pid"
SUPERVISOR_STATE = "wal_recovery_supervisor_state.json"


@dataclass(frozen=True, slots=True)
class SafeWalSnapshot:
    captured_at: str
    archive_mode: str
    wal_level_class: str
    historical_failure_count: int
    archived_count: int
    active_unresolved_failure_count: int
    pending_archive_status_count: int
    completed_archive_status_count: int
    export_backlog_count: int
    export_ack_count: int
    archive_artifact_coverage_count: int
    required_wal_range_known: bool
    required_segment_count: int
    missing_required_segment_count: int
    source_recoverable_missing_count: int
    base_backup_chain_contiguous: bool
    physical_wal_gap: bool
    physical_wal_gap_unrecoverable: bool
    destination_accessible: bool
    last_success_age_seconds: int | None
    newest_recoverable_point_class: str
    newest_recoverable_ordinal: int | None
    continuous_pitr_window_seconds: int
    diagnosis_class: str
    failure_retried_and_recovered: bool
    health: str
    finding_codes: tuple[str, ...]


def _run(command: list[str], *, timeout: float = _DAEMON_POLICY.command_timeout_seconds) -> str:
    if any("://" in part for part in command):
        raise OperationFailure("PROTECTED_BINDING_OR_URI_IN_COMMAND")
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if result.returncode:
        raise OperationFailure("SAFE_WAL_INSPECTION_COMMAND_FAILED")
    return result.stdout.strip()


def _container_names(directory: str, pattern: str) -> tuple[str, ...]:
    if directory not in {
        "/var/lib/postgresql/data/pg_wal/archive_status",
        "/var/lib/postgresql/data/pg_wal",
        "/var/lib/postgresql/wal_export",
    }:
        raise OperationFailure("UNAPPROVED_WAL_INSPECTION_DIRECTORY")
    script = 'for f in "$1"/*; do [ -f "$f" ] && basename "$f"; done 2>/dev/null || true'
    output = _run([
        "docker", "exec", "--user", "postgres", CONTAINER,
        "sh", "-c", script, "wal-safe-list", directory,
    ])
    return tuple(line for line in output.splitlines() if fnmatch.fnmatchcase(line, pattern))


def _stat_record() -> tuple[int, int, str | None, str | None, int | None, datetime | None, str, str]:
    sql = (
        "SELECT archived_count, failed_count, COALESCE(last_archived_wal,''), "
        "COALESCE(last_failed_wal,''), "
        "COALESCE(EXTRACT(EPOCH FROM clock_timestamp()-last_archived_time)::bigint,-1), "
        "COALESCE(to_char(last_archived_time AT TIME ZONE 'UTC','YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"'),''), "
        "current_setting('archive_mode'), current_setting('wal_level') FROM pg_stat_archiver"
    )
    value = _run([
        "docker", "exec", "--user", "postgres", CONTAINER, "psql", "-U", DB_USER,
        "-d", DB_NAME, "-AtX", "-F", "|", "-c", sql,
    ])
    parts = value.split("|")
    if len(parts) != 8 or not parts[0].isdigit() or not parts[1].isdigit():
        raise OperationFailure("SAFE_ARCHIVER_RECORD_REJECTED")
    archived = parts[2] if SEGMENT_RE.fullmatch(parts[2]) else None
    failed = parts[3] if SEGMENT_RE.fullmatch(parts[3]) else None
    age = int(parts[4])
    archived_at = None if not parts[5] else datetime.fromisoformat(parts[5].replace("Z", "+00:00"))
    return int(parts[0]), int(parts[1]), archived, failed, None if age < 0 else age, archived_at, parts[6], parts[7]


def _base_contract(root: Path) -> tuple[datetime, int, str, tuple[str, ...]]:
    bases = [item for item in load_catalog(root) if item.artifact_type == "BASE"]
    if not bases:
        raise OperationFailure("BASE_BACKUP_MISSING")
    base = max(bases, key=lambda item: item.created_at)
    base_root = root / base.relative_path
    manifest = json.loads((base_root / "backup_manifest").read_text(encoding="utf-8"))
    ranges = manifest.get("WAL-Ranges")
    if not isinstance(ranges, list) or len(ranges) != 1:
        raise OperationFailure("BASE_WAL_RANGE_UNAVAILABLE")
    wal_range = ranges[0]
    timeline = wal_range.get("Timeline")
    start_lsn = wal_range.get("Start-LSN")
    if not isinstance(timeline, int) or not isinstance(start_lsn, str):
        raise OperationFailure("BASE_WAL_RANGE_REJECTED")
    base_wal = tuple(path.name for path in (base_root / "pg_wal").iterdir() if path.is_file() and SEGMENT_RE.fullmatch(path.name))
    return parse_utc(base.created_at), timeline, start_lsn, base_wal


def capture_snapshot(root: Path = SAFE_ROOT) -> SafeWalSnapshot:
    captured = datetime.now(timezone.utc)
    destination_accessible = root.is_dir() and (root / "wal_archive").is_dir()
    try:
        archive_names = tuple(path.name for path in (root / "wal_archive").iterdir() if path.is_file() and SEGMENT_RE.fullmatch(path.name))
    except OSError:
        archive_names = ()
        destination_accessible = False
    archived_count, failed_count, last_archived, last_failed, age, archived_at, archive_mode, wal_level = _stat_record()
    base_at, timeline, start_lsn, base_wal = _base_contract(root)
    ready = _container_names("/var/lib/postgresql/data/pg_wal/archive_status", "*.ready")
    done = _container_names("/var/lib/postgresql/data/pg_wal/archive_status", "*.done")
    export_all = _container_names("/var/lib/postgresql/wal_export", "*")
    export_wal = tuple(name for name in export_all if SEGMENT_RE.fullmatch(name))
    export_ack = tuple(name for name in export_all if name.endswith(".ack") and SEGMENT_RE.fullmatch(name[:-4]))
    source_wal = _container_names("/var/lib/postgresql/data/pg_wal", "*") + export_wal
    continuity = inspect_wal_continuity(
        timeline=timeline, base_start_lsn=start_lsn,
        latest_archived_segment=last_archived, base_wal_segments=base_wal,
        archive_wal_segments=archive_names, source_wal_segments=source_wal,
    )
    failed_present = bool(last_failed and last_failed in archive_names)
    failed_ack = bool(last_failed and f"{last_failed}.ack" in export_ack)
    diagnosis = diagnose_wal_archive_failure(
        historical_failure_count=failed_count, pending_archive_count=len(ready),
        export_backlog_count=len(export_wal), destination_accessible=destination_accessible,
        continuity=continuity, last_failed_segment=last_failed,
        last_archived_segment=last_archived, failed_artifact_present=failed_present,
        failed_ack_present=failed_ack,
    )
    newest_ordinal = None
    if last_archived:
        identity = wal_segment_identity(last_archived)
        newest_ordinal = None if identity is None else identity[1]
    wal_level_class = "REPLICA_OR_HIGHER" if wal_level in {"replica", "logical"} else "MINIMAL"
    progressing = bool(last_archived and age is not None and age <= 900 and not ready and not export_wal)
    health = build_wal_archive_health(
        archive_mode=archive_mode == "on", wal_level_class=wal_level_class,
        diagnosis=diagnosis, continuity=continuity, pending_archive_count=len(ready),
        archive_progressing=progressing, last_success_age_seconds=age,
        oldest_recoverable_point=base_at, newest_recoverable_point=archived_at,
    )
    return SafeWalSnapshot(
        captured.isoformat().replace("+00:00", "Z"), archive_mode.upper(), wal_level_class,
        failed_count, archived_count, diagnosis.active_unresolved_failure_count,
        len(ready), len(done), len(export_wal), len(export_ack),
        continuity.archive_artifact_coverage_count, continuity.required_range_known,
        continuity.required_segment_count, continuity.missing_required_segment_count,
        continuity.source_recoverable_missing_count, continuity.base_backup_chain_contiguous,
        continuity.physical_gap, continuity.unrecoverable_physical_gap,
        destination_accessible, age,
        "ARCHIVED_WAL_TIMESTAMP" if archived_at else "UNAVAILABLE", newest_ordinal,
        health.continuous_window_seconds, diagnosis.state.value,
        diagnosis.failure_retried_and_recovered, health.health, health.finding_codes,
    )


def bounded_retry(root: Path, *, timeout_seconds: int) -> tuple[SafeWalSnapshot, int]:
    if timeout_seconds < 1 or timeout_seconds > 600:
        raise OperationFailure("INVALID_BOUNDED_RETRY_TIMEOUT")
    deadline = time.monotonic() + timeout_seconds
    attempts = 0
    while True:
        snapshot = capture_snapshot(root)
        if (
            snapshot.active_unresolved_failure_count == 0
            and snapshot.pending_archive_status_count == 0
            and snapshot.export_backlog_count == 0
            and snapshot.base_backup_chain_contiguous
        ):
            return snapshot, attempts
        if time.monotonic() >= deadline:
            raise OperationFailure("BOUNDED_ARCHIVE_RETRY_TIMEOUT")
        if snapshot.export_backlog_count:
            sync_wal(root)
            attempts += 1
        time.sleep(2)


def install_host_ack_archive_command(root: Path) -> bool:
    """Restore and reload the validated host-ACK archive command."""
    if root.resolve() != SAFE_ROOT.resolve() or not (root / "wal_archive").is_dir():
        raise OperationFailure("ARCHIVE_DESTINATION_UNAVAILABLE")
    if "'" in HOST_ACK_ARCHIVE_COMMAND:
        raise OperationFailure("ARCHIVE_HELPER_SQL_LITERAL_REJECTED")
    sql = f"ALTER SYSTEM SET archive_command = '{HOST_ACK_ARCHIVE_COMMAND}'"
    _run([
        "docker", "exec", "--user", "postgres", CONTAINER, "psql", "-U", DB_USER,
        "-d", DB_NAME, "-AtX", "-c", sql,
    ])
    reloaded = _run([
        "docker", "exec", "--user", "postgres", CONTAINER, "psql", "-U", DB_USER,
        "-d", DB_NAME, "-AtX", "-c", "SELECT pg_reload_conf()",
    ])
    if reloaded != "t":
        raise OperationFailure("ARCHIVE_HELPER_RELOAD_FAILED")
    time.sleep(1)
    verified = _run([
        "docker", "exec", "--user", "postgres", CONTAINER, "psql", "-U", DB_USER,
        "-d", DB_NAME, "-AtX", "-c",
        "SELECT (current_setting('archive_command') = "
        + "'" + HOST_ACK_ARCHIVE_COMMAND + "')::int",
    ])
    if verified != "1":
        raise OperationFailure("ARCHIVE_HELPER_RELOAD_NOT_EFFECTIVE")
    return True


def _publish_daemon_state(
    path: Path,
    payload: dict[str, object],
    *,
    attempts: int = DAEMON_STATE_WRITE_ATTEMPTS,
    retry_seconds: float = DAEMON_STATE_WRITE_RETRY_SECONDS,
) -> bool:
    """Keep the archive owner alive across transient Windows replace denial."""
    if attempts < 1 or retry_seconds < 0:
        raise OperationFailure("INVALID_DAEMON_STATE_RETRY_POLICY")
    for attempt in range(attempts):
        try:
            atomic_json_write(path, payload)
            return True
        except OSError:
            if attempt + 1 < attempts:
                time.sleep(retry_seconds)
    return False


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _publish_recovery_domains(path: Path, updates: dict[str, object]) -> bool:
    current = _read_json_object(path)
    current.update(updates)
    return _publish_daemon_state(path, current)


def _utc(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def classify_worker_health(
    state: dict[str, object], *, now: datetime, process_alive: bool,
) -> tuple[bool, str]:
    """Return authoritative health for one generation-bound worker."""
    if not process_alive:
        return False, "RECOVERY_WORKER_NOT_RUNNING"
    heartbeat = _utc(state.get("heartbeat_at") or state.get("updated_at"))
    if heartbeat is None or (now - heartbeat).total_seconds() > _DAEMON_POLICY.heartbeat_freshness_seconds:
        return False, "RECOVERY_HEARTBEAT_STALE"
    deadline = _utc(state.get("next_recheck_at"))
    if deadline is None or (now - deadline).total_seconds() > _DAEMON_POLICY.recheck_grace_seconds:
        return False, "RECOVERY_RECHECK_STALLED"
    return True, "RECOVERY_WORKER_READY"


def _process_is_alive(pid: int) -> bool:
    if pid < 1:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _acquire_daemon_lock(lock: Path) -> int:
    """Acquire the owner lock, recovering only a proven-dead stale PID."""
    for attempt in range(2):
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                # Publish the owner before another simultaneous launcher can
                # misclassify a newly created, still-empty lock as stale.
                os.write(descriptor, str(os.getpid()).encode("ascii"))
                return descriptor
            except OSError:
                os.close(descriptor)
                try:
                    lock.unlink()
                except OSError:
                    pass
                raise
        except FileExistsError as error:
            if attempt or _process_is_alive(_read_lock_pid(lock)):
                raise OperationFailure("ACK_DAEMON_ALREADY_RUNNING_OR_STALE_LOCK") from error
            try:
                lock.unlink()
            except OSError as unlink_error:
                raise OperationFailure("ACK_DAEMON_STALE_LOCK_RECOVERY_FAILED") from unlink_error
    raise OperationFailure("ACK_DAEMON_LOCK_ACQUISITION_FAILED")


def _read_lock_pid(lock: Path) -> int:
    try:
        return int(lock.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return 0


def install_windows_daemon_autostart(root: Path, *, interval_seconds: int) -> bool:
    """Install the canonical daemon as a current-user logon task on Windows."""
    if os.name != "nt":
        raise OperationFailure("WINDOWS_AUTOSTART_UNAVAILABLE")
    if not (
        _DAEMON_POLICY.minimum_interval_seconds
        <= interval_seconds
        <= _DAEMON_POLICY.maximum_interval_seconds
    ):
        raise OperationFailure("INVALID_ACK_DAEMON_INTERVAL")
    if root.resolve() != SAFE_ROOT.resolve() or not (root / "wal_archive").is_dir():
        raise OperationFailure("UNAPPROVED_STORAGE_ROOT")
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        raise OperationFailure("PYTHONW_UNAVAILABLE")
    script = Path(__file__).resolve()
    task_action = (
        f'"{pythonw}" "{script}" supervisor --root "{root.resolve()}" '
        f"--interval-seconds {interval_seconds}"
    )
    created = subprocess.run(
        ["schtasks.exe", "/Create", "/TN", WINDOWS_AUTOSTART_TASK, "/SC", "ONLOGON",
         "/RL", "LIMITED", "/TR", task_action, "/F"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if not created.returncode:
        verified = subprocess.run(
            ["schtasks.exe", "/Query", "/TN", WINDOWS_AUTOSTART_TASK],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if verified.returncode:
            raise OperationFailure("ACK_DAEMON_AUTOSTART_VERIFY_FAILED")
        started = subprocess.run(
            ["schtasks.exe", "/Run", "/TN", WINDOWS_AUTOSTART_TASK],
            capture_output=True, text=True, timeout=_DAEMON_POLICY.command_timeout_seconds,
            check=False,
        )
        if started.returncode:
            raise OperationFailure("RECOVERY_SUPERVISOR_START_FAILED")
        return True

    # Non-elevated Windows sessions may not create even a LIMITED scheduled
    # task. The current-user Startup folder is the bounded, privilege-free
    # fallback and pythonw keeps the owner non-interactive and hidden.
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OperationFailure("ACK_DAEMON_AUTOSTART_INSTALL_FAILED")
    startup = (Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup")
    if not startup.is_dir():
        raise OperationFailure("WINDOWS_STARTUP_DIRECTORY_UNAVAILABLE")
    launcher = startup / WINDOWS_STARTUP_LAUNCHER
    vbs_action = task_action.replace('"', '""')
    content = f'CreateObject("WScript.Shell").Run "{vbs_action}", 0, False\n'
    pending = launcher.with_suffix(".vbs.pending")
    try:
        pending.write_text(content, encoding="utf-8")
        os.replace(pending, launcher)
        if launcher.read_text(encoding="utf-8") != content:
            raise OperationFailure("ACK_DAEMON_AUTOSTART_VERIFY_FAILED")
    except OSError as error:
        raise OperationFailure("ACK_DAEMON_AUTOSTART_INSTALL_FAILED") from error
    subprocess.Popen(
        [str(pythonw), str(script), "supervisor", "--root", str(root.resolve()),
         "--interval-seconds", str(interval_seconds)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return True


def _host_ack_daemon_cycle(root: Path, *, process_id: int) -> dict[str, object]:
    """Service one ACK cycle and publish only the post-sync durable state."""

    snapshot = capture_snapshot(root)
    published = 0
    deadline = time.monotonic() + _DAEMON_POLICY.cycle_work_seconds
    while time.monotonic() < deadline:
        if snapshot.export_backlog_count:
            result = sync_wal(root)
            published += int(result["published_segment_count"])
        snapshot = capture_snapshot(root)
        if (
            snapshot.pending_archive_status_count == 0
            and snapshot.export_backlog_count == 0
        ):
            break
        time.sleep(_DAEMON_POLICY.settle_poll_seconds)
    return {
        "schema": "TRADERS_ML_WAL_ACK_DAEMON_STATE_V1",
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "process_id": process_id,
        "status": "RUNNING",
        "pending_archive_status_count": snapshot.pending_archive_status_count,
        "export_backlog_count": snapshot.export_backlog_count,
        "published_segment_count_last_cycle": published,
        "error_class": "NONE",
    }


def run_host_ack_daemon(
    root: Path, *, interval_seconds: int, instance_id: str | None = None,
    generation: int = 1,
) -> None:
    """Continuously service the existing fail-closed host ACK protocol."""
    if not (
        _DAEMON_POLICY.minimum_interval_seconds
        <= interval_seconds
        <= _DAEMON_POLICY.maximum_interval_seconds
    ):
        raise OperationFailure("INVALID_ACK_DAEMON_INTERVAL")
    if root.resolve() != SAFE_ROOT.resolve():
        raise OperationFailure("UNAPPROVED_STORAGE_ROOT")
    lock = root / "catalog" / "wal_ack_daemon.pid"
    state = root / "catalog" / "wal_ack_daemon_state.json"
    descriptor = _acquire_daemon_lock(lock)
    recovery_path = root / "catalog" / "recovery_readiness.json"
    instance_id = instance_id or str(uuid.uuid4())
    domains = {"wal": RecoveryState(), "pitr": RecoveryState()}
    try:
        previous = json.loads(recovery_path.read_text(encoding="utf-8"))
        domains = {key: RecoveryState(**previous[key]) for key in domains}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        os.close(descriptor)
        bound_at = datetime.now(timezone.utc)
        domains = {key: value.bind(instance_id, generation, bound_at, interval_seconds) for key, value in domains.items()}
        while True:
            now = datetime.now(timezone.utc)
            started = now.isoformat()
            try:
                for key, value in domains.items():
                    if value.state == "DEGRADED":
                        domains[key] = value.advance("RECOVERING", "PITR_VERIFICATION_PENDING", now, interval_seconds)
                _publish_recovery_domains(recovery_path, {key: value.project() for key, value in domains.items()})
                payload = _host_ack_daemon_cycle(root, process_id=os.getpid())
                observed_at = datetime.now(timezone.utc)
                payload.update(
                    schema="TRADERS_ML_WAL_ACK_DAEMON_STATE_V2",
                    instance_id=instance_id, generation=generation,
                    started_at=domains["wal"].started_at,
                    heartbeat_at=observed_at.isoformat(),
                    next_recheck_at=(observed_at + timedelta(seconds=interval_seconds)).isoformat(),
                    snapshot_generated_at=observed_at.isoformat(),
                )
                _publish_daemon_state(state, payload)
                # Reuse the exact API lineage verifier; never manufacture a healthy chain.
                from app.server_api.paper_runtime_observation import _pitr_lineage
                finished_at = datetime.now(timezone.utc)
                observed = _pitr_lineage(root, finished_at)
                domains["wal"] = domains["wal"].advance(observed.wal_state, observed.wal_reason_code, finished_at, interval_seconds)
                domains["pitr"] = domains["pitr"].advance(observed.pitr_state, observed.pitr_reason_code, finished_at, interval_seconds)
            except Exception as error:
                # The supervisor must never be lost to a transient subprocess,
                # Docker, filesystem or publication exception.
                failed_at = datetime.now(timezone.utc)
                payload = {
                    "schema": "TRADERS_ML_WAL_ACK_DAEMON_STATE_V2",
                    "updated_at": failed_at.isoformat().replace("+00:00", "Z"),
                    "process_id": os.getpid(),
                    "status": "DEGRADED",
                    "pending_archive_status_count": -1,
                    "export_backlog_count": -1,
                    "published_segment_count_last_cycle": 0,
                    "error_class": type(error).__name__,
                }
                domains["wal"] = domains["wal"].advance("DEGRADED", "WAL_ARCHIVER_FAILURE", failed_at, interval_seconds)
                domains["pitr"] = domains["pitr"].advance("DEGRADED", "PITR_VERIFICATION_PENDING", failed_at, interval_seconds)
            finished = datetime.now(timezone.utc)
            next_recheck = (finished + timedelta(seconds=interval_seconds)).isoformat()
            payload.update(
                schema="TRADERS_ML_WAL_ACK_DAEMON_STATE_V2", instance_id=instance_id,
                generation=generation, started_at=domains["wal"].started_at,
                heartbeat_at=finished.isoformat(), last_recheck_started_at=started,
                last_recheck_finished_at=finished.isoformat(), next_recheck_at=next_recheck,
                snapshot_generated_at=finished.isoformat(),
            )
            _publish_daemon_state(state, payload)
            _publish_recovery_domains(recovery_path, {key: value.project() for key, value in domains.items()})
            time.sleep(interval_seconds)
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


def run_recovery_supervisor(root: Path, *, interval_seconds: int) -> None:
    """Watch the watchdog: keep exactly one generation-bound ACK worker alive."""
    if root.resolve() != SAFE_ROOT.resolve():
        raise OperationFailure("UNAPPROVED_STORAGE_ROOT")
    catalog = root / "catalog"
    descriptor = _acquire_daemon_lock(catalog / SUPERVISOR_LOCK)
    os.close(descriptor)
    generation = int(_read_json_object(catalog / SUPERVISOR_STATE).get("generation", 0))
    restarts: list[float] = []
    child: subprocess.Popen[str] | None = None
    instance_id = ""
    try:
        while True:
            now = datetime.now(timezone.utc)
            worker_state = _read_json_object(catalog / "wal_ack_daemon_state.json")
            alive = child is not None and child.poll() is None
            healthy, reason = classify_worker_health(worker_state, now=now, process_alive=alive)
            identity_matches = (
                alive and worker_state.get("instance_id") == instance_id
                and worker_state.get("generation") == generation
            )
            if not healthy or not identity_matches:
                if alive:
                    child.terminate()
                    try:
                        child.wait(timeout=_DAEMON_POLICY.command_timeout_seconds)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait()
                stale_pid = catalog / "wal_ack_daemon.pid"
                if stale_pid.exists() and not _process_is_alive(_read_lock_pid(stale_pid)):
                    stale_pid.unlink()
                moment = time.monotonic()
                restarts = [value for value in restarts if moment - value < _DAEMON_POLICY.restart_cooldown_seconds]
                if len(restarts) >= _DAEMON_POLICY.restart_burst:
                    time.sleep(_DAEMON_POLICY.restart_cooldown_seconds)
                    restarts.clear()
                time.sleep(_DAEMON_POLICY.restart_backoff_seconds)
                generation += 1
                instance_id = str(uuid.uuid4())
                child = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), "daemon", "--root", str(root),
                     "--interval-seconds", str(interval_seconds), "--instance-id", instance_id,
                     "--generation", str(generation)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    text=True,
                )
                restarts.append(moment)
                reason = "RECOVERY_WORKER_RESTARTED"
                started = datetime.now(timezone.utc)
                _publish_daemon_state(catalog / "wal_ack_daemon_state.json", {
                    "schema": "TRADERS_ML_WAL_ACK_DAEMON_STATE_V2",
                    "process_id": child.pid, "status": "RECOVERING",
                    "error_class": "NONE", "instance_id": instance_id,
                    "generation": generation, "started_at": started.isoformat(),
                    "heartbeat_at": started.isoformat(),
                    "next_recheck_at": (started + timedelta(seconds=interval_seconds)).isoformat(),
                    "last_recheck_started_at": None, "last_recheck_finished_at": None,
                    "snapshot_generated_at": started.isoformat(),
                    "pending_archive_status_count": -1, "export_backlog_count": -1,
                    "published_segment_count_last_cycle": 0,
                })
            stamp = datetime.now(timezone.utc).isoformat()
            supervisor = {
                "state": "READY", "reason_code": "RECOVERY_SUPERVISOR_READY",
                "heartbeat_at": stamp, "last_success_at": stamp,
                "last_failure_at": None, "instance_id": str(os.getpid()),
                "generation": generation, "started_at": stamp,
            }
            worker = dict(worker_state)
            worker.update(state="READY" if healthy and identity_matches else "RECOVERING", reason_code=reason,
                          instance_id=instance_id, generation=generation)
            scheduler = dict(worker)
            scheduler.update(state="READY" if healthy else "RECOVERING",
                             reason_code="RECOVERY_RECHECK_READY" if healthy else reason)
            publication = dict(worker)
            publication.update(state="READY", reason_code="RECOVERY_STATE_PUBLICATION_READY",
                               snapshot_generated_at=stamp, heartbeat_at=stamp)
            _publish_recovery_domains(catalog / "recovery_readiness.json", {
                "recovery_supervisor": supervisor, "recovery_worker": worker,
                "recovery_recheck_scheduler": scheduler,
                "recovery_state_publication": publication,
            })
            _publish_daemon_state(catalog / SUPERVISOR_STATE, {
                "schema": "TRADERS_ML_RECOVERY_SUPERVISOR_STATE_V1", "process_id": os.getpid(),
                "heartbeat_at": stamp, "generation": generation, "worker_instance_id": instance_id,
                "worker_process_id": child.pid if child and child.poll() is None else None,
            })
            time.sleep(_DAEMON_POLICY.supervisor_poll_seconds)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
        try:
            (catalog / SUPERVISOR_LOCK).unlink()
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=(
        "diagnose", "retry", "install-host-ack-command", "install-daemon-autostart", "daemon", "supervisor",
    ))
    parser.add_argument("--root", type=Path, default=SAFE_ROOT)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument(
        "--interval-seconds", type=int, default=_DAEMON_POLICY.interval_seconds
    )
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--generation", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        if args.operation == "diagnose":
            result = asdict(capture_snapshot(args.root))
        elif args.operation == "retry":
            snapshot, attempts = bounded_retry(args.root, timeout_seconds=args.timeout_seconds)
            result = {**asdict(snapshot), "archive_retry_attempts": attempts}
        elif args.operation == "install-host-ack-command":
            result = {"archive_command_restored": install_host_ack_archive_command(args.root), "reload": "PASS"}
        elif args.operation == "install-daemon-autostart":
            result = {"autostart_installed": install_windows_daemon_autostart(
                args.root, interval_seconds=args.interval_seconds),
                "autostart_scope": "CURRENT_USER_LOGON"}
        elif args.operation == "daemon":
            run_host_ack_daemon(args.root, interval_seconds=args.interval_seconds,
                                instance_id=args.instance_id, generation=args.generation)
            result = {"status": "STOPPED"}
        else:
            run_recovery_supervisor(args.root, interval_seconds=args.interval_seconds)
            result = {"status": "STOPPED"}
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, OperationFailure, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "FAILED", "error_class": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
