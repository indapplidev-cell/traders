from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderRecord,
    PaperPositionRecord,
    PaperSimulationPolicyRecord,
)
from app.engine_market_data.candle import Candle
from app.engine_market_data.continuous_sync_state import SyncStateUpdate
from app.engine_market_data.db.candle_repository import CandleRepository
from app.engine_market_data.sync_state_repository import SyncStateRepository
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_paper.accounting import PaperAccountBaseline, PaperAccountIdentity
from app.engine_paper.controlled_worker import (
    PaperControlledLifecycleWorker,
    SqlAlchemyPaperLifecycleGraphLoader,
)
from app.engine_paper.command_ingestion_service import PaperCommandIngestionService
from app.engine_paper.eligible_approval_ranking import (
    MULTI_SYMBOL_SELECTION_POLICY_VERSION,
    ProductionEligibleApprovalSelector,
)
from app.engine_paper.first_canary_correlation import SqlAlchemyPaperFirstCanaryStore
from app.engine_paper.production_approval import (
    PaperProductionApprovalOutcome,
    PaperProductionApprovalRequest,
    PaperProductionApprovalScope,
    PaperProductionApprovalSourceAdapter,
    SqlAlchemyPaperProductionApprovalReader,
)
from app.engine_paper.production_market_data import (
    PaperProductionMarketDataInputAdapter,
    SqlAlchemyPaperProductionMarketDataReader,
)
from app.engine_paper.scalping_paper_runner import ScalpingPaperRunner
from app.engine_paper.scalping_shadow import ShadowCostInputs
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety.paper_production_control import (
    PaperProductionMutationSafetyGate,
    PaperProductionSafetyControl,
    PersistentState,
)
from app.operator_control.config import PaperOperatorControlConfig
from app.operator_control.continuation_worker import (
    PaperFirstCanaryEligibleApprovalContinuationWorker,
    PostgresCanaryContinuationLock,
)
from app.operator_control.production_executor import (
    ExistingCanaryRuntimeReadiness,
    ProductionPaperFirstCanaryExecutor,
    _foundation_policy,
)
from app.operator_control.production_lifecycle_worker import (
    ProductionPaperFirstCanaryLifecycleWorker,
)
from app.operator_control.schemas import (
    PaperOperatorArmFirstCanaryRequest,
    PaperOperatorStartFirstCanaryRequest,
)
from app.operator_control.service import (
    PaperOperatorArmReadiness,
    PaperOperatorControlService,
)
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter
from app.server_api.services.paper_reporting import PaperReadonlyReportingService


SYMBOL = "BTCUSDT"
BOUNDARY = 1_800_000_000_000
EVALUATION_MS = BOUNDARY + 5_000
ENTRY_MARKET_AS_OF_MS = BOUNDARY + 60_001


class _Owner:
    def assert_active(self, _session) -> None:
        return None


class _DeterministicCostSource:
    """Local replacement for the out-of-scope Binance public HTTP boundary."""

    def load(self, _symbol: str, entry: float, *, safety_margin_bps: float):
        return ShadowCostInputs(
            entry_fee_bps=10,
            exit_fee_bps=10,
            entry_slippage_bps=2,
            exit_slippage_bps=2,
            safety_margin_bps=safety_margin_bps,
            spread_bps=1,
            depth_impact_bps=1,
            fee_source="FOUNDATION_POLICY",
            spread_source="DETERMINISTIC_LOCAL_FIXTURE",
            depth_impact_source="DETERMINISTIC_LOCAL_FIXTURE",
            spread_authoritative=True,
            depth_authoritative=True,
            bid=entry - 0.005,
            ask=entry + 0.005,
            buy_vwap=entry + 0.01,
            sell_vwap=entry - 0.01,
            economic_input_timestamp_ms=BOUNDARY - 1,
            economic_capture_started_at_ms=BOUNDARY - 1,
            decision_cutoff_timestamp_ms=BOUNDARY,
            economic_input_source="DETERMINISTIC_LOCAL_FIXTURE",
            maximum_age_ms=5_000,
            require_causal_timestamp=True,
            reference_quantity=1,
            reference_notional=100,
        )


class _ApprovalReaderAt(SqlAlchemyPaperProductionApprovalReader):
    def __init__(self, at_ms: int) -> None:
        self.at_ms = at_ms

    def read_clock_ms(self, _executor) -> int:
        return self.at_ms


class _MarketReaderAt(SqlAlchemyPaperProductionMarketDataReader):
    def read_clock_ms(self, _executor) -> int:
        return ENTRY_MARKET_AS_OF_MS


