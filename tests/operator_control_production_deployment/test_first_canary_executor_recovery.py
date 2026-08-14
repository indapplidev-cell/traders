from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from app.engine_paper.first_canary_correlation import (
    PaperFirstCanarySession,
    PaperFirstCanaryState,
    SqlAlchemyPaperFirstCanaryStore,
)
from app.engine_safety.paper_production_control import (
    ArmReadinessPreflight,
    PaperProductionArmingScope,
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
)
from app.operator_control.auth import ProtectedFileOperatorCredentialBinding
from app.operator_control.config import PaperOperatorControlConfig
from app.operator_control.production_executor import ProductionPaperFirstCanaryExecutor
from app.operator_control.runtime import create_runtime_app
from app.operator_control.schemas import PaperOperatorStartFirstCanaryRequest
from app.operator_control.service import (
    DisabledPaperFirstCanaryExecutor,
    PaperOperatorArmReadiness,
    PaperOperatorControlService,
)


NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)
CANARY_ID = "8c52768d-2a3a-47cb-acdc-3d1cb1b6ce9d"
REQUEST_ID = "client-start-4df3c10a480248c9bff16cf398b06dfe"


def armed_control(root: Path):
    control = PaperProductionSafetyControl(root, acl_checker=lambda _path: True)
    control.initialize_disabled(acknowledge=True)
    state = control.transition(
        PersistentState.ARMED,
        expected_generation=1,
        reason=ReasonCode.OPERATOR_ARM,
        acknowledge=True,
        acknowledge_paper_arming=True,
        preflight=ArmReadinessPreflight(True, True, True, True, True, True, True, True, True),
        arming_scope=PaperProductionArmingScope(1, 1, ("BTCUSDT",)),
    )
    return control, state


def session(state, *, canary_state=PaperFirstCanaryState.ARMED, started_at=None):
    return PaperFirstCanarySession(
        CANARY_ID, "PRODUCTION", "PAPER", canary_state, NOW, NOW, started_at, None,
        "original-arm-request", state.transition_id, state.generation, REQUEST_ID,
        state.generation, 1, 1, ("BTCUSDT",), None, 0, None, 0, None, False,
        "NOT_STARTED", "NOT_STARTED", None, None, (), 3,
    )


class PendingStore:
    def __init__(self, value): self.value = value
    def get(self, canary_id): return self.value if canary_id == CANARY_ID else None
    def current(self): return self.value
    def reserve_start(self, canary_id, request_id, fingerprint, transition_id, generation):
        assert (canary_id, request_id, transition_id, generation) == (
            CANARY_ID, REQUEST_ID, self.value.arming_transition_id, self.value.arming_generation
        )
        assert fingerprint == self.fingerprint
        return self.value
    def mark_started(self, canary_id, *, no_approval, now):
        target = PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL if no_approval else PaperFirstCanaryState.RUNNING
        self.value = replace(self.value, state=target if self.value.state is PaperFirstCanaryState.ARMED else self.value.state, started_at=now)
        return self.value


class Executor:
    def __init__(self, store): self.store, self.calls = store, 0
    def preflight(self, **_): return ()
    def start_bounded_canary(self, **_):
        self.calls += 1
        self.store.value = replace(self.store.value, state=PaperFirstCanaryState.RUNNING)
        return ()
    def status(self): raise AssertionError


def service(control, store, executor):
    return PaperOperatorControlService(
        config=PaperOperatorControlConfig.production_paper(), control=control,
        readiness=PaperOperatorArmReadiness.isolated_ready,
        canary_store=store, executor=executor,
    )


def test_exact_pending_request_recovery_and_restart_replay_are_idempotent(tmp_path):
    control, state = armed_control(tmp_path / "control")
    store = PendingStore(session(state))
    executor = Executor(store)
    first = service(control, store, executor)
    request = PaperOperatorStartFirstCanaryRequest(
        request_id=REQUEST_ID, expected_generation=state.generation,
        canary_id=CANARY_ID, arming_transition_id=state.transition_id,
        canary_acknowledgement=True,
    )
    store.fingerprint = first._fingerprint("START_FIRST_CANARY", request)
    recovered = first.recover_pending_start(CANARY_ID)
    assert recovered.request_id == REQUEST_ID and recovered.canary_id == CANARY_ID
    assert recovered.executed and store.value.started_at is not None
    assert executor.calls == 1

    replay = service(control, store, executor).recover_pending_start(CANARY_ID)
    assert replay.request_id == REQUEST_ID and replay.canary_id == CANARY_ID
    assert executor.calls == 1
    assert store.value.command_count == 0 and store.value.position_count == 0


def test_recovery_repairs_started_at_after_executor_commit_crash(tmp_path):
    control, state = armed_control(tmp_path / "control")
    store = PendingStore(session(state, canary_state=PaperFirstCanaryState.RUNNING))
    executor = Executor(store)
    subject = service(control, store, executor)
    request = PaperOperatorStartFirstCanaryRequest(
        request_id=REQUEST_ID, expected_generation=state.generation,
        canary_id=CANARY_ID, arming_transition_id=state.transition_id,
        canary_acknowledgement=True,
    )
    store.fingerprint = subject._fingerprint("START_FIRST_CANARY", request)
    result = subject.recover_pending_start(CANARY_ID)
    assert result.executed and result.started_at is not None
    assert executor.calls == 0
    assert store.value.state is PaperFirstCanaryState.RUNNING


def test_runtime_auto_composes_real_executor_and_isolated_mode_stays_disabled(monkeypatch, tmp_path):
    token = tmp_path / "token"
    token.write_bytes(b"focused-control-token-material-0123456789abcdef")
    binding = ProtectedFileOperatorCredentialBinding(token)
    control, _ = armed_control(tmp_path / "control")
    durable = SqlAlchemyPaperFirstCanaryStore(lambda: None)
    engine = object()
    sessions = lambda: None
    monkeypatch.setattr("app.operator_control.runtime._production_canary_store", lambda: (durable, engine))
    monkeypatch.setattr("app.operator_control.runtime.sessionmaker", lambda **_: sessions)
    app = create_runtime_app(
        credential_binding=binding, control=control, runtime_identity="focused-build"
    )
    assert isinstance(app.state.first_canary_executor, ProductionPaperFirstCanaryExecutor)
    assert not isinstance(app.state.first_canary_executor, DisabledPaperFirstCanaryExecutor)
    assert app.state.runtime_identity == "focused-build"

    disabled = create_runtime_app(
        credential_binding=binding, control=control, runtime_identity="isolated-disabled",
        require_production_store=False,
    )
    assert isinstance(disabled.state.first_canary_executor, DisabledPaperFirstCanaryExecutor)
