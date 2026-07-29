from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.engine_execution.paper_idempotency import (
    command_idempotency_key,
    order_idempotency_key,
)
from app.engine_execution.paper_models import PaperExecutionCommand, PaperOrder
from app.engine_paper.fill_policy import (
    PaperFillPriceSource,
    PaperFillSimulationPolicy,
    PaperIntrabarConflictPolicy,
)
from app.engine_paper.fill_causal_boundary import (
    PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
    PaperFillCausalBoundary,
    PaperFillSourceEntityType,
)
from app.engine_paper.fill_simulator import (
    FillSimulationRequest,
    PaperFillCandle,
    PaperFillRole,
)
from app.engine_safety import (
    ExecutionMode,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
    PaperReasonCode,
    PaperSide,
)


NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
COMMAND_BOUNDARY_MS = 3_600_000
EXPECTED_CLOSE_BOUNDARY_MS = 3_660_000
STORAGE_QUANTUM = Decimal("0.000000000000000001")


def make_policy(**changes: object) -> PaperFillSimulationPolicy:
    values: dict[str, object] = {
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
        "intrabar_conflict_policy": (
            PaperIntrabarConflictPolicy.STOP_FIRST_CONSERVATIVE
        ),
        "price_quantum": STORAGE_QUANTUM,
        "fee_quantum": STORAGE_QUANTUM,
        "contract_version": "PAPER_FILL_SIMULATION_V1",
    }
    values.update(changes)
    return PaperFillSimulationPolicy(**values)  # type: ignore[arg-type]


def make_command(
    *,
    side: PaperSide = PaperSide.LONG,
    quantity: Decimal = Decimal("2"),
    **changes: object,
) -> PaperExecutionCommand:
    short = side is PaperSide.SHORT
    values: dict[str, object] = {
        "command_id": "command:fill:1",
        "idempotency_key": command_idempotency_key(
            pipeline_run_id="run:fill:1",
            analysis_result_id="analysis:fill:1",
            setup_id="setup:fill:1",
            strategy_decision_id="strategy:fill:1",
            risk_decision_id="risk:fill:1",
            symbol="BTCUSDT",
            side=side,
            closed_until_ms=COMMAND_BOUNDARY_MS,
            configuration_fingerprint="config:fill:v1",
        ),
        "mode": ExecutionMode.PAPER,
        "symbol": "BTCUSDT",
        "side": side,
        "order_type": PaperOrderType.MARKET_SIMULATED,
        "requested_quantity": quantity,
        "requested_notional": quantity * Decimal("100"),
        "entry_reference_price": Decimal("100"),
        "stop_price": Decimal("110") if short else Decimal("90"),
        "target_price": Decimal("90") if short else Decimal("110"),
        "strategy_decision_id": "strategy:fill:1",
        "risk_decision_id": "risk:fill:1",
        "setup_id": "setup:fill:1",
        "pipeline_run_id": "run:fill:1",
        "analysis_result_id": "analysis:fill:1",
        "closed_until_ms": COMMAND_BOUNDARY_MS,
        "created_at": NOW,
        "valid_until_ms": EXPECTED_CLOSE_BOUNDARY_MS,
        "configuration_fingerprint": "config:fill:v1",
        "simulation_policy_id": "simulation:foundation:v1",
        "fee_policy_id": "fee:quote:10bps:v1",
        "slippage_policy_id": "slippage:adverse:2bps:v1",
        "latency_policy_id": "latency:one-closed-1m:v1",
        "final_paper_approval": True,
        "input_health_status": PaperInputHealthStatus.CURRENT,
        "future_bars_used": False,
    }
    values.update(changes)
    return PaperExecutionCommand(**values)  # type: ignore[arg-type]


def make_order(
    command: PaperExecutionCommand | None = None,
    **changes: object,
) -> PaperOrder:
    command = command or make_command()
    values: dict[str, object] = {
        "order_id": "order:fill:1",
        "command_id": command.command_id,
        "idempotency_key": order_idempotency_key(command.command_id, "ENTRY"),
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
    return PaperOrder(**values)  # type: ignore[arg-type]


def make_candle(**changes: object) -> PaperFillCandle:
    values: dict[str, object] = {
        "symbol": "BTCUSDT",
        "timeframe": "1m",
        "open_time_ms": COMMAND_BOUNDARY_MS,
        "close_boundary_ms": EXPECTED_CLOSE_BOUNDARY_MS,
        "open_price": Decimal("100"),
        "high_price": Decimal("105"),
        "low_price": Decimal("95"),
        "close_price": Decimal("101"),
        "is_closed": True,
        "observed_closed_until_ms": EXPECTED_CLOSE_BOUNDARY_MS,
    }
    values.update(changes)
    return PaperFillCandle(**values)  # type: ignore[arg-type]


def make_request(
    *,
    command: PaperExecutionCommand | None = None,
    order: PaperOrder | None = None,
    policy: PaperFillSimulationPolicy | None = None,
    candles: tuple[PaperFillCandle, ...] | None = None,
    role: PaperFillRole = PaperFillRole.ENTRY,
    **changes: object,
) -> FillSimulationRequest:
    role = PaperFillRole(role)
    command = command or make_command()
    order = order or make_order(
        command,
        idempotency_key=order_idempotency_key(
            command.command_id,
            role.persistence_role,
        ),
    )
    selected_policy = policy or make_policy()
    causal_boundary = PaperFillCausalBoundary(
        contract_version=PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
        fill_role=role,
        source_entity_type=(
            PaperFillSourceEntityType.PAPER_EXECUTION_COMMAND
            if role is PaperFillRole.ENTRY
            else PaperFillSourceEntityType.PAPER_EXIT_DECISION
        ),
        source_entity_id=(
            command.command_id if role is PaperFillRole.ENTRY else "exit:fill:1"
        ),
        source_closed_until_ms=command.closed_until_ms,
        order_id=order.order_id,
        symbol=command.symbol,
        timeframe=selected_policy.timeframe,
        latency_candles=selected_policy.latency_candles,
        simulation_policy_id=selected_policy.simulation_policy_id,
        slippage_policy_id=selected_policy.slippage_policy_id,
        fee_policy_id=selected_policy.fee_policy_id,
        latency_policy_id=selected_policy.latency_policy_id,
        correlation_id="correlation:fill:1",
        causation_id="causation:fill:1",
    )
    values: dict[str, object] = {
        "command": command,
        "order": order,
        "fill_role": role,
        "causal_boundary": causal_boundary,
        "quote_asset": "USDT",
        "simulation_policy": selected_policy,
        "candidate_candles": candles if candles is not None else (make_candle(),),
        "market_snapshot_closed_until_ms": EXPECTED_CLOSE_BOUNDARY_MS,
        "correlation_id": "correlation:fill:1",
        "causation_id": "causation:fill:1",
    }
    values.update(changes)
    return FillSimulationRequest(**values)  # type: ignore[arg-type]


@pytest.fixture
def policy_factory():
    return make_policy


@pytest.fixture
def command_factory():
    return make_command


@pytest.fixture
def order_factory():
    return make_order


@pytest.fixture
def candle_factory():
    return make_candle


@pytest.fixture
def request_factory():
    return make_request
