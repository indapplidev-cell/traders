from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.engine_execution.paper_idempotency import (
    command_idempotency_key,
    order_idempotency_key,
)
from app.engine_execution.paper_models import PaperExecutionCommand, PaperOrder
from app.engine_execution.paper_state_machine import fill_order
from app.engine_exit.paper_exit import PaperExitDecision
from app.engine_paper.fill_policy import (
    PaperFillPriceSource,
    PaperFillSimulationPolicy,
    PaperIntrabarConflictPolicy,
)
from app.engine_paper.fill_simulator import (
    FillSimulationRequest,
    PaperFillCandle,
    PaperFillRole,
    simulate_paper_fill,
)
from app.engine_paper.order_execution_service import (
    PaperCloseExecutionRequest,
    PaperEntryExecutionRequest,
)
from app.engine_paper.repositories import (
    CloseFillGraph,
    EntryFillGraph,
    PaperCommandGraph,
)
from app.engine_paper.repository_results import RepositoryOutcome, result
from app.engine_position.paper_models import PaperPosition
from app.engine_position.paper_state_machine import apply_close_fill
from app.engine_safety import (
    ExecutionMode,
    PaperExitCause,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
)

# Register the existing fail-closed loopback ``paper_test_*`` PostgreSQL
# fixtures for this focused service suite.  The fixture owns migration to 0009
# and never accepts a production/non-loopback database URL.
from tests.paper_repository.conftest import (  # noqa: F401,E402
    paper_session_factory,
    repository_postgres_engine,
)


NOW = datetime(2026, 7, 29, 16, 0, tzinfo=timezone.utc)
OPERATION_AT = NOW + timedelta(minutes=2)
BOUNDARY = int(NOW.timestamp() * 1000)
CLOSE_BOUNDARY = BOUNDARY + 60_000
Q = Decimal("0.000000000000000001")


def make_policy(**changes):
    values = {
        "simulation_policy_id": "simulation:foundation:v1",
        "fee_policy_id": "fee:quote:10bps:v1",
        "slippage_policy_id": "slippage:adverse:2bps:v1",
        "latency_policy_id": "latency:one-closed-1m:v1",
        "price_source": PaperFillPriceSource.NEXT_ELIGIBLE_CLOSED_1M_OPEN,
        "timeframe": "1m",
        "latency_candles": 1,
        "slippage_bps": Decimal("2"),
        "fee_bps": Decimal("10"),
        "partial_fill_enabled": False,
        "future_data_allowed": False,
        "intrabar_conflict_policy": PaperIntrabarConflictPolicy.STOP_FIRST_CONSERVATIVE,
        "price_quantum": Q,
        "fee_quantum": Q,
        "contract_version": "PAPER_FILL_SIMULATION_V1",
    }
    values.update(changes)
    return PaperFillSimulationPolicy(**values)


def make_command(*, side=PaperSide.LONG, **changes):
    values = {
        "command_id": "command:service:1",
        "idempotency_key": command_idempotency_key(
            pipeline_run_id="run:service:1",
            analysis_result_id="analysis:service:1",
            setup_id="setup:service:1",
            strategy_decision_id="strategy:service:1",
            risk_decision_id="risk:service:1",
            symbol="BTCUSDT",
            side=side,
            closed_until_ms=BOUNDARY,
            configuration_fingerprint="config:service:v1",
        ),
        "mode": ExecutionMode.PAPER,
        "symbol": "BTCUSDT",
        "side": side,
        "order_type": PaperOrderType.MARKET_SIMULATED,
        "requested_quantity": Decimal("2"),
        "requested_notional": Decimal("200"),
        "entry_reference_price": Decimal("100"),
        "stop_price": Decimal("110") if side is PaperSide.SHORT else Decimal("90"),
        "target_price": Decimal("90") if side is PaperSide.SHORT else Decimal("110"),
        "strategy_decision_id": "strategy:service:1",
        "risk_decision_id": "risk:service:1",
        "setup_id": "setup:service:1",
        "pipeline_run_id": "run:service:1",
        "analysis_result_id": "analysis:service:1",
        "closed_until_ms": BOUNDARY,
        "created_at": NOW,
        "valid_until_ms": CLOSE_BOUNDARY,
        "configuration_fingerprint": "config:service:v1",
        "simulation_policy_id": "simulation:foundation:v1",
        "fee_policy_id": "fee:quote:10bps:v1",
        "slippage_policy_id": "slippage:adverse:2bps:v1",
        "latency_policy_id": "latency:one-closed-1m:v1",
        "final_paper_approval": True,
        "input_health_status": PaperInputHealthStatus.CURRENT,
        "future_bars_used": False,
    }
    values.update(changes)
    return PaperExecutionCommand(**values)