def _candles(timeframe: str, count: int) -> tuple[Candle, ...]:
    duration = timeframe_to_milliseconds(timeframe)
    first = BOUNDARY - count * duration
    breakout = (
        Decimal("100.10"), Decimal("100.15"), Decimal("100.20"),
        Decimal("100.25"), Decimal("100.30"), Decimal("100.35"),
        Decimal("100.40"), Decimal("100.45"), Decimal("100.50"),
        Decimal("100.55"), Decimal("100.60"), Decimal("100.65"),
    )
    rows = []
    for index in range(count):
        opened = first + index * duration
        if timeframe == "5m" and index >= count - len(breakout):
            offset = index - (count - len(breakout))
            close = breakout[offset]
            open_price = breakout[offset - 1] if offset else Decimal("100.05")
            high = max(open_price, close) + Decimal("0.12")
            low = min(open_price, close) - Decimal("0.09")
            volume = Decimal("500")
        elif timeframe == "5m":
            open_price = Decimal("100") + Decimal(index % 5) * Decimal("0.02")
            high = open_price + Decimal("0.15")
            low = open_price - Decimal("0.09")
            close = open_price + Decimal("0.02")
            volume = Decimal("100")
        elif timeframe in {"15m", "1h"}:
            open_price = Decimal("102.5") + Decimal((index % 8) - 4) * Decimal("0.05")
            high = open_price + Decimal("0.12")
            low = open_price - Decimal("0.12")
            close = open_price + (Decimal("0.03") if index % 2 else Decimal("-0.03"))
            volume = Decimal("100")
        else:
            open_price = Decimal("100")
            high = Decimal("100.2")
            low = Decimal("99.8")
            close = Decimal("100.05")
            volume = Decimal("100")
        rows.append(Candle(
            symbol=SYMBOL,
            timeframe=timeframe,
            open_time_ms=opened,
            close_time_ms=opened + duration - 1,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            is_closed=True,
            source="paper-e2e-local-fixture",
        ))
    return tuple(rows)


def _seed_foundation(factory) -> None:
    with PaperUnitOfWork(factory) as uow:
        baseline = PaperAccountBaseline(
                "baseline:paper-natural-e2e",
                PaperAccountIdentity("paper-primary", "paper-natural-e2e"),
                Decimal("100"),
                datetime.fromtimestamp((BOUNDARY - 1) / 1000, tz=timezone.utc),
            )
        created = uow.repositories.account_baselines.create_if_absent(baseline)
        assert created == baseline
        assert uow.commit().successful

    repository = CandleRepository(factory)
    for timeframe, count in (("1m", 512), ("5m", 120), ("15m", 64), ("1h", 50)):
        repository.upsert_candles(_candles(timeframe, count))
        assert repository.count(SYMBOL, timeframe) == count
    entry = Candle(
        symbol=SYMBOL,
        timeframe="1m",
        open_time_ms=BOUNDARY,
        close_time_ms=BOUNDARY + 59_999,
        open=Decimal("100.70"),
        high=Decimal("100.90"),
        low=Decimal("100.50"),
        close=Decimal("100.75"),
        volume=Decimal("100"),
        is_closed=True,
        source="paper-e2e-local-fixture",
    )
    assert repository.upsert_candle(entry) is None
    SyncStateRepository(factory).upsert(SyncStateUpdate(
        symbol=SYMBOL,
        timeframe="1m",
        daemon_instance_id="paper-natural-e2e",
        status="OK",
        last_expected_open_time_ms=BOUNDARY,
        last_expected_close_boundary_ms=BOUNDARY + 60_000,
        last_stored_open_time_ms=BOUNDARY,
        last_stored_close_boundary_ms=BOUNDARY + 60_000,
        last_attempt_at=datetime.fromtimestamp(ENTRY_MARKET_AS_OF_MS / 1000, tz=timezone.utc),
        last_success_at=datetime.fromtimestamp(ENTRY_MARKET_AS_OF_MS / 1000, tz=timezone.utc),
        source="paper-e2e-local-fixture",
    ))


