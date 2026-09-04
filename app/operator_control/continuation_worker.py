"""Durable continuation for an already-started first PAPER canary."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from hashlib import sha256
from threading import Event, Lock, Thread
from typing import Iterator

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.engine_paper.first_canary_correlation import (
    PaperFirstCanaryState,
    SqlAlchemyPaperFirstCanaryStore,
)
from app.engine_paper.continuous_authority import (
    ACTIVE_STATE,
    ContinuousAuthorityError,
    PaperContinuousAuthorityStore,
)
from app.engine_safety.paper_production_control import (
    PaperProductionSafetyControl,
    PersistentState,
)

from .production_executor import ProductionPaperFirstCanaryExecutor


LOG = logging.getLogger(__name__)
POLL_SECONDS_ENV = "TRADERS_FIRST_CANARY_CONTINUATION_POLL_SECONDS"
DEFAULT_POLL_SECONDS = 5.0
MIN_POLL_SECONDS = 5.0
MAX_POLL_SECONDS = 3600.0


def continuation_poll_seconds(value: str | None = None) -> float:
    raw = os.environ.get(POLL_SECONDS_ENV) if value is None else value
    if raw is None:
        return DEFAULT_POLL_SECONDS
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        raise RuntimeError("FIRST_CANARY_CONTINUATION_INTERVAL_INVALID") from None
    if not MIN_POLL_SECONDS <= parsed <= MAX_POLL_SECONDS:
        raise RuntimeError("FIRST_CANARY_CONTINUATION_INTERVAL_INVALID")
    return parsed


class PostgresCanaryContinuationLock:
    """Session advisory lock: one continuation execution per canary cluster-wide."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @staticmethod
    def _key(canary_id: str) -> int:
        unsigned = int.from_bytes(
            sha256(f"first-canary-continuation|{canary_id}".encode("ascii")).digest()[:8],
            "big",
        )
        return unsigned if unsigned < 2**63 else unsigned - 2**64

    @contextmanager
    def acquire(self, canary_id: str) -> Iterator[bool]:
        key = self._key(canary_id)
        with self._engine.connect() as connection:
            acquired = bool(
                connection.execute(
                    text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
                ).scalar_one()
            )
            try:
                yield acquired
            finally:
                if acquired:
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:key)"), {"key": key}
                    )


class PaperFirstCanaryEligibleApprovalContinuationWorker:
    """Bounded polling of the durable waiting row; no operator mutation is minted."""

    def __init__(
        self,
        *,
        control: PaperProductionSafetyControl,
        canary_store: SqlAlchemyPaperFirstCanaryStore,
        executor: ProductionPaperFirstCanaryExecutor,
        lock: PostgresCanaryContinuationLock,
        poll_seconds: float,
        continuous_store: PaperContinuousAuthorityStore | None = None,
    ) -> None:
        if not MIN_POLL_SECONDS <= poll_seconds <= MAX_POLL_SECONDS:
            raise ValueError("poll_seconds outside bounded range")
        self._control = control
        self._canary_store = canary_store
        self._executor = executor
        self._lock = lock
        self.poll_seconds = poll_seconds
        self._continuous_store = continuous_store
        self._stop = Event()
        self._thread: Thread | None = None
        self._lifecycle_lock = Lock()
        self._ticks = 0

    @property
    def active(self) -> bool:
        thread = self._thread
        return bool(thread is not None and thread.is_alive() and not self._stop.is_set())

    @property
    def ticks(self) -> int:
        return self._ticks

    def run_once(self) -> str:
        expire = getattr(self._executor, "expire_due_outcomes", None)
        if expire is not None:
            expire()
        control = self._control.read_authoritative()
        if control.state is PersistentState.CONTINUOUS_ARMED:
            if self._continuous_store is None:
                return "SAFE_FAILURE:CONTINUOUS_CONTROL_NOT_CONFIGURED"
            try:
                budget = self._continuous_store.reconcile(generation=control.generation)
            except ContinuousAuthorityError as error:
                return f"SAFE_FAILURE:{error}"
            if budget.control_state != ACTIVE_STATE or not budget.enabled:
                return f"PAUSED_BY_RISK:{budget.pause_reason or 'RISK_BUDGET_EXHAUSTED'}"
            canary = self._canary_store.current()
            if canary is not None:
                if canary.authority_mode != "CONTINUOUS":
                    return "SAFE_FAILURE:LEGACY_CANARY_ACTIVE_DURING_CONTINUOUS_MODE"
                if canary.command_id is not None:
                    return "ACTIVE_CONTINUOUS_CYCLE"
            with self._lock.acquire(f"continuous-generation-{control.generation}") as acquired:
                if not acquired:
                    return "CLAIMED_BY_ANOTHER_WORKER"
                findings = self._executor.execute_continuous_once()
                if findings == ("NO_ELIGIBLE_APPROVAL",):
                    return "WAITING_FOR_ELIGIBLE_APPROVAL"
                if findings:
                    return f"SAFE_FAILURE:{findings[0]}"
                return "COMMAND_CREATED_OR_REPLAYED"
        canary = self._canary_store.current()
        if canary is None or canary.state is not PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL:
            return "NO_WAITING_CANARY"
        if (
            canary.started_at is None
            or canary.start_request_id is None
            or canary.command_count != 0
            or canary.position_count != 0
        ):
            return "WAITING_CANARY_NOT_ELIGIBLE"
        with self._lock.acquire(canary.canary_id) as acquired:
            if not acquired:
                return "CLAIMED_BY_ANOTHER_WORKER"
            # Re-read after ownership. This makes stale discovery harmless.
            current = self._canary_store.get(canary.canary_id)
            if (
                current is None
                or current.state is not PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL
                or current.started_at is None
                or current.start_request_id is None
                or current.command_count != 0
                or current.position_count != 0
            ):
                return "WAITING_CANARY_CHANGED"
            if (
                control.state is not PersistentState.ARMED
                or control.transition_id != current.arming_transition_id
                or control.generation != current.arming_generation
            ):
                return "CONTROL_PREEMPTED"
            findings = self._executor.continue_waiting_canary(current.canary_id)
            if findings == ("NO_ELIGIBLE_APPROVAL",):
                return "WAITING_FOR_ELIGIBLE_APPROVAL"
            if findings:
                return f"SAFE_FAILURE:{findings[0]}"
            return "COMMAND_CREATED_OR_REPLAYED"

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception:
                LOG.exception("first canary continuation tick failed safely")
            finally:
                self._ticks += 1
            self._stop.wait(self.poll_seconds)

    def start(self) -> None:
        with self._lifecycle_lock:
            if self.active:
                return
            self._stop.clear()
            self._thread = Thread(
                target=self._run,
                name="paper-continuous-approval-worker",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        with self._lifecycle_lock:
            self._stop.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=min(self.poll_seconds + 1.0, 10.0))


__all__ = (
    "PaperContinuousApprovalWorker",
    "PaperFirstCanaryEligibleApprovalContinuationWorker",
    "PostgresCanaryContinuationLock",
    "continuation_poll_seconds",
)


# Canonical production name. The legacy export remains for historical tests and
# for decoding old first-canary records only.
PaperContinuousApprovalWorker = PaperFirstCanaryEligibleApprovalContinuationWorker