def make_order(command, *, role="ENTRY", suffix="entry", **changes):
    values = {
        "order_id": f"order:service:{suffix}",
        "command_id": command.command_id,
        "idempotency_key": order_idempotency_key(command.command_id, role),
        "symbol": command.symbol,
        "side": command.side,
        "order_type": command.order_type,
        "state": PaperOrderState.OPEN,
        "requested_quantity": command.requested_quantity,
        "filled_quantity": Decimal("0"),
        "average_fill_price": None,
        "total_fees": Decimal("0"),
        "created_at": NOW,
        "updated_at": NOW,
        "version": 2,
        "reason_code": PaperReasonCode.PAPER_ORDER_OPENED,
        "applied_fill_id": None,
    }
    values.update(changes)
    return PaperOrder(**values)


def make_candle(**changes):
    values = {
        "symbol": "BTCUSDT",
        "timeframe": "1m",
        "open_time_ms": BOUNDARY,
        "close_boundary_ms": CLOSE_BOUNDARY,
        "open_price": Decimal("100"),
        "high_price": Decimal("105"),
        "low_price": Decimal("95"),
        "close_price": Decimal("101"),
        "is_closed": True,
        "observed_closed_until_ms": CLOSE_BOUNDARY,
    }
    values.update(changes)
    return PaperFillCandle(**values)


def simulated_fill(command, order, policy, candle, role):
    return simulate_paper_fill(
        FillSimulationRequest(
            command=command,
            order=order,
            fill_role=role,
            quote_asset="USDT",
            simulation_policy=policy,
            candidate_candles=(candle,),
            market_snapshot_closed_until_ms=CLOSE_BOUNDARY,
            correlation_id="correlation:service:1",
            causation_id="causation:service:1",
        )
    ).fill


def make_position(command, entry_order, *, state=PaperPositionState.CLOSING, **changes):
    values = {
        "position_id": "position:service:1",
        "mode": ExecutionMode.PAPER,
        "symbol": command.symbol,
        "side": command.side,
        "state": state,
        "entry_order_id": entry_order.order_id,
        "entry_fill_id": "fill:service:entry:prior",
        "entry_quantity": command.requested_quantity,
        "remaining_quantity": command.requested_quantity,
        "average_entry_price": Decimal("100"),
        "average_exit_price": None,
        "entry_fees": Decimal("0.2"),
        "exit_fees": Decimal("0"),
        "realized_pnl": Decimal("-0.2"),
        "unrealized_pnl": Decimal("0"),
        "stop_price": command.stop_price,
        "target_price": command.target_price,
        "opened_at": NOW,
        "closed_at": None,
        "last_mark_price": Decimal("100"),
        "last_mark_closed_until_ms": BOUNDARY,
        "version": 1,
        "reason_code": PaperReasonCode.PAPER_POSITION_CLOSING,
        "exit_fill_id": None,
    }
    values.update(changes)
    return PaperPosition(**values)


class FakeRepositories:
    def __init__(self, command, order, *, position=None, decision=None):
        self.command = command
        self.order = order
        self.position = position
        self.decision = decision
        self.active_position = None
        self.atomic_calls = 0
        self.atomic_outcome = None
        self.commands = SimpleNamespace(
            get_command=self.get_command,
            get_command_graph=self.get_command_graph,
        )
        self.orders = SimpleNamespace(get_order=self.get_order)
        self.positions = SimpleNamespace(
            get_position=self.get_position,
            get_active_position=self.get_active_position,
        )

    def get_command(self, command_id):
        return self.command if self.command and self.command.command_id == command_id else None

    def get_order(self, order_id):
        return self.order if self.order and self.order.order_id == order_id else None

    def get_position(self, position_id):
        return (
            self.position
            if self.position and self.position.position_id == position_id
            else None
        )

    def get_active_position(self, mode, symbol):
        return self.active_position

    def get_command_graph(self, command_id, *, limit=100):
        graph = PaperCommandGraph(
            self.command,
            (self.order,) if self.order else (),
            (),
            (self.position,) if self.position else (),
            (self.decision,) if self.decision else (),
            (),
        )
        return result(RepositoryOutcome.EXISTING_IDEMPOTENT, graph)

    def apply_entry_fill_and_open_position(
        self,
        order_id,
        expected_order_version,
        fill,
        position,
        order_event,
        position_event,
        journal_entries,
    ):
        self.atomic_calls += 1
        if self.atomic_outcome is not None:
            return result(self.atomic_outcome)
        changed = fill_order(
            self.order,
            fill,
            expected_version=expected_order_version,
            event_id=order_event.event_id,
        ).order
        graph = EntryFillGraph(changed, fill, position)
        self.order = changed
        self.position = position
        return result(RepositoryOutcome.CREATED, graph)

    def apply_close_fill_and_close_position(
        self,
        exit_decision_id,
        position_id,
        expected_position_version,
        close_order_id,
        expected_order_version,
        fill,
        events,
        journal_entries,
    ):
        self.atomic_calls += 1
        if self.atomic_outcome is not None:
            return result(self.atomic_outcome)
        order_event = next(item for item in events if item.aggregate_type == "paper_order")
        position_event = next(
            item for item in events if item.aggregate_type == "paper_position"
        )
        changed_order = fill_order(
            self.order,
            fill,
            expected_version=expected_order_version,
            event_id=order_event.event_id,
        ).order
        changed_position = apply_close_fill(
            self.position,
            fill,
            expected_version=expected_position_version,
            event_id=position_event.event_id,
        ).position
        graph = CloseFillGraph(changed_order, fill, changed_position)
        self.order = changed_order
        self.position = changed_position
        return result(RepositoryOutcome.UPDATED, graph)


