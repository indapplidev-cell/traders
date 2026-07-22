"""Crash-safe filesystem observer primitives for production soak monitoring.

The observer is deliberately independent from application service lifecycle.  It
may inspect services, but never mutates them or the production database.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


HEARTBEAT_SCHEMA = "OBSERVER_HEARTBEAT/1.0"
PROCESS_SCHEMA = "OBSERVER_PROCESS/1.0"
LOCK_SCHEMA = "OBSERVER_LOCK/1.0"
RECORD_SCHEMA = "OBSERVER_RECORD/1.0"
FINAL_STATE_SCHEMA = "OBSERVER_FINAL_STATE/1.0"
RUN_SCHEMA = "OBSERVER_RUN/1.0"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class HeartbeatState(StrEnum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class CollectorStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    TIMEOUT = "TIMEOUT"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


class GapCause(StrEnum):
    PROCESS_NOT_RUNNING = "PROCESS_NOT_RUNNING"
    COLLECTOR_OVERRUN = "COLLECTOR_OVERRUN"
    SYSTEM_SUSPEND = "SYSTEM_SUSPEND"
    HOST_CLOCK_ADJUSTMENT = "HOST_CLOCK_ADJUSTMENT"
    LOCK_CONTENTION = "LOCK_CONTENTION"
    WRITE_FAILURE = "WRITE_FAILURE"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"
    CONTROLLED_RESTART = "CONTROLLED_RESTART"
    UNKNOWN = "UNKNOWN"


class ObserverError(RuntimeError):
    """Base typed observer error."""


class ObserverAlreadyRunning(ObserverError):
    reason_code = "ACTIVE_OBSERVER_LOCK"


class LockMetadataMismatch(ObserverError):
    reason_code = "LOCK_METADATA_MISMATCH"


class ArtifactWriteError(ObserverError):
    reason_code = "ARTIFACT_WRITE_FAILURE"


@dataclass(frozen=True)
class CollectorResult:
    collector_name: str
    status: CollectorStatus
    started_at_utc: str
    completed_at_utc: str
    duration_ms: int
    data: Any = None
    error_code: str | None = None
    error_message_redacted: str | None = None
    retryable: bool = False


class Collector(Protocol):
    name: str

    def collect(self) -> CollectorResult: ...


@dataclass(frozen=True)
class ObserverConfig:
    soak_directory: Path
    sampling_interval_seconds: float = 60.0
    heartbeat_interval_seconds: float = 10.0
    allowed_jitter_seconds: float = 15.0
    gap_threshold_seconds: float | None = None
    degraded_after_failures: int = 2
    command_timeout_seconds: float = 15.0
    db_timeout_seconds: float = 10.0
    fallback_directory: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "traders_ml_observer_failures")
    stop_request_name: str = "observer.stop.request"
    version: str = "ONLINE-ORCHESTRATOR-OBSERVER-RELIABILITY-FIX-01"

    def __post_init__(self) -> None:
        if self.sampling_interval_seconds <= 0:
            raise ValueError("sampling_interval_seconds must be positive")
        maximum_heartbeat = min(10.0, self.sampling_interval_seconds / 3.0)
        if self.heartbeat_interval_seconds <= 0 or self.heartbeat_interval_seconds > maximum_heartbeat:
            raise ValueError(f"heartbeat_interval_seconds must be <= {maximum_heartbeat}")
        if self.allowed_jitter_seconds < 0:
            raise ValueError("allowed_jitter_seconds must be non-negative")
        threshold = self.gap_threshold_seconds
        if threshold is not None and threshold < self.sampling_interval_seconds:
            raise ValueError("gap_threshold_seconds must be at least the sampling interval")

    @property
    def effective_gap_threshold_seconds(self) -> float:
        return self.gap_threshold_seconds or self.sampling_interval_seconds + self.allowed_jitter_seconds


class Clock(Protocol):
    def monotonic(self) -> float: ...
    def wall_utc(self) -> datetime: ...
    def wait(self, event: threading.Event, seconds: float) -> bool: ...


class SystemClock:
    def monotonic(self) -> float:
        return time.monotonic()

    def wall_utc(self) -> datetime:
        return utc_now()

    def wait(self, event: threading.Event, seconds: float) -> bool:
        return event.wait(max(0.0, seconds))


_SENSITIVE_KEY = re.compile(r"(?:password|passwd|secret|token|authorization|api[_-]?key|database_url|dsn)", re.I)
_URL_CREDENTIAL = re.compile(r"(?P<scheme>[a-z][a-z0-9+.-]*://)(?P<user>[^:/\s]+):(?P<password>[^@/\s]+)@", re.I)
_BEARER = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+")
_ASSIGNMENT = re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*([^\s,;]+)")


def redact(value: Any, *, key: str | None = None) -> Any:
    """Recursively redact credential-bearing keys and common string forms."""
    if key is not None and _SENSITIVE_KEY.search(key):
        return "***REDACTED***"
    if isinstance(value, Mapping):
        return {str(k): redact(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        text = _URL_CREDENTIAL.sub(lambda m: f"{m.group('scheme')}{m.group('user')}:***REDACTED***@", value)
        text = _BEARER.sub(lambda m: f"{m.group(1)} ***REDACTED***", text)
        return _ASSIGNMENT.sub(lambda m: f"{m.group(1)}=***REDACTED***", text)
    return value


def canonical_json(value: Any, *, indent: int | None = None) -> str:
    return json.dumps(redact(value), ensure_ascii=False, sort_keys=True, separators=None if indent else (",", ":"), indent=indent, default=str)


def command_hash(argv: Sequence[str]) -> str:
    safe_shape = [Path(argv[0]).name.lower() if argv else ""] + [str(item).split("=", 1)[0] for item in argv[1:]]
    return hashlib.sha256("\0".join(safe_shape).encode("utf-8")).hexdigest()


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_json(path: Path, value: Any, *, replace_attempts: int = 30) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json(value, indent=2))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(replace_attempts):
            try:
                os.replace(temporary, path)
                _sync_directory(path.parent)
                return
            except PermissionError:
                if attempt + 1 == replace_attempts:
                    raise
                time.sleep(min(0.01 * (attempt + 1), 0.1))
    except Exception as exc:
        raise ArtifactWriteError(f"atomic write failed for {path.name}: {type(exc).__name__}: {exc}") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def atomic_write_text(path: Path, value: str, *, replace_attempts: int = 30) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(replace_attempts):
            try:
                os.replace(temporary, path)
                _sync_directory(path.parent)
                return
            except PermissionError:
                if attempt + 1 == replace_attempts:
                    raise
                time.sleep(min(0.01 * (attempt + 1), 0.1))
    except Exception as exc:
        raise ArtifactWriteError(f"atomic write failed for {path.name}: {type(exc).__name__}: {exc}") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


class ArtifactStore:
    """Single-process, durable JSON/JSONL persistence."""

    COMPATIBLE_JSONL = (
        "health_snapshots.jsonl",
        "resource_audit.jsonl",
        "service_stats.jsonl",
        "observations.jsonl",
        "incident_log.jsonl",
    )

    def __init__(self, root: Path, observer_instance_id: str, clock: Clock) -> None:
        self.root = root.resolve()
        self.observer_instance_id = observer_instance_id
        self.clock = clock
        self._write_lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True)

    def write_json(self, name: str, value: Any) -> None:
        with self._write_lock:
            atomic_write_json(self.root / name, value)

    def append(self, name: str, value: Mapping[str, Any], *, sample_sequence: int, scheduled_for_utc: str | None, record_type: str) -> None:
        record = {
            "schema_version": RECORD_SCHEMA,
            "observer_instance_id": self.observer_instance_id,
            "sample_sequence": sample_sequence,
            "recorded_at_utc": iso_utc(self.clock.wall_utc()),
            "scheduled_for_utc": scheduled_for_utc,
            "record_type": record_type,
            **dict(value),
        }
        line = canonical_json(record) + "\n"
        path = self.root / name
        try:
            with self._write_lock:
                with path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(line)
                    handle.flush()
                    os.fsync(handle.fileno())
        except Exception as exc:
            raise ArtifactWriteError(f"append failed for {name}: {type(exc).__name__}: {exc}") from exc


@dataclass(frozen=True)
class ProcessIdentity:
    exists: bool
    started_at_utc: str | None = None
    command_line_hash: str | None = None


class ProcessInspector:
    """Minimal process identity checks without a third-party dependency."""

    def inspect(self, pid: int) -> ProcessIdentity:
        if pid <= 0:
            return ProcessIdentity(False)
        if os.name != "nt":
            try:
                os.kill(pid, 0)
            except (OSError, ProcessLookupError):
                return ProcessIdentity(False)
            return ProcessIdentity(True)
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return ProcessIdentity(False)
        try:
            creation = ctypes.c_ulonglong()
            exit_time = ctypes.c_ulonglong()
            kernel = ctypes.c_ulonglong()
            user = ctypes.c_ulonglong()
            started = None
            if kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)):
                epoch_seconds = creation.value / 10_000_000 - 11_644_473_600
                started = iso_utc(datetime.fromtimestamp(epoch_seconds, timezone.utc))
            return ProcessIdentity(True, started_at_utc=started)
        finally:
            kernel32.CloseHandle(handle)


def _try_lock(handle: Any) -> bool:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    import fcntl
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class InstanceLock:
    def __init__(self, path: Path, metadata: Mapping[str, Any], inspector: ProcessInspector | None = None) -> None:
        self.path = path
        self.metadata = dict(metadata)
        self.inspector = inspector or ProcessInspector()
        self.handle: Any | None = None
        self.recovered_metadata: dict[str, Any] | None = None

    @staticmethod
    def _read(handle: Any) -> dict[str, Any] | None:
        handle.seek(0)
        raw = handle.read().decode("utf-8", errors="strict").strip()
        if not raw or raw == "0":
            return None
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise LockMetadataMismatch("lock metadata is not an object")
        return value

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"0")
            handle.flush()
            os.fsync(handle.fileno())
        if not _try_lock(handle):
            handle.close()
            raise ObserverAlreadyRunning("another observer holds the soak-directory lock")
        try:
            previous = self._read(handle)
            if previous:
                if previous.get("schema_version") != LOCK_SCHEMA or Path(str(previous.get("soak_directory", ""))).resolve() != Path(str(self.metadata["soak_directory"])).resolve():
                    raise LockMetadataMismatch("existing lock metadata schema or soak directory does not match")
                if previous.get("active", True):
                    identity = self.inspector.inspect(int(previous.get("os_pid", -1)))
                    start_matches = not identity.started_at_utc or identity.started_at_utc == previous.get("process_started_at_utc")
                    command_matches = not identity.command_line_hash or identity.command_line_hash == previous.get("command_line_hash")
                    if identity.exists and start_matches and command_matches:
                        raise ObserverAlreadyRunning("lock metadata identifies a live observer process")
                    self.recovered_metadata = previous
            self.handle = handle
            self._persist({**self.metadata, "active": True})
        except Exception:
            _unlock(handle)
            handle.close()
            raise

    def _persist(self, value: Mapping[str, Any]) -> None:
        if self.handle is None:
            raise RuntimeError("lock not acquired")
        payload = canonical_json(value, indent=2).encode("utf-8") + b"\n"
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(payload)
        self.handle.flush()
        os.fsync(self.handle.fileno())

    def release(self, *, state: str = "STOPPED") -> None:
        if self.handle is None:
            return
        try:
            self._persist({**self.metadata, "active": False, "released_at_utc": iso_utc(utc_now()), "state": state})
        finally:
            try:
                _unlock(self.handle)
            finally:
                self.handle.close()
                self.handle = None


@dataclass
class ScheduleAdvance:
    next_due_monotonic: float
    next_due_utc: datetime
    missed_interval_count: int


class MonotonicSchedule:
    """Fixed-boundary schedule that skips missed slots without burst catch-up."""

    def __init__(self, interval_seconds: float, start_monotonic: float, start_wall_utc: datetime) -> None:
        self.interval_seconds = interval_seconds
        self.due_monotonic = start_monotonic
        self.due_utc = start_wall_utc.astimezone(timezone.utc)

    def advance_after(self, completed_monotonic: float) -> ScheduleAdvance:
        next_due = self.due_monotonic + self.interval_seconds
        missed = 0
        if completed_monotonic >= next_due:
            missed = int((completed_monotonic - next_due) // self.interval_seconds) + 1
            next_due += missed * self.interval_seconds
        delta = next_due - self.due_monotonic
        self.due_monotonic = next_due
        self.due_utc += timedelta(seconds=delta)
        return ScheduleAdvance(next_due, self.due_utc, missed)


def classify_gap(*, monotonic_elapsed: float, wall_elapsed: float, controlled_restart: bool = False, collector_overrun: bool = False) -> GapCause:
    if controlled_restart:
        return GapCause.CONTROLLED_RESTART
    if collector_overrun:
        return GapCause.COLLECTOR_OVERRUN
    if monotonic_elapsed > 0 and wall_elapsed - monotonic_elapsed > max(2.0, monotonic_elapsed * 0.25):
        return GapCause.HOST_CLOCK_ADJUSTMENT
    if monotonic_elapsed > 0 and abs(wall_elapsed - monotonic_elapsed) <= max(2.0, monotonic_elapsed * 0.25):
        return GapCause.SYSTEM_SUSPEND
    return GapCause.UNKNOWN


class CommandCollector:
    def __init__(self, name: str, command: Sequence[str], *, cwd: Path | None = None, timeout_seconds: float = 15.0) -> None:
        self.name = name
        self.command = tuple(command)
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds

    def collect(self) -> CollectorResult:
        started_wall = utc_now()
        started = time.monotonic()
        try:
            result = subprocess.run(self.command, cwd=self.cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False, timeout=self.timeout_seconds)
            status = CollectorStatus.SUCCESS if result.returncode == 0 else CollectorStatus.FAILED
            error = None if status == CollectorStatus.SUCCESS else redact(result.stderr[-2000:])
            data = {"returncode": result.returncode, "stdout": redact(result.stdout[-100_000:])}
            code = None if status == CollectorStatus.SUCCESS else "COMMAND_NONZERO"
            retryable = status != CollectorStatus.SUCCESS
        except subprocess.TimeoutExpired as exc:
            status, data, code, error, retryable = CollectorStatus.TIMEOUT, None, "COMMAND_TIMEOUT", redact(str(exc)), True
        except (FileNotFoundError, OSError) as exc:
            status, data, code, error, retryable = CollectorStatus.UNAVAILABLE, None, "COMMAND_UNAVAILABLE", redact(str(exc)), True
        completed_wall = utc_now()
        return CollectorResult(self.name, status, iso_utc(started_wall) or "", iso_utc(completed_wall) or "", int((time.monotonic() - started) * 1000), data, code, error, retryable)


class JsonFileCollector:
    def __init__(self, name: str, paths: Mapping[str, Path], *, maximum_bytes: int = 2_000_000) -> None:
        self.name, self.paths, self.maximum_bytes = name, dict(paths), maximum_bytes

    def collect(self) -> CollectorResult:
        started_wall, started = utc_now(), time.monotonic()
        data, errors = {}, []
        for key, path in self.paths.items():
            try:
                if path.stat().st_size > self.maximum_bytes:
                    raise ValueError("file exceeds observer read limit")
                data[key] = redact(json.loads(path.read_text(encoding="utf-8")))
            except Exception as exc:
                errors.append({"path": str(path), "error": redact(f"{type(exc).__name__}: {exc}")})
        if not errors:
            status, code = CollectorStatus.SUCCESS, None
        elif data:
            status, code = CollectorStatus.PARTIAL, "FILE_READ_PARTIAL"
        else:
            status, code = CollectorStatus.UNAVAILABLE, "FILE_READ_UNAVAILABLE"
        completed = utc_now()
        return CollectorResult(self.name, status, iso_utc(started_wall) or "", iso_utc(completed) or "", int((time.monotonic() - started) * 1000), {"values": data, "errors": errors}, code, canonical_json(errors) if errors else None, True if errors else False)


class ReadOnlyDatabaseCollector:
    """Bounded PostgreSQL health query with transaction-level read-only guards."""

    name = "database_health"

    def __init__(self, dsn: str, *, timeout_seconds: float = 10.0) -> None:
        self.dsn = dsn
        self.timeout_seconds = timeout_seconds

    def collect(self) -> CollectorResult:
        started_wall, started = utc_now(), time.monotonic()
        try:
            import psycopg
            timeout_ms = max(1, int(self.timeout_seconds * 1000))
            with psycopg.connect(self.dsn, connect_timeout=max(1, int(self.timeout_seconds)), options="-c default_transaction_read_only=on") as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION READ ONLY")
                    cursor.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
                    cursor.execute("SELECT current_database(), pg_is_in_recovery(), clock_timestamp()")
                    row = cursor.fetchone()
                connection.rollback()
            status, data, code, error, retryable = CollectorStatus.SUCCESS, {"database": row[0], "in_recovery": row[1], "database_clock_utc": iso_utc(row[2])}, None, None, False
        except Exception as exc:
            message = redact(f"{type(exc).__name__}: {exc}")
            lowered = str(exc).lower()
            if "timeout" in lowered or "canceling statement" in lowered:
                status, code = CollectorStatus.TIMEOUT, "DB_TIMEOUT"
            else:
                status, code = CollectorStatus.UNAVAILABLE, "DB_UNAVAILABLE"
            data, error, retryable = None, str(message), True
        completed = utc_now()
        return CollectorResult(self.name, status, iso_utc(started_wall) or "", iso_utc(completed) or "", int((time.monotonic() - started) * 1000), data, code, error, retryable)


@dataclass
class ObserverCounters:
    samples_attempted: int = 0
    samples_successful: int = 0
    samples_partial: int = 0
    samples_failed: int = 0
    sampling_gaps: int = 0
    max_sampling_gap_seconds: float = 0.0
    collector_failures: int = 0
    heartbeat_updates: int = 0


class ReliableObserver:
    def __init__(self, config: ObserverConfig, collectors: Sequence[Collector], *, clock: Clock | None = None, argv: Sequence[str] | None = None, process_inspector: ProcessInspector | None = None) -> None:
        self.config = config
        self.collectors = tuple(collectors)
        self.clock = clock or SystemClock()
        self.argv = tuple(argv or ["engine_observer_reliability"])
        self.instance_id = str(uuid.uuid4())
        self.run_id = ""
        self.started_wall = self.clock.wall_utc()
        self.started_monotonic = self.clock.monotonic()
        self.os_pid, self.parent_pid = os.getpid(), os.getppid()
        inspected_self = (process_inspector or ProcessInspector()).inspect(self.os_pid)
        self.process_started_at_utc = inspected_self.started_at_utc or iso_utc(self.started_wall)
        self.hostname = socket.gethostname()
        self.store = ArtifactStore(config.soak_directory, self.instance_id, self.clock)
        self._process_inspector = process_inspector
        self._heartbeat_lock = threading.RLock()
        self._shutdown_event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self._shutdown_requested = False
        self._state = HeartbeatState.STARTING
        self._last_loop_started: datetime | None = None
        self._last_loop_completed: datetime | None = None
        self._last_successful_sample: datetime | None = None
        self._next_sample_due: datetime | None = self.started_wall
        self._last_sample_scheduled: datetime | None = None
        self._sequence = 0
        self._consecutive_failures = 0
        self._last_error_code: str | None = None
        self._last_error_at: datetime | None = None
        self.counters = ObserverCounters()
        self._lock: InstanceLock | None = None

    def _load_or_create_run_id(self) -> str:
        path = self.config.soak_directory / "observer_run.json"
        if path.exists():
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("schema_version") != RUN_SCHEMA or Path(value.get("soak_directory", "")).resolve() != self.config.soak_directory.resolve():
                raise LockMetadataMismatch("observer_run.json does not match this soak directory")
            return str(value["observer_run_id"])
        run_id = str(uuid.uuid4())
        atomic_write_json(path, {"schema_version": RUN_SCHEMA, "observer_run_id": run_id, "soak_directory": str(self.config.soak_directory.resolve()), "created_at_utc": iso_utc(self.started_wall)})
        return run_id

    def _lock_metadata(self) -> dict[str, Any]:
        return {
            "schema_version": LOCK_SCHEMA,
            "observer_instance_id": self.instance_id,
            "os_pid": self.os_pid,
            "parent_pid": self.parent_pid,
            "process_started_at_utc": self.process_started_at_utc,
            "hostname": self.hostname,
            "soak_directory": str(self.config.soak_directory.resolve()),
            "command_line_hash": command_hash(self.argv),
        }

    def _process_record(self, state: HeartbeatState) -> dict[str, Any]:
        return {
            "schema_version": PROCESS_SCHEMA,
            "observer_instance_id": self.instance_id,
            "observer_run_id": self.run_id,
            "os_pid": self.os_pid,
            "parent_pid": self.parent_pid,
            "process_started_at_utc": self.process_started_at_utc,
            "hostname": self.hostname,
            "soak_directory": str(self.config.soak_directory.resolve()),
            "state": state.value,
            "updated_at_utc": iso_utc(self.clock.wall_utc()),
            "version": self.config.version,
        }

    def _heartbeat(self, state: HeartbeatState | None = None) -> dict[str, Any]:
        with self._heartbeat_lock:
            if state is not None:
                self._state = state
            return {
                "schema_version": HEARTBEAT_SCHEMA,
                "observer_instance_id": self.instance_id,
                "observer_run_id": self.run_id,
                "os_pid": self.os_pid,
                "parent_pid": self.parent_pid,
                "hostname": self.hostname,
                "soak_directory": str(self.config.soak_directory.resolve()),
                "state": self._state.value,
                "started_at_utc": iso_utc(self.started_wall),
                "last_loop_started_at_utc": iso_utc(self._last_loop_started),
                "last_loop_completed_at_utc": iso_utc(self._last_loop_completed),
                "last_successful_sample_at_utc": iso_utc(self._last_successful_sample),
                "last_heartbeat_at_utc": iso_utc(self.clock.wall_utc()),
                "next_sample_due_at_utc": iso_utc(self._next_sample_due),
                "sample_sequence": self._sequence,
                "consecutive_loop_failures": self._consecutive_failures,
                "last_error_code": self._last_error_code,
                "last_error_at_utc": iso_utc(self._last_error_at),
                "shutdown_requested": self._shutdown_requested,
            }

    def _write_heartbeat(self, state: HeartbeatState | None = None) -> None:
        heartbeat = self._heartbeat(state)
        self.store.write_json("observer_heartbeat.json", heartbeat)
        self.store.append("heartbeat_history.jsonl", heartbeat, sample_sequence=self._sequence, scheduled_for_utc=iso_utc(self._next_sample_due), record_type="ObserverHeartbeat")
        self.counters.heartbeat_updates += 1

    def _heartbeat_loop(self) -> None:
        next_due = self.clock.monotonic()
        while not self._shutdown_event.is_set():
            try:
                if (self.config.soak_directory / self.config.stop_request_name).exists():
                    with self._heartbeat_lock:
                        self._shutdown_requested = True
                    self._shutdown_event.set()
                self._write_heartbeat()
            except ArtifactWriteError:
                self._last_error_code = "HEARTBEAT_WRITE_FAILURE"
                self._last_error_at = self.clock.wall_utc()
                self._shutdown_event.set()
                return
            next_due += self.config.heartbeat_interval_seconds
            self.clock.wait(self._shutdown_event, max(0.0, next_due - self.clock.monotonic()))

    def start(self) -> None:
        self.config.soak_directory.mkdir(parents=True, exist_ok=True)
        previous_final = None
        previous_final_path = self.config.soak_directory / "observer_final_state.json"
        if previous_final_path.exists():
            previous_final = json.loads(previous_final_path.read_text(encoding="utf-8"))
        self.run_id = self._load_or_create_run_id()
        self._lock = InstanceLock(self.config.soak_directory / "observer.lock", self._lock_metadata(), self._process_inspector)
        self._lock.acquire()
        stop_request = self.config.soak_directory / self.config.stop_request_name
        if stop_request.exists():
            stop_request.unlink()
            self.store.append("incident_log.jsonl", {"event": "STALE_STOP_REQUEST_CLEARED", "cause_code": GapCause.CONTROLLED_RESTART.value}, sample_sequence=0, scheduled_for_utc=None, record_type="ObserverLifecycle")
        self.store.write_json("observer_process.json", self._process_record(HeartbeatState.STARTING))
        atomic_write_text(self.config.soak_directory / "observer.pid", f"{self.os_pid}\n")
        self._write_heartbeat(HeartbeatState.STARTING)
        if self._lock.recovered_metadata:
            self.store.append("incident_log.jsonl", {
                "event": "ABRUPTLY_TERMINATED",
                "cause_code": GapCause.PROCESS_NOT_RUNNING.value,
                "previous_instance": redact(self._lock.recovered_metadata),
            }, sample_sequence=0, scheduled_for_utc=None, record_type="ObserverCrashRecovery")
        if previous_final:
            classification = GapCause.CONTROLLED_RESTART if int(previous_final.get("exit_code", 1)) == 0 else GapCause.PROCESS_NOT_RUNNING
            report = (
                "# Observer restart report\n\n"
                f"classification = {classification.value}\n"
                f"previous_instance_id = {previous_final.get('observer_instance_id')}\n"
                f"previous_stopped_at_utc = {previous_final.get('stopped_at_utc')}\n"
                f"new_instance_id = {self.instance_id}\n"
                f"new_started_at_utc = {iso_utc(self.started_wall)}\n"
                "sample_identity_policy = observer_instance_id + sample_sequence\n"
            )
            atomic_write_text(self.config.soak_directory / "observer_restart_report.md", report)
            self.store.append("incident_log.jsonl", {
                "event": "OBSERVER_RESTART",
                "cause_code": classification.value,
                "previous_instance_id": previous_final.get("observer_instance_id"),
                "new_instance_id": self.instance_id,
            }, sample_sequence=0, scheduled_for_utc=None, record_type="ObserverRestart")
            previous_due_text = previous_final.get("last_sample_scheduled_for_utc")
            if previous_due_text:
                previous_due = datetime.fromisoformat(str(previous_due_text).replace("Z", "+00:00"))
                actual_gap = max(0.0, (self.started_wall - previous_due).total_seconds())
                missed = max(0, int(actual_gap // self.config.sampling_interval_seconds) - 1)
                threshold_exceeded = actual_gap > self.config.effective_gap_threshold_seconds
                if threshold_exceeded:
                    self.counters.sampling_gaps += 1
                    self.counters.max_sampling_gap_seconds = max(self.counters.max_sampling_gap_seconds, actual_gap)
                self.store.append("incident_log.jsonl", {
                    "event": "ObserverSamplingGap",
                    "previous_instance_id": previous_final.get("observer_instance_id"),
                    "current_instance_id": self.instance_id,
                    "previous_sequence": previous_final.get("samples_attempted"),
                    "current_sequence": 1,
                    "previous_scheduled_for_utc": iso_utc(previous_due),
                    "current_scheduled_for_utc": iso_utc(self.started_wall),
                    "expected_interval_seconds": self.config.sampling_interval_seconds,
                    "actual_gap_seconds": actual_gap,
                    "missed_interval_count": missed,
                    "gap_threshold_seconds": self.config.effective_gap_threshold_seconds,
                    "threshold_exceeded": threshold_exceeded,
                    "cause_code": classification.value,
                    "evidence": {"policy": "SKIP_MISSED_INTERVALS_AND_RECORD_GAP", "restart_report": "observer_restart_report.md"},
                }, sample_sequence=0, scheduled_for_utc=iso_utc(self.started_wall), record_type="ObserverSamplingGap")
        self._state = HeartbeatState.RUNNING
        self.store.write_json("observer_process.json", self._process_record(HeartbeatState.RUNNING))
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, name="observer-heartbeat", daemon=True)
        self._heartbeat_thread.start()
        self.store.append("observations.jsonl", {"event": "OBSERVER_STARTED", "observed_at": iso_utc(self.clock.wall_utc()), "os_pid": self.os_pid}, sample_sequence=0, scheduled_for_utc=None, record_type="ObserverLifecycle")

    def _sample(self, scheduled_for: datetime) -> str:
        self._sequence += 1
        sequence = self._sequence
        self._last_sample_scheduled = scheduled_for
        self.counters.samples_attempted += 1
        self._last_loop_started = self.clock.wall_utc()
        results: list[CollectorResult] = []
        for collector in self.collectors:
            try:
                results.append(collector.collect())
            except Exception as exc:
                results.append(CollectorResult(collector.name, CollectorStatus.FAILED, iso_utc(self.clock.wall_utc()) or "", iso_utc(self.clock.wall_utc()) or "", 0, None, "COLLECTOR_INTERNAL_ERROR", str(redact(exc)), False))
        failed = [item for item in results if item.status != CollectorStatus.SUCCESS]
        if not failed:
            status = "SUCCESS"
            self.counters.samples_successful += 1
            self._last_successful_sample = self.clock.wall_utc()
            self._consecutive_failures = 0
            self._last_error_code = None
        elif len(failed) < len(results):
            status = "PARTIAL"
            self.counters.samples_partial += 1
            self.counters.collector_failures += len(failed)
            self._last_successful_sample = self.clock.wall_utc()
            self._consecutive_failures += 1
            self._last_error_code = failed[0].error_code
            self._last_error_at = self.clock.wall_utc()
        else:
            status = "FAILED"
            self.counters.samples_failed += 1
            self.counters.collector_failures += len(failed)
            self._consecutive_failures += 1
            self._last_error_code = failed[0].error_code if failed else "NO_COLLECTORS"
            self._last_error_at = self.clock.wall_utc()
        self._last_loop_completed = self.clock.wall_utc()
        duration_ms = int((self._last_loop_completed - self._last_loop_started).total_seconds() * 1000)
        common = {
            "status": status,
            "started_at_utc": iso_utc(self._last_loop_started),
            "completed_at_utc": iso_utc(self._last_loop_completed),
            "duration_ms": max(0, duration_ms),
            "collectors": [asdict(item) for item in results],
            "observed_at": iso_utc(self._last_loop_completed),
            "captured_at": iso_utc(self._last_loop_completed),
        }
        scheduled = iso_utc(scheduled_for)
        self.store.append("observations.jsonl", common, sample_sequence=sequence, scheduled_for_utc=scheduled, record_type="ObserverSample")
        self.store.append("health_snapshots.jsonl", common, sample_sequence=sequence, scheduled_for_utc=scheduled, record_type="HealthSnapshot")
        resource_results = [asdict(item) for item in results if item.collector_name.startswith("docker") or item.collector_name.startswith("resource")]
        resource_record = {**common, "collectors": resource_results}
        self.store.append("resource_audit.jsonl", resource_record, sample_sequence=sequence, scheduled_for_utc=scheduled, record_type="ResourceAudit")
        self.store.append("service_stats.jsonl", resource_record, sample_sequence=sequence, scheduled_for_utc=scheduled, record_type="ServiceStats")
        with self._heartbeat_lock:
            self._state = HeartbeatState.DEGRADED if self._consecutive_failures >= self.config.degraded_after_failures else HeartbeatState.RUNNING
        self._write_heartbeat()
        return status

    def _record_gap(self, previous_sequence: int, previous_due: datetime, current_due: datetime, missed: int, cause: GapCause) -> None:
        gap = (current_due - previous_due).total_seconds()
        threshold_exceeded = gap > self.config.effective_gap_threshold_seconds
        if threshold_exceeded:
            self.counters.sampling_gaps += 1
            self.counters.max_sampling_gap_seconds = max(self.counters.max_sampling_gap_seconds, gap)
        self.store.append("incident_log.jsonl", {
            "event": "ObserverSamplingGap",
            "previous_sequence": previous_sequence,
            "current_sequence": previous_sequence + 1,
            "previous_scheduled_for_utc": iso_utc(previous_due),
            "current_scheduled_for_utc": iso_utc(current_due),
            "expected_interval_seconds": self.config.sampling_interval_seconds,
            "actual_gap_seconds": gap,
            "missed_interval_count": missed,
            "cause_code": cause.value,
            "gap_threshold_seconds": self.config.effective_gap_threshold_seconds,
            "threshold_exceeded": threshold_exceeded,
            "evidence": {"policy": "SKIP_MISSED_INTERVALS_AND_RECORD_GAP"},
        }, sample_sequence=previous_sequence, scheduled_for_utc=iso_utc(previous_due), record_type="ObserverSamplingGap")

    def run(self, *, maximum_samples: int | None = None, maximum_runtime_seconds: float | None = None) -> int:
        exit_code, exit_reason = 0, "CONTROLLED_STOP"
        try:
            self.start()
            schedule = MonotonicSchedule(self.config.sampling_interval_seconds, self.clock.monotonic(), self.clock.wall_utc())
            while not self._shutdown_event.is_set():
                due_mono, due_wall = schedule.due_monotonic, schedule.due_utc
                if self.clock.wait(self._shutdown_event, max(0.0, due_mono - self.clock.monotonic())):
                    break
                self._next_sample_due = due_wall
                self._sample(due_wall)
                completed = self.clock.monotonic()
                previous_due = due_wall
                advance = schedule.advance_after(completed)
                self._next_sample_due = advance.next_due_utc
                if advance.missed_interval_count:
                    self._record_gap(self._sequence, previous_due, advance.next_due_utc, advance.missed_interval_count, GapCause.COLLECTOR_OVERRUN)
                if maximum_samples is not None and self.counters.samples_attempted >= maximum_samples:
                    self.request_stop("MAXIMUM_SAMPLES_REACHED")
                    exit_reason = "MAXIMUM_SAMPLES_REACHED"
                if maximum_runtime_seconds is not None and completed - self.started_monotonic >= maximum_runtime_seconds:
                    self.request_stop("MAXIMUM_RUNTIME_REACHED")
                    exit_reason = "MAXIMUM_RUNTIME_REACHED"
            if self._last_error_code == "HEARTBEAT_WRITE_FAILURE":
                raise ArtifactWriteError("heartbeat writer stopped after an artifact failure")
        except KeyboardInterrupt:
            self.request_stop("KEYBOARD_INTERRUPT")
            exit_reason = "KEYBOARD_INTERRUPT"
        except (ObserverAlreadyRunning, LockMetadataMismatch):
            raise
        except Exception as exc:
            exit_code, exit_reason = 2, f"FAILED:{type(exc).__name__}"
            self._last_error_code = getattr(exc, "reason_code", "UNHANDLED_EXCEPTION")
            self._last_error_at = self.clock.wall_utc()
            self._state = HeartbeatState.FAILED
            self._write_fallback_failure(exc)
        finally:
            if self._lock and self._lock.handle is not None:
                self._finalize(exit_reason, exit_code)
        return exit_code

    def request_stop(self, reason: str = "CONTROLLED_STOP") -> None:
        with self._heartbeat_lock:
            self._shutdown_requested = True
            self._state = HeartbeatState.STOPPING
        self._write_heartbeat(HeartbeatState.STOPPING)
        self._shutdown_event.set()

    def _finalize(self, exit_reason: str, exit_code: int) -> None:
        final_state = HeartbeatState.FAILED if exit_code else HeartbeatState.STOPPED
        try:
            if self._state != HeartbeatState.FAILED:
                self._state = HeartbeatState.STOPPING
                self._write_heartbeat(HeartbeatState.STOPPING)
            self._shutdown_event.set()
            if self._heartbeat_thread and self._heartbeat_thread is not threading.current_thread():
                self._heartbeat_thread.join(timeout=max(1.0, self.config.heartbeat_interval_seconds * 2))
            stopped = self.clock.wall_utc()
            summary = {
                "schema_version": FINAL_STATE_SCHEMA,
                "observer_instance_id": self.instance_id,
                "observer_run_id": self.run_id,
                "started_at_utc": iso_utc(self.started_wall),
                "stopped_at_utc": iso_utc(stopped),
                "runtime_seconds": max(0.0, self.clock.monotonic() - self.started_monotonic),
                "last_sample_scheduled_for_utc": iso_utc(self._last_sample_scheduled),
                **asdict(self.counters),
                "exit_reason": exit_reason,
                "exit_code": exit_code,
            }
            self.store.write_json("observer_final_state.json", summary)
            self.store.append("observer_final_states.jsonl", summary, sample_sequence=self._sequence, scheduled_for_utc=iso_utc(self._next_sample_due), record_type="ObserverFinalState")
            self.store.write_json("observer_shutdown.json", {**summary, "shutdown_requested": self._shutdown_requested})
            self._state = final_state
            self.store.write_json("observer_process.json", self._process_record(final_state))
            self._write_heartbeat(final_state)
            self.store.append("observations.jsonl", {"event": "OBSERVER_STOPPED", "exit_reason": exit_reason, "exit_code": exit_code, "observed_at": iso_utc(stopped)}, sample_sequence=self._sequence, scheduled_for_utc=iso_utc(self._next_sample_due), record_type="ObserverLifecycle")
            (self.config.soak_directory / self.config.stop_request_name).unlink(missing_ok=True)
        except Exception as exc:
            final_state = HeartbeatState.FAILED
            self._write_fallback_failure(exc)
        finally:
            self._lock.release(state=final_state.value)

    def _write_fallback_failure(self, exc: Exception) -> None:
        self.config.fallback_directory.mkdir(parents=True, exist_ok=True)
        target = self.config.fallback_directory / f"observer_failure_{self.instance_id}.json"
        try:
            atomic_write_json(target, {
                "schema_version": "OBSERVER_FALLBACK_FAILURE/1.0",
                "observer_instance_id": self.instance_id,
                "soak_directory": str(self.config.soak_directory.resolve()),
                "failed_at_utc": iso_utc(self.clock.wall_utc()),
                "error_code": self._last_error_code,
                "error_message_redacted": redact(f"{type(exc).__name__}: {exc}"),
            })
        except Exception:
            pass


def audit_jsonl(directory: Path) -> dict[str, Any]:
    corrupt, records, identities = 0, 0, set()
    duplicates = 0
    files: dict[str, Any] = {}
    for name in ArtifactStore.COMPATIBLE_JSONL:
        path = directory / name
        file_corrupt = file_records = 0
        if path.exists():
            raw = path.read_bytes()
            newline_terminated = not raw or raw.endswith(b"\n")
            for line in raw.splitlines():
                try:
                    value = json.loads(line.decode("utf-8"))
                    file_records += 1
                    if value.get("record_type") in {"ObserverSample", "HealthSnapshot", "ResourceAudit", "ServiceStats"}:
                        identity = (value.get("observer_instance_id"), value.get("sample_sequence"), value.get("record_type"))
                        if identity in identities:
                            duplicates += 1
                        identities.add(identity)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    file_corrupt += 1
            if not newline_terminated:
                file_corrupt += 1
        else:
            newline_terminated = True
        corrupt += file_corrupt
        records += file_records
        files[name] = {"records": file_records, "corrupt_lines": file_corrupt, "newline_terminated": newline_terminated}
    return {"files": files, "records": records, "corrupt_lines": corrupt, "duplicate_identities": duplicates}
