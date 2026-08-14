from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from threading import Event, Lock, Thread

import pytest

from app.engine_paper.first_canary_correlation import (
    PaperFirstCanarySession,
    PaperFirstCanaryState,
)
from app.engine_safety.paper_production_control import PersistentState
from app.engine_paper.production_approval import PaperProductionApprovalSourceAdapter
from app.operator_control.continuation_worker import (
    PaperFirstCanaryEligibleApprovalContinuationWorker,
    continuation_poll_seconds,
)
from app.operator_control.production_executor import ProductionPaperFirstCanaryExecutor
from app.operator_control.service import PaperOperatorControlService
from tests.paper_production_approval_source_adapter.test_adapter_contract import (
    AS_OF,
    FakeReader,
    FakeSession,
    eligible_row,
    row,
)


NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)
CANARY_ID = "8c52768d-2a3a-47cb-acdc-3d1cb1b6ce9d"
START_REQUEST_ID = "client-start-4df3c10a480248c9bff16cf398b06dfe"
TRANSITION_ID = "transition-original-arm"


def waiting_canary(**changes):
    value = PaperFirstCanarySession(
        CANARY_ID, "PRODUCTION", "PAPER",
        PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL,
        NOW, NOW, NOW, None, "original-arm-request", TRANSITION_ID, 4,
        START_REQUEST_ID, 4, 1, 1, ("BTCUSDT",), None, 0, None, 0, None,
        False, "NOT_STARTED", "NOT_STARTED", None, None, (), 4,
    )
    return replace(value, **changes)


class Store:
    def __init__(self, value):
        self.value = value
        self.created_canaries = 1

    def current(self):
        return self.value

    def get(self, canary_id):
        return self.value if self.value is not None and canary_id == self.value.canary_id else None


class Control:
    def __init__(self, state=PersistentState.ARMED):
        self.state = state

    def read_authoritative(self):
        return type("State", (), {
            "state": self.state, "transition_id": TRANSITION_ID, "generation": 4,
        })()


class AlwaysLock:
    @contextmanager
    def acquire(self, _canary_id):
        yield True


class ExclusiveLock:
    def __init__(self):
        self.lock = Lock()

    @contextmanager
    def acquire(self, _canary_id):
        acquired = self.lock.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                self.lock.release()


