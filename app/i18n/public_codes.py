"""Registry of machine codes intentionally exposed in user-facing Readonly DTOs."""

from app.engine_risk.risk_status import RiskStatus
from app.engine_risk.risk_reason_codes import RiskReasonCode
from app.engine_safety.paper_domain import PaperExitCause, PaperOrderState, PaperPositionState, PaperSide
from app.engine_safety.paper_production_control import PersistentState
from app.engine_paper.paper_reason_codes import PaperReasonCode as PipelinePaperReasonCode
from app.engine_setup.setup_reason_codes import SetupReasonCode
from app.engine_setup.setup_status import SetupStatus
from app.engine_setup.setup_type import SetupType
from app.engine_strategy.strategy_reason_codes import StrategyReasonCode
from app.engine_strategy.strategy_status import StrategyStatus
from app.server_api.schemas.models import (
    AnalysisStatus, Direction, HealthState, IncidentStatus, PipelineStatus, Severity,
)

PUBLIC_ENUM_NAMESPACES = (
    ("market.data", (HealthState,)), ("setup.direction", (Direction,)),
    ("analysis.status", (AnalysisStatus,)), ("setup.status", (SetupStatus,)),
    ("incident.status", (IncidentStatus,)), ("incident.severity", (Severity,)),
    ("pipeline.status", (PipelineStatus,)), ("setup.scenario", (SetupType,)),
    ("strategy.status", (StrategyStatus,)), ("risk.decision", (RiskStatus,)),
    ("control.state", (PersistentState,)),
    ("paper.state", (PaperOrderState, PaperPositionState)), ("paper.side", (PaperSide,)),
    ("paper.exit", (PaperExitCause,)),
)

PUBLIC_LITERAL_CODES = {
    "control.canary": (
        "NOT_CONFIGURED", "DISABLED", "RESERVED", "ARMED", "ARMED_WAITING",
        "NO_ELIGIBLE_APPROVAL", "WAITING_FOR_ELIGIBLE_APPROVAL", "RUNNING",
        "POSITION_OPEN", "POSITION_CLOSING", "POSITION_CLOSED",
        "RECONCILIATION_PENDING", "COMPLETED", "STOPPED", "FAILED_SAFE",
    ),
}

# Full source registries consumed by trading-funnel-v1, plus bounded projection
# reasons produced by the funnel/materializer itself.
PUBLIC_REASON_ENUMS = (
    SetupReasonCode, StrategyReasonCode, RiskReasonCode, PipelinePaperReasonCode,
)
PUBLIC_REASON_CODES = frozenset(
    member.value for enum_type in PUBLIC_REASON_ENUMS for member in enum_type
) | frozenset({
    "PAPER_NO_PLAN_SOURCE_NO_DECISION",
    "PAPER_REJECT_SOURCE_REJECTED",
    "PAPER_REJECT_LOW_PLANNED_RR",
    "PAPER_INPUT_IDENTITY_INVALID",
    "APPROVAL_EXPIRED",
    "FINAL_APPROVAL_CREATED",
    "NOT_ELIGIBLE",
})
