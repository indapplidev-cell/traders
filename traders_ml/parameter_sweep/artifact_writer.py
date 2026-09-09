"""Windows-safe, process-local serialization for parameter-sweep artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import io
import json
import os
from pathlib import Path
import threading
import time
import uuid
from typing import Any, Callable, Iterable


TRANSIENT_WINDOWS_CODES = frozenset({5, 32, 33})
from app.config.yaml_authority import RESEARCH_PARAMETERS

DEFAULT_RETRY_DELAYS = RESEARCH_PARAMETERS.artifact_writer.retry_delays_seconds
_locks_guard = threading.Lock()
_locks: dict[str, threading.RLock] = {}


def _path_lock(path: Path) -> threading.RLock:
    key = os.path.normcase(str(path.resolve()))
    with _locks_guard:
        return _locks.setdefault(key, threading.RLock())


def windows_error_code(error: BaseException) -> int | None:
    value = getattr(error, "winerror", None)
    if value is not None:
        return int(value)
    if isinstance(error, PermissionError):
        return int(getattr(error, "errno", 5) or 5)
    return None


def is_transient_windows_filesystem_error(error: BaseException) -> bool:
    return isinstance(error, PermissionError) or (
        isinstance(error, OSError) and windows_error_code(error) in TRANSIENT_WINDOWS_CODES
    )


@dataclass(slots=True)
class ArtifactWriteError(RuntimeError):
    path: Path
    operation: str
    attempts: int
    winerror: int | None
    original: BaseException

    def __str__(self) -> str:
        return (
            f"ARTIFACT_WRITE_FAILED operation={self.operation} path={self.path} "
            f"winerror={self.winerror} attempts={self.attempts}: {self.original}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": "ARTIFACT_WRITE_FAILED",
            "operation": self.operation,
            "path": str(self.path),
            "winerror": self.winerror,
            "attempts": self.attempts,
            "exception_type": type(self.original).__name__,
            "message": str(self.original),
        }


class ArtifactWriter:
    """Own atomic replacement, retry policy, and per-target serialization."""

    def __init__(
        self,
        *,
        retry_delays: Iterable[float] = DEFAULT_RETRY_DELAYS,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.retry_delays = tuple(retry_delays)
        self.sleeper = sleeper

    @staticmethod
    def _temporary(path: Path) -> Path:
        return path.parent / (
            f".{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
        )

    def _retry(self, path: Path, operation: str, action: Callable[[], None]) -> None:
        attempts = 0
        last: BaseException | None = None
        for delay in self.retry_delays:
            if delay:
                self.sleeper(delay)
            attempts += 1
            try:
                action()
                return
            except BaseException as error:
                if not is_transient_windows_filesystem_error(error):
                    raise
                last = error
        assert last is not None
        raise ArtifactWriteError(path, operation, attempts, windows_error_code(last), last)

    def atomic_bytes(self, path: Path, content: bytes, *, operation: str = "replace") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _path_lock(path):
            temporary = self._temporary(path)
            try:
                def write_temp() -> None:
                    with temporary.open("wb") as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())

                self._retry(path, f"{operation}:write_temp", write_temp)
                def replace_temp() -> None:
                    try:
                        os.replace(temporary, path)
                    except BaseException as error:
                        # Some Windows/filesystem layers report failure after the
                        # rename became visible. Content reconciliation prevents a
                        # second replace from turning success into data loss.
                        if is_transient_windows_filesystem_error(error):
                            try:
                                if path.read_bytes() == content:
                                    return
                            except OSError:
                                pass
                        raise

                self._retry(path, operation, replace_temp)
            finally:
                if temporary.exists():
                    try:
                        self._retry(path, f"{operation}:unlink_temp", temporary.unlink)
                    except ArtifactWriteError:
                        pass

    def atomic_text(self, path: Path, content: str, *, operation: str = "replace") -> None:
        self.atomic_bytes(path, content.encode("utf-8"), operation=operation)

    def atomic_json(self, path: Path, payload: object, *, operation: str = "replace_json") -> None:
        self.atomic_text(
            path, json.dumps(payload, indent=2, sort_keys=True, default=str), operation=operation,
        )

    def append_text(self, path: Path, content: str, *, operation: str = "append") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _path_lock(path):
            def append() -> None:
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
            self._retry(path, operation, append)


DEFAULT_ARTIFACT_WRITER = ArtifactWriter()


class DurableResultWriter:
    """Exactly-once JSONL authority with a derived, atomically replaced CSV view."""

    def __init__(self, directory: Path, csv_fields: list[str], *, writer: ArtifactWriter | None = None) -> None:
        self.directory = directory
        self.jsonl_path = directory / "RESULTS.jsonl"
        self.csv_path = directory / "RESULTS.csv"
        self.csv_fields = csv_fields
        self.writer = writer or DEFAULT_ARTIFACT_WRITER
        self._lock = threading.RLock()

    @staticmethod
    def identity(item: dict[str, Any]) -> tuple[Any, Any, Any]:
        return item.get("run_id"), item.get("result_index"), item.get("config_hash")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.jsonl_path.exists():
            return []
        return [json.loads(line) for line in self.jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def append(self, item: dict[str, Any]) -> bool:
        """Return True for a new durable result and False for an identical replay."""
        with self._lock, _path_lock(self.jsonl_path), _path_lock(self.csv_path):
            rows = self.read_all()
            identity = self.identity(item)
            matches = [row for row in rows if self.identity(row) == identity]
            if matches:
                if len(matches) != 1 or matches[0] != item:
                    raise ValueError(f"RESULT_IDENTITY_CONFLICT:{identity}")
                self._write_csv(rows)
                return False
            if any(row.get("result_index") == item.get("result_index") for row in rows):
                raise ValueError(f"RESULT_INDEX_CONFLICT:{item.get('result_index')}")
            rendered = "".join(json.dumps(row, sort_keys=True) + "\n" for row in (*rows, item))
            try:
                self.writer.atomic_text(self.jsonl_path, rendered, operation="result_jsonl_replace")
            except ArtifactWriteError:
                # os.replace can report an error after completing; reconcile before retrying upstream.
                durable = self.read_all()
                if not any(self.identity(row) == identity and row == item for row in durable):
                    raise
                rows = durable
            else:
                rows.append(item)
            self._write_csv(rows)
            return True

    def _write_csv(self, rows: list[dict[str, Any]]) -> None:
        buffer = io.StringIO(newline="")
        csv_writer = csv.DictWriter(buffer, fieldnames=self.csv_fields)
        csv_writer.writeheader()
        for item in rows:
            validation = item["validation"]
            csv_writer.writerow({
                "result_index": item["result_index"],
                "config_hash": item["config_hash"],
                "stage": item["stage"],
                "result_status": item["result_status"],
                "validation_expectancy": validation.get("net_expectancy_per_trade"),
                "validation_drawdown": validation.get("max_drawdown"),
                "validation_trades": validation.get("trade_count"),
                "parameters_json": json.dumps(item["parameters"], sort_keys=True),
            })
        self.writer.atomic_text(self.csv_path, buffer.getvalue(), operation="result_csv_replace")
