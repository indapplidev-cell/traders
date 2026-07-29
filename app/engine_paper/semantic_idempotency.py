"""Explicit public causal tuples used for semantic replay verification."""

from __future__ import annotations

from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_exit.paper_exit import PaperExitDecision
from app.engine_journal.paper_events import PaperDomainEvent


COMMAND_FIELDS = (
    "command_id", "idempotency_key", "mode", "symbol", "side", "order_type",
    "requested_quantity", "requested_notional", "entry_reference_price", "stop_price",
    "target_price", "strategy_decision_id", "risk_decision_id", "setup_id",
    "pipeline_run_id", "analysis_result_id", "closed_until_ms", "created_at",
    "valid_until_ms", "configuration_fingerprint", "simulation_policy_id",
    "fee_policy_id", "slippage_policy_id", "latency_policy_id",
    "final_paper_approval", "input_health_status", "future_bars_used",
)
ORDER_CAUSAL_FIELDS = (
    "order_id", "command_id", "idempotency_key", "symbol", "side", "order_type",
    "requested_quantity", "created_at",
)
FILL_FIELDS = (
    "fill_id", "order_id", "idempotency_key", "symbol", "side", "quantity",
    "price", "fee_amount", "fee_asset", "filled_at", "source_closed_until_ms",
    "simulation_policy_id", "slippage_policy_id", "fee_policy_id",
    "latency_policy_id", "future_bars_used",
)
EXIT_FIELDS = (
    "exit_decision_id", "idempotency_key", "position_id", "position_version",
    "cause", "decision_price", "requested_close_quantity", "source_closed_until_ms",
    "decided_at", "reason_code",
)
JOURNAL_FIELDS = (
    "event_id", "event_type", "occurred_at", "aggregate_type", "aggregate_id",
    "correlation_id", "causation_id", "reason_code", "aggregate_version",
)


def _tuple(value: object, fields: tuple[str, ...]) -> tuple[object, ...]:
    return tuple(getattr(value, name) for name in fields)


def command_semantic_tuple(value: PaperExecutionCommand) -> tuple[object, ...]:
    return _tuple(value, COMMAND_FIELDS)


def order_semantic_tuple(value: PaperOrder) -> tuple[object, ...]:
    return _tuple(value, ORDER_CAUSAL_FIELDS)


def fill_semantic_tuple(value: PaperFill) -> tuple[object, ...]:
    return _tuple(value, FILL_FIELDS)


def exit_semantic_tuple(value: PaperExitDecision) -> tuple[object, ...]:
    return _tuple(value, EXIT_FIELDS)


def journal_semantic_tuple(value: PaperDomainEvent) -> tuple[object, ...]:
    return _tuple(value, JOURNAL_FIELDS)