def _pipeline(factory):
    config = OrchestratorConfig(
        symbols=(SYMBOL,),
        trade_profile_id="trade-5m-v1",
        primary_timeframe="5m",
        required_timeframes=("1m", "5m", "15m", "1h"),
        minimum_windows={"1m": 60, "5m": 120, "15m": 64, "1h": 50},
    )
    runner = PipelineRunner(
        config,
        CandleRepository(factory),
        paper_runner=ScalpingPaperRunner(
            runtime_parameters=config.runtime_parameters,
            cost_source=_DeterministicCostSource(),
        ),
    )
    result = runner.run(SYMBOL, BOUNDARY)
    assert result.status == "COMPLETED"
    assert result.analysis_status == "ANALYZED"
    assert result.setup_status == "SETUP_CANDIDATE"
    assert result.strategy_status == "ALLOW_RESEARCH_TRADE_PLAN"
    assert result.risk_status == "RISK_PRE_APPROVED_RESEARCH"
    assert result.paper_status == "PAPER_PLAN_READY"
    assert result.analysis_payload["source_market_data_snapshot_id"] == (
        result.market_data_payload["5m"]["snapshot_id"]
    )
    return result


def _persist_natural_approval(factory, result):
    at = datetime.fromtimestamp(EVALUATION_MS / 1000, tz=timezone.utc)
    store = PipelineResultStore(factory, clock=lambda: at, owner_guard=_Owner())
    run_id = store.reserve(
        SYMBOL,
        "5m",
        BOUNDARY,
        daemon_instance_id="paper-natural-e2e",
        trigger_source="DETERMINISTIC_POSTGRES_E2E",
        trade_profile_id="trade-5m-v1",
        freshness_deadline_at=at,
    )
    assert run_id is not None
    claim = store.get_claim(run_id)
    assert store.mark_running(
        claim,
        daemon_instance_id="paper-natural-e2e",
        checked_at=at,
        payload={"status": "READY"},
    )
    assert store.finish(run_id, result, freshness_status="READY")
    return run_id


def _approval_source(factory, at_ms=EVALUATION_MS):
    return PaperProductionApprovalSourceAdapter(
        factory,
        reader=_ApprovalReaderAt(at_ms),
        monotonic=lambda: 1.0,
    )


def _seed_simulation_policy(factory, candidate) -> None:
    policy = _foundation_policy()
    with factory.begin() as session:
        session.add(PaperSimulationPolicyRecord(
            policy_id=policy.simulation_policy_id,
            policy_version=1,
            status="ACTIVE",
            price_source=policy.price_source.value,
            timeframe=policy.timeframe,
            latency_candles=policy.latency_candles,
            slippage_bps=policy.slippage_bps,
            fee_bps=policy.fee_bps,
            partial_fill_enabled=policy.partial_fill_enabled,
            future_data_allowed=policy.future_data_allowed,
            intrabar_conflict_policy=policy.intrabar_conflict_policy.value,
            configuration_fingerprint=(
                candidate.paper_strategy_approval.configuration_fingerprint
            ),
            created_at=candidate.paper_strategy_approval.approved_at,
            retired_at=None,
        ))


def _runtime(factory, engine, control, source):
    store = SqlAlchemyPaperFirstCanaryStore(factory)
    gate = PaperProductionMutationSafetyGate(control)
    uow = lambda: PaperUnitOfWork(factory)
    executor = ProductionPaperFirstCanaryExecutor(
        control=control,
        canary_store=store,
        approval_source=source,
        ingestion_service=PaperCommandIngestionService(uow, factory),
        mutation_safety_gate=gate,
        runtime_readiness=lambda: ExistingCanaryRuntimeReadiness(
            True, True, True, True, True
        ),
    )
    lock = PostgresCanaryContinuationLock(engine)
    continuation = PaperFirstCanaryEligibleApprovalContinuationWorker(
        control=control,
        canary_store=store,
        executor=executor,
        lock=lock,
        poll_seconds=5,
    )
    lifecycle_core = PaperControlledLifecycleWorker.from_factories(uow, factory)
    lifecycle = ProductionPaperFirstCanaryLifecycleWorker(
        control=control,
        canary_store=store,
        graph_loader=SqlAlchemyPaperLifecycleGraphLoader(uow),
        lifecycle_worker=lifecycle_core,
        market_data=PaperProductionMarketDataInputAdapter(
            factory,
            reader=_MarketReaderAt(),
            monotonic=lambda: 2.0,
        ),
        mutation_safety_gate=gate,
        runtime_readiness=lambda: ExistingCanaryRuntimeReadiness(
            True, True, True, True, True
        ),
        lock=lock,
        readonly_base_url="http://127.0.0.1:1",
        poll_seconds=5,
    )
    service = PaperOperatorControlService(
        config=PaperOperatorControlConfig.production_paper(),
        control=control,
        readiness=PaperOperatorArmReadiness.isolated_ready,
        executor=executor,
        canary_store=store,
    )
    return store, executor, continuation, lifecycle, service


