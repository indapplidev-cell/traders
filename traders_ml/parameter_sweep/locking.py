"""Single-run project-local lock with stale-owner recovery."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .state import process_alive


class SweepAlreadyRunning(RuntimeError):
    def __init__(self, run_id: str, pid: int) -> None:
        self.run_id = run_id
        self.pid = pid
        super().__init__(f"PARAMETER_SWEEP_ALREADY_RUNNING:{run_id}:{pid}")


class SingleRunLock:
    def __init__(self, path: Path, run_id: str) -> None:
        self.path = path
        self.run_id = run_id
        self.pid = os.getpid()
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": self.run_id,
            "pid": self.pid,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                owner = json.loads(self.path.read_text(encoding="utf-8"))
                owner_pid = int(owner.get("pid", -1))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                owner, owner_pid = {}, -1
            if process_alive(owner_pid):
                raise SweepAlreadyRunning(str(owner.get("run_id", "UNKNOWN")), owner_pid)
            self.path.unlink(missing_ok=True)
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        self.acquired = True

    def release(self) -> None:
        if not self.acquired:
            return
        try:
            owner = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            owner = {}
        if owner.get("pid") == self.pid and owner.get("run_id") == self.run_id:
            self.path.unlink(missing_ok=True)
        self.acquired = False

    def __enter__(self) -> "SingleRunLock":
        self.acquire()
        return self

    def __exit__(self, *_args: object) -> None:
        self.release()
