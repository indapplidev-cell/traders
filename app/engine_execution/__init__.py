"""Safe, deterministic execution-intent layer for PAPER and DRY_RUN."""

from app.engine_execution.builder import ExecutionIntentBuilder, build_execution_intent
from app.engine_execution.approval_policy import ApprovalScope
from app.engine_execution.enums import (
    ExecutionAcknowledgementStatus,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionOrderType,
    ExecutionReasonCode,
    ExecutionSide,
)
from app.engine_execution.gateway import (
    DisabledLiveExecutionGateway,
    DryRunExecutionGateway,
    ExecutionGateway,
    PaperExecutionGateway,
)
from app.engine_execution.idempotency import InMemoryIdempotencyRegistry, build_idempotency_key
from app.engine_execution.models import ExecutionAcknowledgement, ExecutionIntent
from app.engine_execution.paper_idempotency import (
    PAPER_IDEMPOTENCY_VERSION,
    command_idempotency_key,
    exit_decision_idempotency_key,
    fill_idempotency_key,
    journal_event_idempotency_key,
    order_idempotency_key,
    position_application_key,
)
from app.engine_execution.paper_models import PaperExecutionCommand, PaperFill, PaperOrder
from app.engine_execution.paper_state_machine import (
    PaperOrderTransition,
    command_created_event,
    create_paper_order,
    fill_order,
    transition_order,
)
from app.engine_execution.serialization import canonical_json, execution_schema_version

__all__ = [
    "ApprovalScope", "DisabledLiveExecutionGateway", "DryRunExecutionGateway",
    "ExecutionAcknowledgement", "ExecutionAcknowledgementStatus", "ExecutionGateway",
    "ExecutionIntent", "ExecutionIntentBuilder", "ExecutionIntentStatus", "ExecutionMode",
    "ExecutionOrderType", "ExecutionReasonCode", "ExecutionSide",
    "InMemoryIdempotencyRegistry", "PaperExecutionGateway", "build_execution_intent",
    "build_idempotency_key", "canonical_json", "execution_schema_version",
    "PAPER_IDEMPOTENCY_VERSION", "PaperExecutionCommand", "PaperFill", "PaperOrder",
    "PaperOrderTransition", "command_created_event", "command_idempotency_key",
    "create_paper_order", "exit_decision_idempotency_key", "fill_idempotency_key",
    "fill_order", "journal_event_idempotency_key", "order_idempotency_key",
    "position_application_key", "transition_order",
]
"""Order-execution layer skeleton; no exchange calls are implemented."""