def _arm_and_wait(service):
    armed = service.arm_first_canary(PaperOperatorArmFirstCanaryRequest(
        request_id="paper-natural-e2e-arm",
        expected_generation=1,
        environment="PRODUCTION",
        mode="PAPER",
        max_new_commands=1,
        max_open_positions=1,
        allowed_symbols=(SYMBOL,),
        operator_acknowledgement=True,
        paper_acknowledgement=True,
        live_forbidden_acknowledgement=True,
    ))
    started = service.start_first_canary(PaperOperatorStartFirstCanaryRequest(
        request_id="paper-natural-e2e-start",
        expected_generation=armed.generation_after,
        canary_id=armed.canary_id,
        arming_transition_id=armed.arming_transition_id,
        canary_acknowledgement=True,
    ))
    assert started.state_after == "WAITING_FOR_ELIGIBLE_APPROVAL"
    assert started.executed is False
    return armed.canary_id


def test_natural_approval_opens_paper_position_end_to_end(
    natural_e2e_sessions, natural_e2e_engine, tmp_path
):
    factory = natural_e2e_sessions
    _seed_foundation(factory)
    source = _approval_source(factory)
    control = PaperProductionSafetyControl(tmp_path / "isolated-paper-control")
    disabled = control.initialize_disabled(acknowledge=True)
    assert disabled.state.value == "DISABLED"
    store, executor, continuation, lifecycle, service = _runtime(
        factory, natural_e2e_engine, control, source
    )
    canary_id = _arm_and_wait(service)
    waiting = store.get(canary_id)
    assert waiting.max_new_commands == waiting.max_open_positions == 1
    assert waiting.command_count == waiting.position_count == 0
    assert control.read_authoritative().state is PersistentState.ARMED
    assert not hasattr(PersistentState, "LIVE")

    result = _pipeline(factory)
    snapshot_id = result.market_data_payload["5m"]["snapshot_id"]
    analysis_id = result.analysis_payload["snapshot_id"]
    plan_id = result.paper_payload["paper_plan_id"]
    run_id = _persist_natural_approval(factory, result)

    adapter = source.read(PaperProductionApprovalRequest(
        PaperProductionApprovalScope((SYMBOL,), "5m", max_candidates=1),
        request_id="paper-natural-e2e-adapter-proof",
        as_of_ms=EVALUATION_MS,
    ))
    classified = adapter.symbol_results[0]
    assert classified.outcome is PaperProductionApprovalOutcome.ELIGIBLE_APPROVAL
    assert classified.candidate is not None
    candidate = classified.candidate
    assert candidate.watermark.source_market_data_snapshot_id == snapshot_id
    selection = ProductionEligibleApprovalSelector().select(
        (candidate,), policy_version=MULTI_SYMBOL_SELECTION_POLICY_VERSION
    )
    assert selection.winner == candidate
    assert selection.diagnostics.eligible_count == 1
    _seed_simulation_policy(factory, candidate)

    assert continuation.run_once() == "COMMAND_CREATED_OR_REPLAYED"
    after_command = store.get(canary_id)
    assert after_command.command_count == 1
    assert after_command.position_count == 0
    assert executor.last_selection_diagnostics.winner_symbol == SYMBOL
    assert continuation.run_once() == "NO_WAITING_CANARY"

    lifecycle_result = lifecycle.run_once()
    assert lifecycle_result.endswith(":POSITION_OPEN_CURSOR_READY")
    after_entry = store.get(canary_id)
    assert after_entry.command_count == 1
    assert after_entry.position_count == 1
    assert after_entry.position_id is not None

    restarted_continuation = _runtime(
        factory, natural_e2e_engine, control, source
    )[2]
    assert restarted_continuation.run_once() == "NO_WAITING_CANARY"
    restarted_lifecycle = _runtime(
        factory, natural_e2e_engine, control, source
    )[3]
    assert restarted_lifecycle.run_once() == "WAITING_FOR_EXIT_CANDLE"

    with factory() as session:
        command = session.scalar(select(PaperExecutionCommandRecord))
        orders = tuple(session.scalars(select(PaperOrderRecord)))
        fills = tuple(session.scalars(select(PaperFillRecord)))
        positions = tuple(session.scalars(select(PaperPositionRecord)))
        journal_count = session.scalar(
            select(func.count()).select_from(PaperJournalEntryRecord)
        )
    assert command is not None
    assert command.pipeline_run_id == run_id
    assert command.analysis_result_id == analysis_id
    assert command.valid_until_ms > command.closed_until_ms
    assert command.processing_status == "PENDING"
    assert len(orders) == 1 and orders[0].order_role == "ENTRY"
    assert orders[0].command_id == command.command_id
    assert orders[0].state == "FILLED"
    assert len(fills) == 1 and fills[0].fill_role == "ENTRY"
    assert fills[0].order_id == orders[0].order_id
    assert fills[0].quantity > 0
    assert len(positions) == 1 and positions[0].state == "OPEN"
    assert positions[0].entry_order_id == orders[0].order_id
    assert positions[0].entry_fill_id == fills[0].fill_id
    assert positions[0].entry_fees == fills[0].fee_amount
    assert positions[0].average_entry_price == fills[0].price
    assert journal_count == 6

    policy = _foundation_policy()
    expected_price = (
        Decimal("100.70") * (Decimal("1") + policy.slippage_bps / Decimal("10000"))
    ).quantize(policy.price_quantum)
    expected_fee = (
        fills[0].quantity * expected_price * policy.fee_bps / Decimal("10000")
    ).quantize(policy.fee_quantum)
    assert fills[0].price == expected_price
    assert fills[0].fee_amount == expected_fee

    projection = PaperReadonlyReportingService(
        SqlAlchemyReadAdapter(factory)
    ).positions(limit=10, cursor=None, state="OPEN", symbol=SYMBOL)
    assert len(projection.items) == 1
    ui_position = projection.items[0]
    assert ui_position.position_id == positions[0].position_id
    assert ui_position.command_id == command.command_id
    assert ui_position.entry_price == str(positions[0].average_entry_price).rstrip("0").rstrip(".")
    assert ui_position.state == "OPEN"

    with factory() as session:
        counts_after_retry = (
            session.scalar(select(func.count()).select_from(PaperExecutionCommandRecord)),
            session.scalar(select(func.count()).select_from(PaperOrderRecord)),
            session.scalar(select(func.count()).select_from(PaperFillRecord)),
            session.scalar(select(func.count()).select_from(PaperPositionRecord)),
        )
    assert counts_after_retry == (1, 1, 1, 1)

    # Stable trace is emitted only for the isolated test log/evidence capture.
    print({
        "snapshot_id": snapshot_id,
        "analysis_id": analysis_id,
        "paper_plan_id": plan_id,
        "approval_id": candidate.paper_risk_approval.approval_id,
        "adapter_outcome": classified.outcome.value,
        "candidate_id": candidate.candidate_id,
        "winner": selection.winner.candidate_id,
        "command_id": command.command_id,
        "entry_order_id": orders[0].order_id,
        "fill_id": fills[0].fill_id,
        "position_id": positions[0].position_id,
        "position_state": positions[0].state,
    })
    print({
        "database_proof": {
            "paper_execution_commands": 1,
            "paper_orders": 1,
            "paper_fills": 1,
            "paper_positions": 1,
            "paper_exit_decisions": 0,
            "paper_journal_entries": journal_count,
            "command_status": command.processing_status,
            "entry_order_state": orders[0].state,
            "fill_price": str(fills[0].price),
            "fill_fee": str(fills[0].fee_amount),
            "position_state": positions[0].state,
        },
        "retry_counts": counts_after_retry,
        "ui_projection": {
            "active_positions": len(projection.items),
            "command_id": ui_position.command_id,
            "position_id": ui_position.position_id,
            "symbol": ui_position.symbol,
            "state": ui_position.state,
        },
    })


def test_expired_natural_approval_does_not_create_command(
    natural_e2e_sessions, natural_e2e_engine, tmp_path
):
    factory = natural_e2e_sessions
    _seed_foundation(factory)
    result = _pipeline(factory)
    _persist_natural_approval(factory, result)
    expired_source = _approval_source(factory, BOUNDARY + 300_001)
    control = PaperProductionSafetyControl(tmp_path / "expired-paper-control")
    control.initialize_disabled(acknowledge=True)
    store, _executor, _continuation, _lifecycle, service = _runtime(
        factory, natural_e2e_engine, control, expired_source
    )
    canary_id = _arm_and_wait(service)
    assert store.get(canary_id).command_count == 0
    with factory() as session:
        assert session.scalar(
            select(func.count()).select_from(PaperExecutionCommandRecord)
        ) == 0
