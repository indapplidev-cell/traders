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
from app.engine_execution.serialization import canonical_json, execution_schema_version

__all__ = [
    "ApprovalScope", "DisabledLiveExecutionGateway", "DryRunExecutionGateway",
    "ExecutionAcknowledgement", "ExecutionAcknowledgementStatus", "ExecutionGateway",
    "ExecutionIntent", "ExecutionIntentBuilder", "ExecutionIntentStatus", "ExecutionMode",
    "ExecutionOrderType", "ExecutionReasonCode", "ExecutionSide",
    "InMemoryIdempotencyRegistry", "PaperExecutionGateway", "build_execution_intent",
    "build_idempotency_key", "canonical_json", "execution_schema_version",
]
"""Order-execution layer skeleton; no exchange calls are implemented."""
