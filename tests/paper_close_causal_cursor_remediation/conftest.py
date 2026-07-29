from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.engine_execution.paper_idempotency import (
    command_idempotency_key,
    order_idempotency_key,
)
from app.engine_execution.paper_models import PaperExecutionCommand, PaperOrder
from app.engine_execution.paper_state_machine import fill_order
from app.engine_exit.paper_exit import PaperExitDecision
from app.engine_paper.exit_evaluation_cursor import (
    PAPER_EXIT_CURSOR_CONTRACT_VERSION,
    PaperExitCursorAdvance,
    PaperExitEvaluationCursor,
    paper_exit_cursor_window_identity,
    paper_exit_evaluation_cursor_id,
)
from app.engine_paper.fill_causal_boundary import (
    resolve_paper_fill_causal_boundary,
)
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
from app.engine_position.paper_state_machine import apply_entry_fill
from app.engine_safety import (
    ExecutionMode,
    PaperExitCause,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
    PaperReasonCode,
    PaperSide,
)

from tests.paper_repository.conftest import (  # noqa: F401
    paper_session_factory,
    repository_postgres_engine,
)


T0 = 1_785_340_800_000
T1 = T0 + 60_000
T10 = T0 + 600_000
T11 = T10 + 60_000
NOW = datetime.fromtimestamp(T0 / 1000, tz=timezone.utc)
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


