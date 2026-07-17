"""Potential market-setup discovery from completed analysis snapshots."""

from app.engine_setup.setup_candidate import SetupCandidate, setup_candidate_id
from app.engine_setup.setup_context import SetupContext
from app.engine_setup.setup_detector import SetupDetector
from app.engine_setup.setup_diagnostics import SetupDiagnostics, SetupSemanticBucket
from app.engine_setup.setup_invalidation import InvalidationReason
from app.engine_setup.setup_runner import SetupRunner
from app.engine_setup.setup_status import (
    ConfirmationState,
    DirectionHint,
    SetupQuality,
    SetupStatus,
)
from app.engine_setup.setup_store import SetupStore
from app.engine_setup.setup_type import SetupType
from app.engine_setup.setup_quality_diagnostics import (
    SetupQualityDiagnostics, calculate_setup_quality, diagnose_setup_quality, quality_from_score,
)

__all__ = [
    "ConfirmationState",
    "DirectionHint",
    "InvalidationReason",
    "SetupCandidate",
    "SetupContext",
    "SetupDetector",
    "SetupDiagnostics",
    "SetupSemanticBucket",
    "SetupQuality",
    "SetupRunner",
    "SetupStatus",
    "SetupStore",
    "SetupType",
    "SetupQualityDiagnostics",
    "calculate_setup_quality",
    "diagnose_setup_quality",
    "quality_from_score",
    "setup_candidate_id",
]
