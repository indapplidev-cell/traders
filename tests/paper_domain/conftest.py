from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.engine_execution.paper_idempotency import (
    command_idempotency_key,
    fill_idempotency_key,
    order_idempotency_key,
)
from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill
from app.engine_execution.paper_state_machine import (
    create_paper_order,
    fill_order,
    transition_order,
)
from app.engine_position.paper_state_machine import apply_entry_fill
from app.engine_safety import (
    ExecutionMode,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
    PaperSide,
)


NOW = datetime(2026, 7, 29, 6, 0, tzinfo=timezone.utc)


def make_command(**changes: object) -> PaperExecutionCommand:
    side = changes.get("side", PaperSide.LONG)
    short = side in {PaperSide.SHORT, "SHORT"}
    values: dict[str, object] = {
        "command_id": "command:1",
        "idempotency_key": command_idempotency_key(
            pipeline_run_id="run:1",
            analysis_result_id="analysis:1",
            setup_id="setup:1",
            strategy_decision_id="strategy:1",
            risk_decision_id="risk:1",
            symbol="BTCUSDT",
            side=side,
            closed_until_ms=1_000,
            configuration_fingerprint="config:v1",
        ),
        "mode": ExecutionMode.PAPER,
        "symbol": "BTCUSDT",
        "side": side,
        "order_type": PaperOrderType.MARKET_SIMULATED,
        "requested_quantity": Decimal("2"),
        "requested_notional": Decimal("200"),
        "entry_reference_price": Decimal("100"),
        "stop_price": Decimal("120") if short else Decimal("90"),
        "target_price": Decimal("90") if short else Decimal("120"),
        "strategy_decision_id": "strategy:1",
        "risk_decision_id": "risk:1",
        "setup_id": "setup:1",
        "pipeline_run_id": "run:1",
        "analysis_result_id": "analysis:1",
        "closed_until_ms": 1_000,
        "created_at": NOW,
        "valid_until_ms": 2_000,
        "configuration_fingerprint": "config:v1",
        "simulation_policy_id": "simulation:v1",
        "fee_policy_id": "fee:v1",
        "slippage_policy_id": "slippage:v1",
        "latency_policy_id": "latency:v1",
        "final_paper_approval": True,
        "input_health_status": PaperInputHealthStatus.CURRENT,
        "future_bars_used": False,
    }
    values.update(changes)
    return PaperExecutionCommand(**values)


def make_created_order(command: PaperExecutionCommand | None = None):
    command = command or make_command()
    return create_paper_order(
        command,
        order_id="order:1",
        idempotency_key=order_idempotency_key(command.command_id, "ENTRY"),
        occurred_at=NOW,
        event_id="event:order-created",
    ).order


def make_order(state: PaperOrderState):
    order = make_created_order()
    if state is PaperOrderState.CREATED:
        return order
    if state in {PaperOrderState.REJECTED, PaperOrderState.FAILED}:
        return transition_order(
            order,
            state,
            expected_version=order.version,
            occurred_at=NOW,
            event_id=f"event:{state.value.lower()}",
        ).order
    order = transition_order(
        order,
        PaperOrderState.VALIDATED,
        expected_version=order.version,
        occurred_at=NOW,
    ).order
    if state is PaperOrderState.VALIDATED:
        return order
    if state in {PaperOrderState.REJECTED, PaperOrderState.FAILED}:
        return transition_order(
            order,
            state,
            expected_version=order.version,
            occurred_at=NOW,
            event_id=f"event:{state.value.lower()}",
        ).order
    order = transition_order(
        order,
        PaperOrderState.OPEN,
        expected_version=order.version,
        occurred_at=NOW,
    ).order
    if state is PaperOrderState.OPEN:
        return order
    if state is PaperOrderState.FILLED:
        fill = make_fill(order_id=order.order_id)
        return fill_order(
            order,
            fill,
            expected_version=order.version,
            event_id="event:filled",
        ).order
    raise AssertionError(state)


def make_fill(**changes: object) -> PaperFill:
    values: dict[str, object] = {
        "fill_id": "fill:1",
        "order_id": "order:1",
        "idempotency_key": fill_idempotency_key("order:1", "ENTRY"),
        "symbol": "BTCUSDT",
        "side": PaperSide.LONG,
        "quantity": Decimal("2"),
        "price": Decimal("101"),
        "fee_amount": Decimal("0.2"),
        "fee_asset": "USDT",
        "filled_at": NOW,
        "source_closed_until_ms": 1_060,
        "simulation_policy_id": "simulation:v1",
        "slippage_policy_id": "slippage:v1",
        "fee_policy_id": "fee:v1",
        "latency_policy_id": "latency:v1",
        "future_bars_used": False,
    }
    values.update(changes)
    return PaperFill(**values)


def make_open_position(*, side: PaperSide = PaperSide.LONG):
    command = make_command(side=side)
    order = make_created_order(command)
    order = transition_order(
        order,
        PaperOrderState.VALIDATED,
        expected_version=0,
        occurred_at=NOW,
    ).order
    order = transition_order(
        order,
        PaperOrderState.OPEN,
        expected_version=1,
        occurred_at=NOW,
    ).order
    fill = make_fill(
        side=side,
        price=Decimal("100"),
        order_id=order.order_id,
        idempotency_key=fill_idempotency_key(order.order_id, "ENTRY"),
    )
    order = fill_order(order, fill, expected_version=2, event_id="event:entry-fill").order
    return apply_entry_fill(
        None,
        command,
        order,
        fill,
        position_id="position:1",
        event_id="event:position-open",
    ).position


@pytest.fixture
def command_factory():
    return make_command


@pytest.fixture
def fill_factory():
    return make_fill


@pytest.fixture
def order_factory():
    return make_order


@pytest.fixture
def position_factory():
    return make_open_position
