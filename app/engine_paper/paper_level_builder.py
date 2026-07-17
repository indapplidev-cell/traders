"""Causal hypothetical level builder; it never observes fills or future candles."""

from __future__ import annotations

from dataclasses import dataclass

from app.engine_paper.paper_config import PaperConfig
from app.engine_paper.paper_context import PaperContext
from app.engine_paper.paper_errors import PaperLevelError
from app.engine_paper.paper_reason_codes import PaperReasonCode as R


@dataclass(frozen=True, slots=True)
class PaperLevels:
    entry: float
    invalidation: float
    stop: float
    target: float
    planned_rr: float
    entry_source: str
    invalidation_source: str
    stop_source: str
    target_source: str


class PaperLevelBuilder:
    def __init__(self, config: PaperConfig | None = None) -> None:
        self.config = config or PaperConfig()

    def build(self, context: PaperContext, direction: str) -> PaperLevels:
        if not isinstance(context, PaperContext):
            raise TypeError("context must be a PaperContext")
        direction = str(direction).upper()
        if direction not in {"BULLISH", "BEARISH"}:
            raise PaperLevelError(R.PAPER_REJECT_INVALID_DIRECTION.value)
        entry, entry_source = self._first(context, (
            "confirmation_close", "reference_close", "current_closed_candle_close"))
        if entry is None:
            raise PaperLevelError(R.PAPER_NO_PLAN_MISSING_ENTRY_REFERENCE.value)
        invalidation_names = (("causal_support_level", "causal_invalidation_level")
                              if direction == "BULLISH" else
                              ("causal_resistance_level", "causal_invalidation_level"))
        invalidation, invalidation_source = self._first(context, invalidation_names)
        if invalidation is None:
            raise PaperLevelError(R.PAPER_NO_PLAN_MISSING_INVALIDATION_LEVEL.value)
        if ((direction == "BULLISH" and invalidation >= entry)
                or (direction == "BEARISH" and invalidation <= entry)):
            raise PaperLevelError(R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value)

        buffer = context.volatility_buffer
        buffer_source = "volatility_buffer"
        if buffer is None and context.atr_value is not None:
            buffer = context.atr_value
            buffer_source = "atr_value"
        if buffer is None:
            buffer = entry * self.config.default_stop_buffer_pct
            buffer_source = "default_stop_buffer_pct"
        stop = invalidation - buffer if direction == "BULLISH" else invalidation + buffer

        target, target_source = self._first(context, ("causal_target_level", "nearest_opposite_level"))
        if target is None:
            if not self.config.allow_fallback_target:
                raise PaperLevelError(R.PAPER_NO_PLAN_MISSING_TARGET_LEVEL.value)
            risk_distance = entry - stop if direction == "BULLISH" else stop - entry
            if risk_distance <= 0:
                raise PaperLevelError(R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value)
            reward = risk_distance * self.config.default_target_rr
            target = entry + reward if direction == "BULLISH" else entry - reward
            target_source = "paper_fallback_default_target_rr"

        risk_distance = entry - stop if direction == "BULLISH" else stop - entry
        reward_distance = target - entry if direction == "BULLISH" else entry - target
        if risk_distance <= 0 or reward_distance <= 0:
            raise PaperLevelError(R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value)
        if self.config.maximum_stop_distance_pct is not None and risk_distance / entry > self.config.maximum_stop_distance_pct:
            raise PaperLevelError(R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value)
        if self.config.maximum_target_distance_pct is not None and reward_distance / entry > self.config.maximum_target_distance_pct:
            raise PaperLevelError(R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value)
        planned_rr = reward_distance / risk_distance
        if planned_rr < self.config.minimum_planned_rr:
            raise PaperLevelError(R.PAPER_REJECT_LOW_PLANNED_RR.value)
        return PaperLevels(
            entry=entry, invalidation=invalidation, stop=stop, target=target,
            planned_rr=round(planned_rr, 8), entry_source=str(entry_source),
            invalidation_source=str(invalidation_source),
            stop_source=f"{invalidation_source}+{buffer_source}", target_source=str(target_source),
        )

    @staticmethod
    def _first(context: PaperContext, names: tuple[str, ...]) -> tuple[float | None, str | None]:
        for name in names:
            value = getattr(context, name)
            if value is not None:
                return value, name
        return None, None
