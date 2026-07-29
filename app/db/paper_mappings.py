"""Pure PAPER domain-to-ORM value mappings.

The helpers deliberately accept records or plain mappings and never access a
session, generate identities, read a clock, retry, or commit.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_exit.paper_exit import PaperExitDecision
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_position.paper_models import PaperPosition
from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperEventType,
    PaperExitCause,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
)


def _read(source: object, name: str) -> Any:
    if isinstance(source, Mapping):
        return source[name]
    return getattr(source, name)


def paper_command_to_orm_values(command: PaperExecutionCommand) -> dict[str, object]:
    return {
        "command_id": command.command_id,
        "idempotency_key": command.idempotency_key,
        "mode": command.mode.value,
        "symbol": command.symbol,
        "side": command.side.value,
        "order_type": command.order_type.value,
        "requested_quantity": command.requested_quantity,
        "requested_notional": command.requested_notional,
        "entry_reference_price": command.entry_reference_price,
        "stop_price": command.stop_price,
        "target_price": command.target_price,
        "strategy_decision_id": command.strategy_decision_id,
        "risk_decision_id": command.risk_decision_id,
        "setup_id": command.setup_id,
        "pipeline_run_id": command.pipeline_run_id,
        "analysis_result_id": command.analysis_result_id,
        "closed_until_ms": command.closed_until_ms,
        "created_at": command.created_at,
        "valid_until_ms": command.valid_until_ms,
        "configuration_fingerprint": command.configuration_fingerprint,
        "simulation_policy_id": command.simulation_policy_id,
        "fee_policy_id": command.fee_policy_id,
        "slippage_policy_id": command.slippage_policy_id,
        "latency_policy_id": command.latency_policy_id,
        "final_paper_approval": command.final_paper_approval,
        "input_health_status": command.input_health_status.value,
        "future_bars_used": command.future_bars_used,
        "processing_status": "PENDING",
    }


def orm_values_to_paper_command(source: object) -> PaperExecutionCommand:
    return PaperExecutionCommand(
        command_id=_read(source, "command_id"),
        idempotency_key=_read(source, "idempotency_key"),
        mode=ExecutionMode(_read(source, "mode")),
        symbol=_read(source, "symbol"),
        side=PaperSide(_read(source, "side")),
        order_type=PaperOrderType(_read(source, "order_type")),
        requested_quantity=_read(source, "requested_quantity"),
        requested_notional=_read(source, "requested_notional"),
        entry_reference_price=_read(source, "entry_reference_price"),
        stop_price=_read(source, "stop_price"),
        target_price=_read(source, "target_price"),
        strategy_decision_id=_read(source, "strategy_decision_id"),
        risk_decision_id=_read(source, "risk_decision_id"),
        setup_id=_read(source, "setup_id"),
        pipeline_run_id=_read(source, "pipeline_run_id"),
        analysis_result_id=_read(source, "analysis_result_id"),
        closed_until_ms=_read(source, "closed_until_ms"),
        created_at=_read(source, "created_at"),
        valid_until_ms=_read(source, "valid_until_ms"),
        configuration_fingerprint=_read(source, "configuration_fingerprint"),
        simulation_policy_id=_read(source, "simulation_policy_id"),
        fee_policy_id=_read(source, "fee_policy_id"),
        slippage_policy_id=_read(source, "slippage_policy_id"),
        latency_policy_id=_read(source, "latency_policy_id"),
        final_paper_approval=_read(source, "final_paper_approval"),
        input_health_status=PaperInputHealthStatus(_read(source, "input_health_status")),
        future_bars_used=_read(source, "future_bars_used"),
    )


def paper_order_to_orm_values(
    order: PaperOrder,
    *,
    order_role: str,
    mode: ExecutionMode = ExecutionMode.PAPER,
) -> dict[str, object]:
    return {
        "order_id": order.order_id,
        "command_id": order.command_id,
        "idempotency_key": order.idempotency_key,
        "order_role": order_role,
        "mode": mode.value,
        "symbol": order.symbol,
        "side": order.side.value,
        "order_type": order.order_type.value,
        "state": order.state.value,
        "requested_quantity": order.requested_quantity,
        "filled_quantity": order.filled_quantity,
        "average_fill_price": order.average_fill_price,
        "total_fees": order.total_fees,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "version": order.version,
        "reason_code": order.reason_code.value,
        "applied_fill_id": order.applied_fill_id,
    }


def orm_values_to_paper_order(source: object) -> PaperOrder:
    return PaperOrder(
        order_id=_read(source, "order_id"),
        command_id=_read(source, "command_id"),
        idempotency_key=_read(source, "idempotency_key"),
        symbol=_read(source, "symbol"),
        side=PaperSide(_read(source, "side")),
        order_type=PaperOrderType(_read(source, "order_type")),
        state=PaperOrderState(_read(source, "state")),
        requested_quantity=_read(source, "requested_quantity"),
        filled_quantity=_read(source, "filled_quantity"),
        average_fill_price=_read(source, "average_fill_price"),
        total_fees=_read(source, "total_fees"),
        created_at=_read(source, "created_at"),
        updated_at=_read(source, "updated_at"),
        version=_read(source, "version"),
        reason_code=PaperReasonCode(_read(source, "reason_code")),
        applied_fill_id=_read(source, "applied_fill_id"),
    )


def paper_fill_to_orm_values(fill: PaperFill, *, fill_role: str) -> dict[str, object]:
    return {
        "fill_id": fill.fill_id,
        "order_id": fill.order_id,
        "idempotency_key": fill.idempotency_key,
        "fill_role": fill_role,
        "symbol": fill.symbol,
        "side": fill.side.value,
        "quantity": fill.quantity,
        "price": fill.price,
        "fee_amount": fill.fee_amount,
        "fee_asset": fill.fee_asset,
        "filled_at": fill.filled_at,
        "source_closed_until_ms": fill.source_closed_until_ms,
        "simulation_policy_id": fill.simulation_policy_id,
        "slippage_policy_id": fill.slippage_policy_id,
        "fee_policy_id": fill.fee_policy_id,
        "latency_policy_id": fill.latency_policy_id,
        "future_bars_used": fill.future_bars_used,
    }


def orm_values_to_paper_fill(source: object) -> PaperFill:
    return PaperFill(
        fill_id=_read(source, "fill_id"),
        order_id=_read(source, "order_id"),
        idempotency_key=_read(source, "idempotency_key"),
        symbol=_read(source, "symbol"),
        side=PaperSide(_read(source, "side")),
        quantity=_read(source, "quantity"),
        price=_read(source, "price"),
        fee_amount=_read(source, "fee_amount"),
        fee_asset=_read(source, "fee_asset"),
        filled_at=_read(source, "filled_at"),
        source_closed_until_ms=_read(source, "source_closed_until_ms"),
        simulation_policy_id=_read(source, "simulation_policy_id"),
        slippage_policy_id=_read(source, "slippage_policy_id"),
        fee_policy_id=_read(source, "fee_policy_id"),
        latency_policy_id=_read(source, "latency_policy_id"),
        future_bars_used=_read(source, "future_bars_used"),
    )


def paper_position_to_orm_values(position: PaperPosition) -> dict[str, object]:
    updated_at = position.closed_at or position.opened_at
    return {
        "position_id": position.position_id,
        "mode": position.mode.value,
        "symbol": position.symbol,
        "side": position.side.value,
        "state": position.state.value,
        "entry_order_id": position.entry_order_id,
        "entry_fill_id": position.entry_fill_id,
        "entry_quantity": position.entry_quantity,
        "remaining_quantity": position.remaining_quantity,
        "average_entry_price": position.average_entry_price,
        "average_exit_price": position.average_exit_price,
        "entry_fees": position.entry_fees,
        "exit_fees": position.exit_fees,
        "realized_pnl": position.realized_pnl,
        "unrealized_pnl": position.unrealized_pnl,
        "stop_price": position.stop_price,
        "target_price": position.target_price,
        "opened_at": position.opened_at,
        "closed_at": position.closed_at,
        "last_mark_price": position.last_mark_price,
        "last_mark_closed_until_ms": position.last_mark_closed_until_ms,
        "version": position.version,
        "reason_code": position.reason_code.value,
        "exit_fill_id": position.exit_fill_id,
        "created_at": position.opened_at,
        "updated_at": updated_at,
    }


def orm_values_to_paper_position(source: object) -> PaperPosition:
    return PaperPosition(
        position_id=_read(source, "position_id"),
        mode=ExecutionMode(_read(source, "mode")),
        symbol=_read(source, "symbol"),
        side=PaperSide(_read(source, "side")),
        state=PaperPositionState(_read(source, "state")),
        entry_order_id=_read(source, "entry_order_id"),
        entry_fill_id=_read(source, "entry_fill_id"),
        entry_quantity=_read(source, "entry_quantity"),
        remaining_quantity=_read(source, "remaining_quantity"),
        average_entry_price=_read(source, "average_entry_price"),
        average_exit_price=_read(source, "average_exit_price"),
        entry_fees=_read(source, "entry_fees"),
        exit_fees=_read(source, "exit_fees"),
        realized_pnl=_read(source, "realized_pnl"),
        unrealized_pnl=_read(source, "unrealized_pnl"),
        stop_price=_read(source, "stop_price"),
        target_price=_read(source, "target_price"),
        opened_at=_read(source, "opened_at"),
        closed_at=_read(source, "closed_at"),
        last_mark_price=_read(source, "last_mark_price"),
        last_mark_closed_until_ms=_read(source, "last_mark_closed_until_ms"),
        version=_read(source, "version"),
        reason_code=PaperReasonCode(_read(source, "reason_code")),
        exit_fill_id=_read(source, "exit_fill_id"),
    )


def paper_exit_decision_to_orm_values(decision: PaperExitDecision) -> dict[str, object]:
    return {
        "exit_decision_id": decision.exit_decision_id,
        "idempotency_key": decision.idempotency_key,
        "position_id": decision.position_id,
        "position_version": decision.position_version,
        "cause": decision.cause.value,
        "decision_price": decision.decision_price,
        "requested_close_quantity": decision.requested_close_quantity,
        "source_closed_until_ms": decision.source_closed_until_ms,
        "decided_at": decision.decided_at,
        "reason_code": decision.reason_code.value,
    }


def orm_values_to_paper_exit_decision(source: object) -> PaperExitDecision:
    return PaperExitDecision(
        exit_decision_id=_read(source, "exit_decision_id"),
        idempotency_key=_read(source, "idempotency_key"),
        position_id=_read(source, "position_id"),
        position_version=_read(source, "position_version"),
        cause=PaperExitCause(_read(source, "cause")),
        decision_price=_read(source, "decision_price"),
        requested_close_quantity=_read(source, "requested_close_quantity"),
        source_closed_until_ms=_read(source, "source_closed_until_ms"),
        decided_at=_read(source, "decided_at"),
        reason_code=PaperReasonCode(_read(source, "reason_code")),
    )


def paper_event_to_journal_values(
    event: PaperDomainEvent,
    *,
    command_id: str | None = None,
    order_id: str | None = None,
    fill_id: str | None = None,
    position_id: str | None = None,
    exit_decision_id: str | None = None,
) -> dict[str, object]:
    return {
        "journal_entry_id": event.event_id,
        "event_type": event.event_type.value,
        "occurred_at": event.occurred_at,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "aggregate_version": event.aggregate_version,
        "correlation_id": event.correlation_id,
        "causation_id": event.causation_id,
        "idempotency_key": event.event_id,
        "reason_code": event.reason_code.value,
        "command_id": command_id,
        "order_id": order_id,
        "fill_id": fill_id,
        "position_id": position_id,
        "exit_decision_id": exit_decision_id,
    }


def orm_values_to_paper_event(source: object) -> PaperDomainEvent:
    return PaperDomainEvent(
        event_id=_read(source, "journal_entry_id"),
        event_type=PaperEventType(_read(source, "event_type")),
        occurred_at=_read(source, "occurred_at"),
        aggregate_type=_read(source, "aggregate_type"),
        aggregate_id=_read(source, "aggregate_id"),
        correlation_id=_read(source, "correlation_id"),
        causation_id=_read(source, "causation_id"),
        reason_code=PaperReasonCode(_read(source, "reason_code")),
        aggregate_version=_read(source, "aggregate_version"),
    )
