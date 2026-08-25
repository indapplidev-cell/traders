"""Semantic diagnostics for setup discovery decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.engine_setup.setup_status import SetupStatus


class SetupSemanticBucket(StrEnum):
    CANDIDATE_STRUCTURE = "CANDIDATE_STRUCTURE"
    PRE_SETUP_WAITING_CONFIRMATION = "PRE_SETUP_WAITING_CONFIRMATION"
    INVALIDATED_STRUCTURE = "INVALIDATED_STRUCTURE"
    NO_STRUCTURAL_SETUP = "NO_STRUCTURAL_SETUP"
    ERROR_BUCKET = "ERROR_BUCKET"


_STATUS_BY_BUCKET = {
    SetupSemanticBucket.CANDIDATE_STRUCTURE.value: SetupStatus.SETUP_CANDIDATE.value,
    SetupSemanticBucket.PRE_SETUP_WAITING_CONFIRMATION.value: SetupStatus.WAIT_FOR_CONFIRMATION.value,
    SetupSemanticBucket.INVALIDATED_STRUCTURE.value: SetupStatus.SETUP_INVALID.value,
    SetupSemanticBucket.NO_STRUCTURAL_SETUP.value: SetupStatus.NO_SETUP.value,
    SetupSemanticBucket.ERROR_BUCKET.value: SetupStatus.ERROR.value,
}


def status_for_semantic_bucket(bucket: str) -> str:
    return _STATUS_BY_BUCKET[SetupSemanticBucket(bucket).value]


@dataclass(frozen=True, slots=True)
class SetupDiagnostics:
    has_structural_trigger: bool = False
    has_directional_context: bool = False
    has_level_context: bool = False
    has_confirmation_requirement: bool = False
    has_invalidation_context: bool = False
    is_choppy_noise: bool = False
    is_late_entry: bool = False
    is_actionable_setup_candidate: bool = False
    semantic_bucket: str = SetupSemanticBucket.NO_STRUCTURAL_SETUP.value
    diagnostic_reasons: list[str] = field(default_factory=list)
    distance_to_setup_condition: int | None = None
    missing_setup_conditions: list[str] = field(default_factory=list)
    breakout_strength: float | str | None = None
    pullback_quality: str | None = None
    liquidity_presence: bool | None = None
    volatility_suitability: str | None = None

    def __post_init__(self) -> None:
        bucket = SetupSemanticBucket(self.semantic_bucket).value
        object.__setattr__(self, "semantic_bucket", bucket)
        if bucket == SetupSemanticBucket.CANDIDATE_STRUCTURE.value:
            if not self.has_structural_trigger or not self.is_actionable_setup_candidate:
                raise ValueError("candidate diagnostics require an actionable structural trigger")
        if bucket == SetupSemanticBucket.PRE_SETUP_WAITING_CONFIRMATION.value:
            if not self.has_structural_trigger or not self.has_confirmation_requirement:
                raise ValueError("waiting diagnostics require a trigger and confirmation requirement")
        if bucket == SetupSemanticBucket.INVALIDATED_STRUCTURE.value and not self.has_invalidation_context:
            raise ValueError("invalidated diagnostics require invalidation context")
