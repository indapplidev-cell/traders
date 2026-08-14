from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.paper_models import TradingUniverseRuntimeStateRecord
from app.engine_paper.first_canary_correlation import SqlAlchemyPaperFirstCanaryStore
from app.engine_safety.paper_production_control import (
    ArmReadinessPreflight,
    PaperProductionArmingScope,
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
)
from app.operator_control.config import PaperOperatorControlConfig
from app.operator_control.schemas import PaperOperatorTransitionRequest
from app.operator_control.service import PaperOperatorControlService
from app.trading_universe.activation import (
    SqlAlchemyTradingUniverseStore,
    TradingUniverseActivationError,
)


NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)


@pytest.fixture()
def stores():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with sessions.begin() as session:
        session.add(TradingUniverseRuntimeStateRecord(
            environment="PRODUCTION",
            active_version_id="trading-universe-v1",
            previous_version_id=None,
            generation=1,
            activated_at=NOW,
            activation_reason="INITIAL_V1_BASELINE",
            runtime_revision="0015",
        ))
    yield SqlAlchemyTradingUniverseStore(sessions), SqlAlchemyPaperFirstCanaryStore(sessions)
    engine.dispose()


def test_v2_activation_is_single_transaction_and_idempotent(stores):
    universe, _ = stores
    state = universe.activate(
        expected_active_version_id="trading-universe-v1",
        target_version_id="trading-universe-v2",
        reason="CONTROLLED_V2_ACTIVATION_AFTER_V1_STOP",
        runtime_revision="revision-under-test",
        now=NOW,
    )
    assert state.active_version_id == "trading-universe-v2"
    assert state.previous_version_id == "trading-universe-v1"
    assert state.generation == 2
    assert universe.active_universe().symbols == (
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "LINKUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SUIUSDT",
    )
    assert universe.activate(
        expected_active_version_id="trading-universe-v1",
        target_version_id="trading-universe-v2",
        reason="CONTROLLED_V2_ACTIVATION_AFTER_V1_STOP",
        runtime_revision="revision-under-test",
    ) == state


def test_active_canary_blocks_activation_and_controlled_waiting_stop_preserves_lineage(stores):
    universe, canaries = stores
    canary = canaries.reserve_arm(
        request_id="arm-v1",
        fingerprint="f" * 64,
        expected_generation=3,
        allowed_symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        universe_version_id="trading-universe-v1",
        selection_policy_version="exactly-one-eligible-v1",
        now=NOW,
    )
    canary = canaries.complete_arm(canary.canary_id, "transition-v1", 4, NOW)
    canary = canaries.reserve_start(canary.canary_id, "start-v1", "s" * 64, "transition-v1", 4)
    canary = canaries.mark_started(canary.canary_id, no_approval=True, now=NOW)
    with pytest.raises(TradingUniverseActivationError, match="ACTIVE_CANARY"):
        universe.activate(
            expected_active_version_id="trading-universe-v1",
            target_version_id="trading-universe-v2",
            reason="CONTROLLED_V2_ACTIVATION_AFTER_V1_STOP",
            runtime_revision="revision-under-test",
        )
    stopped = canaries.stop_waiting(
        canary.canary_id,
        control_generation=5,
        reason="CONTROLLED_OPERATOR_DISABLE_WAITING_ZERO_TRADE",
        now=NOW,
    )
    assert stopped.state == "STOPPED"
    assert stopped.universe_version_id == "trading-universe-v1"
    assert stopped.selection_policy_version == "exactly-one-eligible-v1"
    assert stopped.allowed_symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert (stopped.command_count, stopped.position_count) == (0, 0)
    assert canaries.current() is None


def test_normal_control_disable_stops_only_waiting_zero_trade_canary(stores, tmp_path):
    universe, canaries = stores
    control = PaperProductionSafetyControl(tmp_path / "control", acl_checker=lambda _path: True)
    control.initialize_disabled(acknowledge=True)
    armed = control.transition(
        PersistentState.ARMED,
        expected_generation=1,
        reason=ReasonCode.OPERATOR_ARM,
        acknowledge=True,
        acknowledge_paper_arming=True,
        preflight=ArmReadinessPreflight(True, True, True, True, True, True, True, True, True),
        arming_scope=PaperProductionArmingScope(1, 1, ("BTCUSDT", "ETHUSDT", "SOLUSDT")),
    )
    canary = canaries.reserve_arm(
        request_id="arm-normal-disable",
        fingerprint="a" * 64,
        expected_generation=1,
        allowed_symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        universe_version_id="trading-universe-v1",
        selection_policy_version="exactly-one-eligible-v1",
        now=NOW,
    )
    canary = canaries.complete_arm(canary.canary_id, armed.transition_id, armed.generation, NOW)
    canaries.reserve_start(canary.canary_id, "start-normal-disable", "b" * 64, armed.transition_id, armed.generation)
    canaries.mark_started(canary.canary_id, no_approval=True, now=NOW)
    service = PaperOperatorControlService(
        config=PaperOperatorControlConfig.production_paper(),
        control=control,
        canary_store=canaries,
        active_universe=universe.active_universe,
    )
    decision = service.disable(PaperOperatorTransitionRequest(
        request_id="disable-normal-waiting",
        expected_generation=armed.generation,
        operator_acknowledgement=True,
    ))
    stopped = canaries.get(canary.canary_id)
    assert decision.operation == "DISABLE" and decision.state_after == "DISABLED"
    assert stopped is not None and stopped.state == "STOPPED"
    assert stopped.terminal_reason == "CONTROLLED_OPERATOR_DISABLE_WAITING_ZERO_TRADE"
    assert control.read_authoritative().state is PersistentState.DISABLED
