"""Pure safety contracts. No runtime configuration or transport is accessed."""

from app.engine_safety.paper_domain import (
    ExecutionMode,
    PaperDomainError,
    PaperEventType,
    PaperExitCause,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
    normalize_symbol,
    parse_execution_mode,
    require_paper_mode,
)

__all__ = [
    "ExecutionMode",
    "PaperDomainError",
    "PaperEventType",
    "PaperExitCause",
    "PaperInputHealthStatus",
    "PaperOrderState",
    "PaperOrderType",
    "PaperPositionState",
    "PaperReasonCode",
    "PaperSide",
    "normalize_symbol",
    "parse_execution_mode",
    "require_paper_mode",
]

from app.engine_safety.paper_production_control import (
    PaperProductionMutationSafetyGate,
    PaperProductionSafetyControl,
    ProductionPaperMutationComposition,
)

__all__ += [
    "PaperProductionMutationSafetyGate",
    "PaperProductionSafetyControl",
    "ProductionPaperMutationComposition",
]