class Executor:
    def __init__(self, store, outcomes):
        self.store = store
        self.outcomes = iter(outcomes)
        self.calls = 0

    def continue_waiting_canary(self, canary_id):
        assert canary_id == CANARY_ID
        self.calls += 1
        outcome = next(self.outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        if outcome == ():
            self.store.value = replace(
                self.store.value,
                state=PaperFirstCanaryState.RUNNING,
                approval_id="risk-approval:authoritative",
                command_count=1,
                command_id="paper:command:authoritative",
            )
        return outcome


def worker(store, executor, *, control=None, lock=None):
    return PaperFirstCanaryEligibleApprovalContinuationWorker(
        control=control or Control(), canary_store=store, executor=executor,
        lock=lock or AlwaysLock(), poll_seconds=5.0,
    )


def test_waiting_no_approval_has_no_write_and_preserves_original_lineage():
    original = waiting_canary()
    store = Store(original)
    executor = Executor(store, [("NO_ELIGIBLE_APPROVAL",)])
    assert worker(store, executor).run_once() == "WAITING_FOR_ELIGIBLE_APPROVAL"
    assert store.value == original
    assert store.value.start_request_id == START_REQUEST_ID
    assert store.created_canaries == 1 and executor.calls == 1


def test_control_projection_distinguishes_durable_waiting_from_terminal_no_approval():
    status = PaperOperatorControlService._canary_dto(waiting_canary())
    assert status.state.value == "WAITING_FOR_ELIGIBLE_APPROVAL"
    assert status.availability_code == "NO_ELIGIBLE_APPROVAL"
    assert status.started_at is not None and status.completed_at is None


def test_future_approval_continues_same_canary_once_and_replay_stops():
    store = Store(waiting_canary())
    executor = Executor(store, [()])
    subject = worker(store, executor)
    assert subject.run_once() == "COMMAND_CREATED_OR_REPLAYED"
    assert store.value.canary_id == CANARY_ID
    assert store.value.start_request_id == START_REQUEST_ID
    assert store.value.approval_id == "risk-approval:authoritative"
    assert store.value.command_count == 1 and store.value.position_count == 0
    assert subject.run_once() == "NO_WAITING_CANARY"
    assert executor.calls == 1 and store.created_canaries == 1


def test_real_production_approval_adapter_future_visibility_uses_existing_ingestion_boundary():
    store = Store(waiting_canary())
    reader = FakeReader({"BTCUSDT": (row(is_trade_signal=False),)}, now=AS_OF)
    approval_source = PaperProductionApprovalSourceAdapter(
        lambda: FakeSession(), reader=reader, monotonic=lambda: 1.0
    )

    class Ingestion:
        def __init__(self):
            self.requests = []

        def ingest_and_create_entry_order(self, request):
            self.requests.append(request)
            store.value = replace(
                store.value,
                state=PaperFirstCanaryState.RUNNING,
                approval_id=request.paper_risk_approval.approval_id,
                command_count=1,
                command_id=request.command_id,
            )
            return type("Result", (), {"successful": True})()

    ingestion = Ingestion()
    executor = ProductionPaperFirstCanaryExecutor(
        control=Control(), canary_store=store, approval_source=approval_source,
        ingestion_service=ingestion,
    )
    subject = worker(store, executor)
    assert subject.run_once() == "WAITING_FOR_ELIGIBLE_APPROVAL"
    assert ingestion.requests == [] and store.value.command_count == 0

    reader.rows = {"BTCUSDT": (eligible_row(),)}
    reader.snapshot = None
    assert subject.run_once() == "COMMAND_CREATED_OR_REPLAYED"
    assert len(ingestion.requests) == 1
    request = ingestion.requests[0]
    assert request.canary_id == CANARY_ID
    assert request.execution_mode.value == "PAPER"
    assert request.explicit_paper_authorization is True
    assert store.value.start_request_id == START_REQUEST_ID
    assert store.value.approval_id == request.paper_risk_approval.approval_id
    assert store.value.command_count == 1 and store.created_canaries == 1
    assert subject.run_once() == "NO_WAITING_CANARY"
    assert len(ingestion.requests) == 1


def test_two_concurrent_workers_obtain_one_database_claim():
    store = Store(waiting_canary())
    entered, release = Event(), Event()

    class BlockingExecutor(Executor):
        def continue_waiting_canary(self, canary_id):
            self.calls += 1
            entered.set()
            assert release.wait(3)
            self.store.value = replace(
                self.store.value, state=PaperFirstCanaryState.RUNNING,
                approval_id="risk-approval:authoritative", command_count=1,
                command_id="paper:command:authoritative",
            )
            return ()

    executor = BlockingExecutor(store, [])
    database_lock = ExclusiveLock()
    first = worker(store, executor, lock=database_lock)
    second = worker(store, executor, lock=database_lock)
    results = []
    thread = Thread(target=lambda: results.append(first.run_once()))
    thread.start()
    assert entered.wait(3)
    results.append(second.run_once())
    release.set()
    thread.join(3)
    assert sorted(results) == ["CLAIMED_BY_ANOTHER_WORKER", "COMMAND_CREATED_OR_REPLAYED"]
    assert executor.calls == 1 and store.value.command_count == 1


def test_restart_and_crash_before_command_rediscover_same_waiting_row():
    store = Store(waiting_canary())
    executor = Executor(store, [RuntimeError("crash boundary"), ()])
    with pytest.raises(RuntimeError, match="crash boundary"):
        worker(store, executor).run_once()
    assert store.value.state is PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL
    restarted = worker(store, executor)
    assert restarted.run_once() == "COMMAND_CREATED_OR_REPLAYED"
    assert store.value.canary_id == CANARY_ID and store.value.command_count == 1
    assert executor.calls == 2


@pytest.mark.parametrize("state", [PersistentState.DISABLED, PersistentState.EMERGENCY_STOP])
def test_disabled_and_emergency_stop_preempt_continuation(state):
    store = Store(waiting_canary())
    executor = Executor(store, [()])
    assert worker(store, executor, control=Control(state)).run_once() == "CONTROL_PREEMPTED"
    assert executor.calls == 0 and store.value.command_count == 0


@pytest.mark.parametrize("value", [
    waiting_canary(state=PaperFirstCanaryState.COMPLETED),
    waiting_canary(command_count=1, command_id="paper:command:existing"),
    waiting_canary(position_count=1, position_id="paper:position:existing"),
])
def test_terminal_or_consumed_bound_is_not_polled(value):
    store = Store(value)
    executor = Executor(store, [()])
    result = worker(store, executor).run_once()
    assert result in {"NO_WAITING_CANARY", "WAITING_CANARY_NOT_ELIGIBLE"}
    assert executor.calls == 0


def test_poll_interval_is_bounded_and_live_has_no_continuation_state():
    assert continuation_poll_seconds("30") == 30.0
    for value in ("0", "4.99", "3601", "invalid"):
        with pytest.raises(RuntimeError, match="INTERVAL_INVALID"):
            continuation_poll_seconds(value)
    assert not hasattr(PersistentState, "LIVE")


def test_worker_lifecycle_is_active_and_gracefully_stops():
    store = Store(None)
    executor = Executor(store, [])
    subject = worker(store, executor)
    subject.start()
    assert subject.active
    assert subject._stop.wait(0.05) is False
    assert subject.ticks >= 1
    subject.stop()
    assert not subject.active
