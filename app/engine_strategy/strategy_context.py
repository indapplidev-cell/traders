"""Normalized read-only strategy view of a SetupCandidate."""

from __future__ import annotations

from dataclasses import dataclass

from app.engine_setup.setup_candidate import SetupCandidate
from app.engine_setup.causal_planning_context import select_causal_primitives


@dataclass(frozen=True, slots=True)
class StrategyContext:
    setup_status: str
    setup_type: str
    direction_hint: str
    setup_quality: str
    quality_score: float | None
    confirmation_state: str
    semantic_bucket: str | None
    quality_reasons: tuple[str, ...]
    quality_warnings: tuple[str, ...]
    invalidation_reasons: tuple[str, ...]
    diagnostic_reasons: tuple[str, ...]
    analysis_confidence: float | None
    has_hard_invalidation: bool
    has_conflict: bool
    source_future_bars_used: bool
    source_is_trade_signal: bool
    causal_primitives: dict[str, object]
    structural_score: float | None
    confirmation_score: float | None
    context_score: float | None
    conflict_penalty: float | None
    invalidation_penalty: float | None

    @classmethod
    def from_setup_candidate(cls, candidate: SetupCandidate) -> "StrategyContext":
        diagnostics = candidate.diagnostics
        quality = candidate.quality_diagnostics
        source_context = dict(candidate.context or {})
        return cls(
            setup_status=candidate.status, setup_type=candidate.setup_type,
            direction_hint=candidate.direction_hint, setup_quality=candidate.setup_quality,
            quality_score=candidate.quality_score,
            confirmation_state=candidate.confirmation_state,
            semantic_bucket=getattr(diagnostics, "semantic_bucket", None),
            quality_reasons=tuple(candidate.quality_reasons),
            quality_warnings=tuple(candidate.quality_warnings),
            invalidation_reasons=tuple(candidate.invalidation_reasons),
            diagnostic_reasons=tuple(getattr(diagnostics, "diagnostic_reasons", ())),
            analysis_confidence=candidate.source_confidence,
            has_hard_invalidation=bool(
                getattr(quality, "has_hard_invalidation", False)
                or source_context.get("has_hard_invalidation", False)
            ),
            has_conflict=bool(
                getattr(quality, "has_conflict", False) or source_context.get("has_conflict", False)
            ),
            source_future_bars_used=bool(candidate.future_bars_used),
            source_is_trade_signal=bool(candidate.is_trade_signal),
            causal_primitives=select_causal_primitives(source_context),
            structural_score=getattr(quality, "structural_score", None),
            confirmation_score=getattr(quality, "confirmation_score", None),
            context_score=getattr(quality, "context_score", None),
            conflict_penalty=getattr(quality, "conflict_penalty", None),
            invalidation_penalty=getattr(quality, "invalidation_penalty", None),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "confirmation_state": self.confirmation_state,
            "semantic_bucket": self.semantic_bucket,
            "quality_reasons": list(self.quality_reasons),
            "quality_warnings": list(self.quality_warnings),
            "invalidation_reasons": list(self.invalidation_reasons),
            "diagnostic_reasons": list(self.diagnostic_reasons),
            "analysis_confidence": self.analysis_confidence,
            "has_hard_invalidation": self.has_hard_invalidation,
            "has_conflict": self.has_conflict,
            "setup_component_scores": {
                "structure": self.structural_score,
                "candle_confirmation": self.confirmation_score,
                "context_alignment": self.context_score,
                "conflict_penalty": self.conflict_penalty,
                "invalidation_penalty": self.invalidation_penalty,
            },
            **self.causal_primitives,
        }
