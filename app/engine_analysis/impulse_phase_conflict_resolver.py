"""Research-only phase conflict resolver for ENGINE-ANALYSIS-34."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PhaseConflictInput:
    source_regime: str
    source_phase: str
    source_entry_quality: str
    structure: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.source_regime not in {"UP", "DOWN", "FLAT", "UNKNOWN"}:
            raise ValueError("unsupported source_regime")


def resolve_phase_conflicts(data: PhaseConflictInput) -> dict[str, Any]:
    """Resolve analysis conflicts without mutating the runtime decision."""

    evidence = data.structure
    regime = data.source_regime
    phase = data.source_phase
    quality = data.source_entry_quality
    reasons = list(evidence.get("reason_codes", ()))

    def add(code: str) -> None:
        if code not in reasons:
            reasons.append(code)

    inferred_reentry = bool(
        evidence.get("range_reentry")
        or (
            data.source_phase == "RANGE_REENTRY"
            and data.source_regime in {"UP", "DOWN"}
            and not evidence.get("range_structure")
        )
    )

    if evidence.get("choppy_structure"):
        regime, phase, quality = "UNKNOWN", "CONFLICTED_IMPULSE", "INVALID"
    elif evidence.get("post_spike_pullback"):
        regime, phase, quality = "UNKNOWN", "POST_SPIKE_PULLBACK", "POOR"
        add("PHASE_CONFLICT_RESOLVED_TO_PULLBACK")
        add("INDICATOR_TREND_OVERRIDDEN_BY_STRUCTURE")
    elif evidence.get("distribution"):
        regime, phase, quality = "FLAT", "IMPULSE_EXHAUSTION_RISK", "POOR"
        add("PHASE_CONFLICT_RESOLVED_TO_DISTRIBUTION")
        add("INDICATOR_TREND_OVERRIDDEN_BY_STRUCTURE")
    elif evidence.get("late_confirmation_risk"):
        phase, quality = "LATE_CONFIRMATION_RISK", "POOR"
        add("PHASE_CONFLICT_RESOLVED_TO_LATE_RISK")
    elif inferred_reentry:
        regime, phase, quality = "UNKNOWN", "RANGE_REENTRY", "INVALID"
        add("PHASE_CONFLICT_RESOLVED_TO_RANGE")
        add("INDICATOR_TREND_OVERRIDDEN_BY_STRUCTURE")
    elif evidence.get("range_structure"):
        regime, phase, quality = "FLAT", "NO_IMPULSE", "INVALID"
        add("PHASE_CONFLICT_RESOLVED_TO_RANGE")
        if data.source_regime != "FLAT":
            add("INDICATOR_TREND_OVERRIDDEN_BY_STRUCTURE")
    elif evidence.get("impulse_exhaustion"):
        phase, quality = "IMPULSE_EXHAUSTION_RISK", "POOR"
    elif evidence.get("impulse_extension"):
        phase, quality = "IMPULSE_EXTENSION", "POOR"
    elif evidence.get("structural_follow_through"):
        phase = "IMPULSE_DETECTED"
        if quality in {"INVALID", "NOT_EVALUATED"}:
            quality = "ACCEPTABLE"

    structural_direction = evidence.get("structural_direction")
    if (
        data.source_regime == "UNKNOWN"
        and structural_direction in {"UP", "DOWN"}
        and evidence.get("structural_follow_through")
        and not any(evidence.get(key) for key in ("range_reentry", "post_spike_pullback", "distribution", "range_structure"))
    ):
        # This is an offline analytical classification only.  The safety block
        # below makes explicit that UNKNOWN is not converted into an action.
        regime = str(structural_direction)

    return {
        "analysis_regime": regime,
        "impulse_phase": phase,
        "entry_quality": quality,
        "reason_codes": reasons,
        "conflict_resolved": (regime, phase, quality) != (
            data.source_regime, data.source_phase, data.source_entry_quality
        ),
        "source": {
            "regime": data.source_regime,
            "impulse_phase": data.source_phase,
            "entry_quality": data.source_entry_quality,
        },
        "research_only": True,
        "safety": {
            "runtime_decision_changed": False,
            "trade_signal_created": False,
            "setup_created": False,
            "final_action": "NO_ACTION",
        },
    }


__all__ = ["PhaseConflictInput", "resolve_phase_conflicts"]
