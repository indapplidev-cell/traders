"""Causal quality diagnostics for setup-layer records.

The score describes evidence already present at the setup decision timestamp.  It
is deliberately independent from trade planning and from all future outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engine_setup.setup_diagnostics import SetupDiagnostics, SetupSemanticBucket
from app.engine_setup.setup_reason_codes import SetupReasonCode
from app.engine_setup.setup_status import ConfirmationState, DirectionHint, SetupQuality, SetupStatus
from app.engine_setup.setup_type import SetupType


QUALITY_ORDER = {"GOOD": 0, "ACCEPTABLE": 1, "WEAK": 2, "POOR": 3, "INVALID": 4, "UNKNOWN": 5}
HARD_INVALIDATIONS = {"FUTURE_BARS_REJECTED", "ANALYSIS_ERROR", "NOT_ENOUGH_DATA", "ENTRY_QUALITY_INVALID"}
CONFLICT_PENALTIES = {
    "LATE_CONFIRMATION_RISK": 12.0,
    "POST_SPIKE_PULLBACK_RISK": 12.0,
    "RANGE_REENTRY_RISK": 10.0,
    "DISTRIBUTION_RISK": 12.0,
    "IMPULSE_EXHAUSTION_RISK": 12.0,
    "LOW_CONFIDENCE": 8.0,
    "CONFLICTING_PHASE_CONTEXT": 10.0,
    "CHOP_WITHOUT_SETUP": 12.0,
    "WEAK_CONTEXT_FILTERED_TO_NO_SETUP": 10.0,
    "NO_STRUCTURAL_SETUP": 20.0,
}
_TIER_SCORE_CAP = {"GOOD": 100.0, "ACCEPTABLE": 79.999, "WEAK": 64.999, "POOR": 44.999,
                   "INVALID": 0.0, "UNKNOWN": 0.0}


@dataclass(frozen=True, slots=True)
class SetupQualityDiagnostics:
    quality: str
    quality_score: float | None
    structural_score: float
    confirmation_score: float
    context_score: float
    conflict_penalty: float
    invalidation_penalty: float
    quality_reasons: list[str] = field(default_factory=list)
    quality_warnings: list[str] = field(default_factory=list)
    has_sufficient_structure: bool = False
    has_confirmation_evidence: bool = False
    has_context_alignment: bool = False
    has_conflict: bool = False
    has_hard_invalidation: bool = False
    capped_by_analysis_entry_quality: bool = False
    source_analysis_entry_quality: str | None = None

    def __post_init__(self) -> None:
        quality = SetupQuality(self.quality).value
        object.__setattr__(self, "quality", quality)
        for name in ("structural_score", "confirmation_score", "context_score",
                     "conflict_penalty", "invalidation_penalty"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 100.0:
                raise ValueError(f"{name} must be in the 0..100 range")
            object.__setattr__(self, name, round(value, 3))
        if self.quality_score is not None:
            score = float(self.quality_score)
            if not 0.0 <= score <= 100.0:
                raise ValueError("quality_score must be in the 0..100 range")
            object.__setattr__(self, "quality_score", round(score, 3))
        if quality == SetupQuality.INVALID.value and not self.has_hard_invalidation:
            # Context invalidation is also a valid INVALID basis.
            if SetupReasonCode.QUALITY_INVALIDATED_BY_CONTEXT.value not in self.quality_reasons:
                raise ValueError("INVALID quality requires an invalidation reason")


def quality_from_score(score: float | None, *, hard_invalidation: bool = False) -> str:
    if hard_invalidation:
        return SetupQuality.INVALID.value
    if score is None:
        return SetupQuality.UNKNOWN.value
    value = max(0.0, min(100.0, float(score)))
    if value >= 80.0:
        return SetupQuality.GOOD.value
    if value >= 65.0:
        return SetupQuality.ACCEPTABLE.value
    if value >= 45.0:
        return SetupQuality.WEAK.value
    if value > 0.0:
        return SetupQuality.POOR.value
    return SetupQuality.UNKNOWN.value


def _analysis_cap(source_quality: str | None) -> str:
    value = str(source_quality).upper() if source_quality is not None else SetupQuality.UNKNOWN.value
    return value if value in QUALITY_ORDER else SetupQuality.UNKNOWN.value


def diagnose_setup_quality(
    *, status: str, setup_type: str, direction_hint: str, confirmation_state: str,
    diagnostics: SetupDiagnostics | None, reason_codes: list[str] | tuple[str, ...] = (),
    invalidation_reasons: list[str] | tuple[str, ...] = (),
    source_analysis_entry_quality: str | None = None, source_confidence: float | None = None,
    source_regime: str | None = None, source_impulse_phase: str | None = None,
) -> SetupQualityDiagnostics:
    """Compute setup quality exclusively from contemporaneous analysis/setup facts."""
    status = SetupStatus(status).value
    setup_type = SetupType(setup_type).value
    direction = DirectionHint(direction_hint).value
    confirmation = ConfirmationState(confirmation_state).value
    tokens = {str(item).upper() for item in (*reason_codes, *invalidation_reasons)}
    reasons = [SetupReasonCode.QUALITY_NO_FUTURE_BARS_USED.value]
    warnings: list[str] = []
    source_quality = _analysis_cap(source_analysis_entry_quality)

    if status in {SetupStatus.NO_SETUP.value, SetupStatus.ERROR.value}:
        reason = (SetupReasonCode.QUALITY_NOT_APPLICABLE_NO_SETUP.value
                  if status == SetupStatus.NO_SETUP.value
                  else SetupReasonCode.QUALITY_UNKNOWN_INSUFFICIENT_DIAGNOSTICS.value)
        reasons.append(reason)
        return SetupQualityDiagnostics(
            quality=SetupQuality.UNKNOWN.value, quality_score=None, structural_score=0.0,
            confirmation_score=0.0, context_score=0.0, conflict_penalty=0.0,
            invalidation_penalty=0.0, quality_reasons=reasons, quality_warnings=warnings,
            source_analysis_entry_quality=source_analysis_entry_quality,
        )

    hard = bool(tokens.intersection(HARD_INVALIDATIONS))
    context_invalid = status == SetupStatus.SETUP_INVALID.value or confirmation in {
        ConfirmationState.REJECTED_BY_ANALYSIS.value,
        ConfirmationState.INVALIDATED_BY_CONTEXT.value,
    }
    diag = diagnostics or SetupDiagnostics()
    sufficient = bool(diag.has_structural_trigger and setup_type != SetupType.NO_SETUP.value and
                      diag.semantic_bucket in {SetupSemanticBucket.CANDIDATE_STRUCTURE.value,
                                               SetupSemanticBucket.PRE_SETUP_WAITING_CONFIRMATION.value,
                                               SetupSemanticBucket.INVALIDATED_STRUCTURE.value})
    structural = (22.0 if diag.has_structural_trigger else 0.0)
    structural += 6.0 if diag.has_directional_context else 0.0
    structural += 5.0 if diag.has_level_context else 0.0
    structural += 2.0 if sufficient else 0.0
    if structural >= 30.0:
        reasons.append(SetupReasonCode.QUALITY_STRONG_STRUCTURE.value)
    elif sufficient:
        reasons.append(SetupReasonCode.QUALITY_ACCEPTABLE_STRUCTURE.value)
    else:
        reasons.append(SetupReasonCode.QUALITY_WEAK_STRUCTURE.value)

    has_confirmation = confirmation == ConfirmationState.CONFIRMED_BY_ANALYSIS.value
    if has_confirmation:
        confirmation_score = 30.0
        reasons.append(SetupReasonCode.QUALITY_CONFIRMED_BY_ANALYSIS.value)
    elif confirmation == ConfirmationState.AWAITING_CONFIRMATION.value:
        confirmation_score = 13.0
        reasons.append(SetupReasonCode.QUALITY_WAITING_CONFIRMATION_CAP.value)
    else:
        confirmation_score = 0.0

    regime = str(source_regime or "").upper()
    aligned = ((regime == "UP" and direction == DirectionHint.BULLISH.value) or
               (regime == "DOWN" and direction == DirectionHint.BEARISH.value) or
               (regime in {"FLAT", "UNKNOWN"} and diag.has_level_context and
                direction in {DirectionHint.BULLISH.value, DirectionHint.BEARISH.value,
                              DirectionHint.NEUTRAL.value}))
    context_score = 12.0 if aligned else (5.0 if diag.has_level_context else 0.0)
    if aligned:
        reasons.append(SetupReasonCode.QUALITY_ALIGNED_DIRECTIONAL_CONTEXT.value)
    confidence = max(0.0, min(1.0, float(source_confidence or 0.0)))
    context_score += 15.0 * confidence
    phase = str(source_impulse_phase or "").upper()
    if phase in {"IMPULSE_EXTENSION", "CONTROLLED_PULLBACK", "CONTROLLED_PULLBACK_CONTINUATION",
                 "NO_IMPULSE", "RANGE_REJECTION"}:
        context_score += 8.0
    if confidence < 0.4 or "LOW_CONFIDENCE" in tokens:
        reasons.append(SetupReasonCode.QUALITY_LOW_ANALYSIS_CONFIDENCE.value)

    active_conflicts = sorted(tokens.intersection(CONFLICT_PENALTIES))
    conflict_penalty = min(35.0, sum(CONFLICT_PENALTIES[item] for item in active_conflicts))
    if active_conflicts:
        reasons.append(SetupReasonCode.QUALITY_CONFLICTING_CONTEXT.value)
        warnings.extend(active_conflicts)
    invalidation_penalty = 100.0 if hard else (60.0 if context_invalid else 0.0)

    if hard or context_invalid:
        reasons.append(SetupReasonCode.QUALITY_INVALIDATED_BY_CONTEXT.value)
        return SetupQualityDiagnostics(
            quality=SetupQuality.INVALID.value, quality_score=0.0,
            structural_score=structural, confirmation_score=confirmation_score,
            context_score=context_score, conflict_penalty=conflict_penalty,
            invalidation_penalty=invalidation_penalty, quality_reasons=reasons,
            quality_warnings=warnings, has_sufficient_structure=sufficient,
            has_confirmation_evidence=has_confirmation, has_context_alignment=aligned,
            has_conflict=bool(active_conflicts), has_hard_invalidation=hard,
            source_analysis_entry_quality=source_analysis_entry_quality,
        )

    score = max(0.0, min(100.0, structural + confirmation_score + context_score - conflict_penalty))
    quality = quality_from_score(score)
    if status == SetupStatus.WAIT_FOR_CONFIRMATION.value and QUALITY_ORDER[quality] < QUALITY_ORDER[SetupQuality.WEAK.value]:
        quality = SetupQuality.WEAK.value
        score = min(score, _TIER_SCORE_CAP[quality])
    cap = source_quality if source_quality != SetupQuality.UNKNOWN.value else SetupQuality.WEAK.value
    capped = QUALITY_ORDER[quality] < QUALITY_ORDER[cap]
    if capped:
        quality = cap
        score = min(score, _TIER_SCORE_CAP[cap])
        reasons.append(SetupReasonCode.QUALITY_CAPPED_BY_ANALYSIS_ENTRY_QUALITY.value)
    return SetupQualityDiagnostics(
        quality=quality, quality_score=score, structural_score=structural,
        confirmation_score=confirmation_score, context_score=context_score,
        conflict_penalty=conflict_penalty, invalidation_penalty=invalidation_penalty,
        quality_reasons=reasons, quality_warnings=warnings,
        has_sufficient_structure=sufficient, has_confirmation_evidence=has_confirmation,
        has_context_alignment=aligned, has_conflict=bool(active_conflicts),
        has_hard_invalidation=hard, capped_by_analysis_entry_quality=capped,
        source_analysis_entry_quality=source_analysis_entry_quality,
    )


calculate_setup_quality = diagnose_setup_quality
