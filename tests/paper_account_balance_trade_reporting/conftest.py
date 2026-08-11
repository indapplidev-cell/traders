from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_paper.accounting import (
    PaperAccountBaseline,
    PaperAccountIdentity,
    PaperClosedTradeFacts,
)
from app.engine_paper.fill_simulator import quote_fee_amount
from app.engine_position.paper_state_machine import apply_close_fill, apply_entry_fill, begin_closing
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
    PaperReasonCode,
    PaperSide,
)


UTC = timezone.utc


@pytest.fixture
def identity() -> PaperAccountIdentity:
    return PaperAccountIdentity("paper-primary", "session-001")


@pytest.fixture
def baseline(identity) -> PaperAccountBaseline:
    return PaperAccountBaseline(
        "baseline-001", identity, Decimal("100"), datetime(2026, 8, 11, tzinfo=UTC)
    )


def make_trade(
    index: int,
    *,
    side: PaperSide = PaperSide.LONG,
    entry_price: Decimal = Decimal("10"),
    exit_price: Decimal = Decimal("11"),
    quantity: Decimal = Decimal("2"),
    fee_bps: Decimal = Decimal("10"),
    close_offset_seconds: int | None = None,
) -> PaperClosedTradeFacts:
    opened = datetime(2026, 8, 11, tzinfo=UTC) + timedelta(seconds=index)
    closed = opened + timedelta(seconds=close_offset_seconds if close_offset_seconds is not None else 60)
    stop = entry_price - Decimal("1") if side is PaperSide.LONG else entry_price + Decimal("1")
    target = entry_price + Decimal("1") if side is PaperSide.LONG else entry_price - Decimal("1")
    command = PaperExecutionCommand(
        command_id=f"command-{index}",
        idempotency_key=f"command-key-{index}",
        mode=ExecutionMode.PAPER,
        symbol="BTCUSDT",
        side=side,
        order_type=PaperOrderType.MARKET_SIMULATED,
        requested_quantity=quantity,
        requested_notional=quantity * entry_price,
        entry_reference_price=entry_price,
        stop_price=stop,
        target_price=target,
        strategy_decision_id=f"strategy-{index}",
        risk_decision_id=f"risk-{index}",
        setup_id=f"setup-{index}",
        pipeline_run_id=f"pipeline-{index}",
        analysis_result_id=f"analysis-{index}",
        closed_until_ms=index * 60_000,
        created_at=opened,
        valid_until_ms=index * 60_000 + 300_000,
        configuration_fingerprint="cfg-1",
        simulation_policy_id="simulation-1",
        fee_policy_id="fee-1",
        slippage_policy_id="slippage-1",
        latency_policy_id="latency-1",
        final_paper_approval=True,
        input_health_status=PaperInputHealthStatus.HEALTHY,
        future_bars_used=False,
    )
    entry_fee = quote_fee_amount(entry_price, quantity, fee_bps, Decimal("0.000000000000000001"))
    entry_fill = PaperFill(
        fill_id=f"entry-fill-{index}", order_id=f"entry-order-{index}",
        idempotency_key=f"entry-fill-key-{index}", symbol="BTCUSDT", side=side,
        quantity=quantity, price=entry_price, fee_amount=entry_fee, fee_asset="USDT",
        filled_at=opened, source_closed_until_ms=index * 60_000,
        simulation_policy_id="simulation-1", slippage_policy_id="slippage-1",
        fee_policy_id="fee-1", latency_policy_id="latency-1",
    )
    entry_order = PaperOrder(
        order_id=entry_fill.order_id, command_id=command.command_id,
        idempotency_key=f"entry-order-key-{index}", symbol="BTCUSDT", side=side,
        order_type=PaperOrderType.MARKET_SIMULATED, state=PaperOrderState.FILLED,
        requested_quantity=quantity, filled_quantity=quantity,
        average_fill_price=entry_price, total_fees=entry_fee,
        created_at=opened, updated_at=opened, version=3,
        reason_code=PaperReasonCode.PAPER_ORDER_FILLED,
        applied_fill_id=entry_fill.fill_id,
    )
    opened_transition = apply_entry_fill(
        None, command, entry_order, entry_fill,
        position_id=f"position-{index}", event_id=f"position-open-event-{index}",
    )
    closing = begin_closing(
        opened_transition.position,
        expected_version=0,
        exit_decision_id=f"exit-decision-{index}",
        occurred_at=closed,
    )
    exit_fee = quote_fee_amount(exit_price, quantity, fee_bps, Decimal("0.000000000000000001"))
    exit_fill = replace(
        entry_fill,
        fill_id=f"exit-fill-{index}",
        order_id=f"exit-order-{index}",
        idempotency_key=f"exit-fill-key-{index}",
        price=exit_price,
        fee_amount=exit_fee,
        filled_at=closed,
        source_closed_until_ms=index * 60_000 + 60_000,
    )
    closed_transition = apply_close_fill(
        closing.position, exit_fill, expected_version=1,
        event_id=f"position-close-event-{index}",
    )
    return PaperClosedTradeFacts(
        closed_transition.position,
        entry_fill,
        exit_fill,
        "TAKE_PROFIT" if side is PaperSide.LONG else "STOP_LOSS",
        (*opened_transition.events, *closed_transition.events),
    )