class FakeUow:
    def __init__(self, repositories, commit_outcome=RepositoryOutcome.UPDATED):
        self.repositories = repositories
        self.commit_outcome = commit_outcome
        self.commit_calls = 0
        self.rollback_calls = 0

    def __enter__(self):
        return self

    def commit(self):
        self.commit_calls += 1
        return result(self.commit_outcome)

    def __exit__(self, exc_type, exc, traceback):
        if self.commit_calls == 0:
            self.rollback_calls += 1


@pytest.fixture
def entry_context():
    command = make_command()
    order = make_order(command)
    policy = make_policy()
    candle = make_candle()
    fill = simulated_fill(command, order, policy, candle, PaperFillRole.ENTRY)
    request = PaperEntryExecutionRequest(
        command_id=command.command_id,
        order_id=order.order_id,
        expected_order_version=order.version,
        fill_role=PaperFillRole.ENTRY,
        candidate_candles=(candle,),
        market_snapshot_closed_until_ms=CLOSE_BOUNDARY,
        simulation_policy=policy,
        price_quantum=policy.price_quantum,
        fee_quantum=policy.fee_quantum,
        quote_asset="USDT",
        fill_id=fill.fill_id,
        position_id="position:service:entry",
        order_event_id="event:service:entry:order",
        position_event_id="event:service:entry:position",
        journal_entry_ids=(
            "journal:service:entry:order",
            "journal:service:entry:position",
        ),
        correlation_id="correlation:service:1",
        causation_id="causation:service:1",
        operation_at=OPERATION_AT,
    )
    repositories = FakeRepositories(command, order)
    uow = FakeUow(repositories)
    return SimpleNamespace(
        command=command,
        order=order,
        policy=policy,
        candle=candle,
        fill=fill,
        request=request,
        repositories=repositories,
        uow=uow,
    )


@pytest.fixture
def close_context():
    command = make_command()
    entry_order = make_order(command, suffix="prior-entry")
    close_order = make_order(command, role="EXIT", suffix="close")
    position = make_position(command, entry_order)
    decision = PaperExitDecision(
        exit_decision_id="exit:service:1",
        idempotency_key="exit:key:service:1",
        position_id=position.position_id,
        position_version=0,
        cause=PaperExitCause.STOP_LOSS,
        decision_price=Decimal("90"),
        requested_close_quantity=position.remaining_quantity,
        source_closed_until_ms=BOUNDARY,
        decided_at=NOW,
        reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
    )
    policy = make_policy()
    candle = make_candle()
    fill = simulated_fill(command, close_order, policy, candle, PaperFillRole.CLOSE)
    request = PaperCloseExecutionRequest(
        command_id=command.command_id,
        order_id=close_order.order_id,
        expected_order_version=close_order.version,
        position_id=position.position_id,
        expected_position_version=position.version,
        exit_decision_id=decision.exit_decision_id,
        fill_role=PaperFillRole.CLOSE,
        candidate_candles=(candle,),
        market_snapshot_closed_until_ms=CLOSE_BOUNDARY,
        simulation_policy=policy,
        price_quantum=policy.price_quantum,
        fee_quantum=policy.fee_quantum,
        quote_asset="USDT",
        fill_id=fill.fill_id,
        order_event_id="event:service:close:order",
        position_event_id="event:service:close:position",
        journal_entry_ids=(
            "journal:service:close:order",
            "journal:service:close:position",
        ),
        correlation_id="correlation:service:1",
        causation_id="causation:service:1",
        operation_at=OPERATION_AT,
    )
    repositories = FakeRepositories(
        command, close_order, position=position, decision=decision
    )
    uow = FakeUow(repositories)
    return SimpleNamespace(
        command=command,
        order=close_order,
        position=position,
        decision=decision,
        policy=policy,
        candle=candle,
        fill=fill,
        request=request,
        repositories=repositories,
        uow=uow,
    )
