"""Sanitized authoritative health for the automatic PAPER execution loops."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Protocol


SCHEMA: Final = "TRADERS_PAPER_RUNTIME_HEALTH/1"
FILE_NAME: Final = "runtime-health.json"
MAX_BYTES: Final = 8 * 1024
PUBLISH_INTERVAL_SECONDS: Final = 5.0
MAX_HEARTBEAT_AGE_SECONDS: Final = 20.0


class RuntimeLoop(Protocol):
    poll_seconds: float

    @property
    def active(self) -> bool: ...

    @property
    def ticks(self) -> int: ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PaperRuntimeHealthPublisher:
    """Publish one bounded no-secret snapshot from the actual worker objects."""

    def __init__(
        self,
        root: Path,
        *,
        approval_loop: RuntimeLoop,
        lifecycle_loop: RuntimeLoop,
        mutation_enabled: bool,
        clock: Callable[[], datetime] = _utc_now,
        interval_seconds: float = PUBLISH_INTERVAL_SECONDS,
    ) -> None:
        if not 1.0 <= interval_seconds <= 30.0:
            raise ValueError("PAPER_RUNTIME_HEALTH_INTERVAL_INVALID")
        self._root = root
        self._approval = approval_loop
        self._lifecycle = lifecycle_loop
        self._mutation_enabled = bool(mutation_enabled)
        self._clock = clock
        self._interval = float(interval_seconds)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def active(self) -> bool:
        return bool(self._thread is not None and self._thread.is_alive() and not self._stop.is_set())

    def _payload(self) -> dict[str, object]:
        approval_active = self._approval.active
        lifecycle_active = self._lifecycle.active
        now = self._clock().astimezone(timezone.utc)
        return {
            "approval_poll_seconds": self._approval.poll_seconds,
            "approval_ticks": self._approval.ticks,
            "approval_watcher_active": approval_active,
            "daemon_enabled": True,
            "execution_poll_seconds": self._lifecycle.poll_seconds,
            "execution_ticks": self._lifecycle.ticks,
            "execution_worker_active": lifecycle_active,
            "generated_at": now.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "live_allowed": False,
            "mode": "PAPER",
            "mutation_enabled": self._mutation_enabled,
            "runtime_enabled": True,
            "scheduler_enabled": approval_active and lifecycle_active,
            "schema": SCHEMA,
            "selector_active": approval_active,
        }

    def publish(self) -> None:
        payload = self._payload()
        rendered = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        if len(rendered) > MAX_BYTES:
            raise RuntimeError("PAPER_RUNTIME_HEALTH_TOO_LARGE")
        with self._lock:
            self._root.mkdir(parents=True, exist_ok=True)
            temporary = self._root / f".{FILE_NAME}.{os.getpid()}.tmp"
            target = self._root / FILE_NAME
            with temporary.open("wb") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.publish()
            except Exception:
                # A missing heartbeat must fail closed in the reader; the
                # runtime loops themselves remain independently guarded.
                pass
            self._stop.wait(self._interval)

    def start(self) -> None:
        if self.active:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="paper-runtime-health-publisher", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=self._interval + 1.0)
        self._thread = None


def read_paper_runtime_health(
    root: Path,
    *,
    now: datetime | None = None,
    max_age_seconds: float = MAX_HEARTBEAT_AGE_SECONDS,
) -> dict[str, object] | None:
    """Return a validated fresh PAPER-only snapshot, otherwise fail closed."""

    try:
        path = root / FILE_NAME
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        generated = datetime.fromisoformat(str(payload["generated_at"]).replace("Z", "+00:00"))
        current = (now or _utc_now()).astimezone(timezone.utc)
        age = (current - generated.astimezone(timezone.utc)).total_seconds()
        exact = {
            "approval_poll_seconds", "approval_ticks", "approval_watcher_active",
            "daemon_enabled", "execution_poll_seconds", "execution_ticks",
            "execution_worker_active", "generated_at", "live_allowed", "mode",
            "mutation_enabled", "runtime_enabled", "scheduler_enabled", "schema",
            "selector_active",
        }
        if (
            not isinstance(payload, dict)
            or set(payload) != exact
            or payload.get("schema") != SCHEMA
            or payload.get("mode") != "PAPER"
            or payload.get("live_allowed") is not False
            or not 0 <= age <= max_age_seconds
            or not isinstance(payload.get("approval_ticks"), int)
            or not isinstance(payload.get("execution_ticks"), int)
        ):
            return None
        return payload
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


__all__ = [
    "FILE_NAME", "MAX_HEARTBEAT_AGE_SECONDS", "PaperRuntimeHealthPublisher",
    "read_paper_runtime_health",
]