def make_command(**changes):
    values = {
        "command_id": "command:remediation:1",
        "idempotency_key": command_idempotency_key(
            pipeline_run_id="run:remediation:1",
            analysis_result_id="analysis:remediation:1",
            setup_id="setup:remediation:1",
            strategy_decision_id="strategy:remediation:1",
            risk_decision_id="risk:remediation:1",
            symbol="BTCUSDT",
            side=PaperSide.LONG,
            closed_until_ms=T0,
            configuration_fingerprint="config:remediation:v1",
        ),
        "mode": ExecutionMode.PAPER,
        "symbol": "BTCUSDT",
        "side": PaperSide.LONG,
        "order_type": PaperOrderType.MARKET_SIMULATED,
        "requested_quantity": Decimal("2"),
        "requested_notional": Decimal("200"),
        "entry_reference_price": Decimal("100"),
        "stop_price": Decimal("90"),
        "target_price": Decimal("110"),
        "strategy_decision_id": "strategy:remediation:1",
        "risk_decision_id": "risk:remediation:1",
        "setup_id": "setup:remediation:1",
        "pipeline_run_id": "run:remediation:1",
        "analysis_result_id": "analysis:remediation:1",
        "closed_until_ms": T0,
        "created_at": NOW,
        "valid_until_ms": T1,
        "configuration_fingerprint": "config:remediation:v1",
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
        "order_id": f"order:remediation:{suffix}",
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


def make_candle(open_ms=T0, **changes):
    values = {
        "symbol": "BTCUSDT",
        "timeframe": "1m",
        "open_time_ms": open_ms,
        "close_boundary_ms": open_ms + 60_000,
        "open_price": Decimal("100"),
        "high_price": Decimal("105"),
        "low_price": Decimal("95"),
        "close_price": Decimal("101"),
        "is_closed": True,
        "observed_closed_until_ms": open_ms + 60_000,
    }
    values.update(changes)
    return PaperFillCandle(**values)


@pytest.fixture
def causal_graph():
    policy = make_policy()
    command = make_command()
    entry_order = make_order(command)
    entry_boundary = resolve_paper_fill_causal_boundary(
        fill_role=PaperFillRole.ENTRY,
        command=command,
        order=entry_order,
        simulation_policy=policy,
        correlation_id="correlation:remediation:1",
        causation_id="causation:remediation:1",
    ).boundary
    entry_candle = make_candle(T0)
    entry_fill = simulate_paper_fill(
        FillSimulationRequest(
            command=command,
            order=entry_order,
            fill_role=PaperFillRole.ENTRY,
            causal_boundary=entry_boundary,
            quote_asset="USDT",
            simulation_policy=policy,
            candidate_candles=(entry_candle,),
            market_snapshot_closed_until_ms=T1,
            correlation_id="correlation:remediation:1",
            causation_id="causation:remediation:1",
        )
    ).fill
    filled_entry_order = fill_order(
        entry_order,
        entry_fill,
        expected_version=2,
        event_id="event:entry:filled",
    ).order
    position = apply_entry_fill(
        None,
        command,
        filled_entry_order,
        entry_fill,
        position_id="position:remediation:1",
        event_id="event:position:opened",
    ).position
    decision = PaperExitDecision(
        exit_decision_id="exit:remediation:1",
        idempotency_key="exit:key:remediation:1",
        position_id=position.position_id,
        position_version=position.version,
        cause=PaperExitCause.STOP_LOSS,
        decision_price=Decimal("90"),
        requested_close_quantity=position.remaining_quantity,
        source_closed_until_ms=T10,
        decided_at=NOW + timedelta(minutes=10),
        reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
    )
    close_order = make_order(command, role="EXIT", suffix="close")
    return {
        "policy": policy,
        "command": command,
        "entry_order": entry_order,
        "filled_entry_order": filled_entry_order,
        "entry_fill": entry_fill,
        "position": position,
        "decision": decision,
        "close_order": close_order,
    }


def make_cursor(graph, **changes):
    position = graph["position"]
    opened_boundary = graph["entry_fill"].source_closed_until_ms
    policy_id = "exit-evaluation:stop-target:v1"
    values = {
        "cursor_id": paper_exit_evaluation_cursor_id(
            position_id=position.position_id,
            mode=position.mode,
            symbol=position.symbol,
            position_opened_closed_until_ms=opened_boundary,
            evaluation_policy_id=policy_id,
        ),
        "contract_version": PAPER_EXIT_CURSOR_CONTRACT_VERSION,
        "position_id": position.position_id,
        "mode": position.mode,
        "symbol": position.symbol,
        "last_evaluated_closed_until_ms": opened_boundary,
        "position_opened_closed_until_ms": opened_boundary,
        "evaluation_policy_id": policy_id,
        "version": 0,
        "created_at": position.opened_at,
        "updated_at": position.opened_at,
        "correlation_id": "correlation:cursor:1",
        "causation_id": position.entry_fill_id,
    }
    values.update(changes)
    return PaperExitEvaluationCursor(**values)


def make_advance(cursor, candle_count=1, **changes):
    boundaries = tuple(
        cursor.last_evaluated_closed_until_ms + 60_000 * index
        for index in range(1, candle_count + 1)
    )
    values = {
        "position_id": cursor.position_id,
        "expected_version": cursor.version,
        "from_closed_until_ms": cursor.last_evaluated_closed_until_ms,
        "to_closed_until_ms": boundaries[-1],
        "evaluation_policy_id": cursor.evaluation_policy_id,
        "evaluated_close_boundaries_ms": boundaries,
        "window_identity": paper_exit_cursor_window_identity(
            position_id=cursor.position_id,
            expected_version=cursor.version,
            from_boundary_ms=cursor.last_evaluated_closed_until_ms,
            to_boundary_ms=boundaries[-1],
            evaluation_policy_id=cursor.evaluation_policy_id,
            evaluated_close_boundaries_ms=boundaries,
        ),
        "advanced_at": cursor.updated_at + timedelta(minutes=candle_count),
        "correlation_id": "correlation:cursor:1",
        "causation_id": "causation:cursor:advance",
    }
    values["idempotency_key"] = values["window_identity"]
    values.update(changes)
    return PaperExitCursorAdvance(**values)


@pytest.fixture
def cursor_factory(causal_graph):
    return lambda **changes: make_cursor(causal_graph, **changes)


@pytest.fixture
def advance_factory():
    return make_advance
