"""Causal hypothetical level builder; it never observes fills or future candles."""

from __future__ import annotations

from dataclasses import asdict, dataclass

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


@dataclass(frozen=True, slots=True)
class PaperLevelEvaluation:
    """Durable progressive geometry/RR evidence, including rejected attempts."""

    calculation_version: str = "paper-level-geometry-v2"
    direction: str | None = None
    entry: float | None = None
    invalidation: float | None = None
    stop: float | None = None
    target: float | None = None
    risk_distance: float | None = None
    reward_distance: float | None = None
    raw_rr: float | None = None
    rr_threshold: float | None = None
    entry_source: str | None = None
    invalidation_source: str | None = None
    buffer_source: str | None = None
    buffer_value: float | None = None
    stop_source: str | None = None
    target_source: str | None = None
    geometry_pass: bool = False
    target_pass: bool = False
    rr_pass: bool = False
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class PaperLevelBuilder:
    def __init__(self, config: PaperConfig | None = None) -> None:
        self.config = config or PaperConfig()

    def build(self, context: PaperContext, direction: str) -> PaperLevels:
        attempt = self.evaluate(context, direction)
        if attempt.rejection_reason is not None:
            raise PaperLevelError(attempt.rejection_reason)
        assert all(value is not None for value in (
            attempt.entry, attempt.invalidation, attempt.stop, attempt.target,
            attempt.raw_rr, attempt.entry_source, attempt.invalidation_source,
            attempt.stop_source, attempt.target_source,
        ))
        return PaperLevels(
            entry=float(attempt.entry), invalidation=float(attempt.invalidation),
            stop=float(attempt.stop), target=float(attempt.target),
            planned_rr=round(float(attempt.raw_rr), 8),
            entry_source=str(attempt.entry_source),
            invalidation_source=str(attempt.invalidation_source),
            stop_source=str(attempt.stop_source), target_source=str(attempt.target_source),
        )

    def evaluate(self, context: PaperContext, direction: str) -> PaperLevelEvaluation:
        if not isinstance(context, PaperContext):
            raise TypeError("context must be a PaperContext")
        direction = str(direction).upper()
        if direction not in {"BULLISH", "BEARISH"}:
            return PaperLevelEvaluation(
                direction=direction, rr_threshold=self.config.minimum_planned_rr,
                rejection_reason=R.PAPER_REJECT_INVALID_DIRECTION.value,
            )
        entry, entry_source = self._first(context, (
            "confirmation_close", "reference_close", "current_closed_candle_close"))
        if entry is None:
            return PaperLevelEvaluation(
                direction=direction, rr_threshold=self.config.minimum_planned_rr,
                rejection_reason=R.PAPER_NO_PLAN_MISSING_ENTRY_REFERENCE.value,
            )
        invalidation_names = (("causal_support_level", "causal_invalidation_level")
                              if direction == "BULLISH" else
                              ("causal_resistance_level", "causal_invalidation_level"))
        invalidation, invalidation_source = self._first(context, invalidation_names)
        if invalidation is None:
            return PaperLevelEvaluation(
                direction=direction, entry=entry, entry_source=entry_source,
                rr_threshold=self.config.minimum_planned_rr,
                rejection_reason=R.PAPER_NO_PLAN_MISSING_INVALIDATION_LEVEL.value,
            )
        if ((direction == "BULLISH" and invalidation >= entry)
                or (direction == "BEARISH" and invalidation <= entry)):
            return PaperLevelEvaluation(
                direction=direction, entry=entry, invalidation=invalidation,
                entry_source=entry_source, invalidation_source=invalidation_source,
                rr_threshold=self.config.minimum_planned_rr,
                rejection_reason=R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value,
            )

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
                return PaperLevelEvaluation(
                    direction=direction, entry=entry, invalidation=invalidation,
                    stop=stop, entry_source=entry_source,
                    invalidation_source=invalidation_source,
                    buffer_source=buffer_source, buffer_value=buffer,
                    stop_source=f"{invalidation_source}+{buffer_source}",
                    geometry_pass=True, rr_threshold=self.config.minimum_planned_rr,
                    rejection_reason=R.PAPER_NO_PLAN_MISSING_TARGET_LEVEL.value,
                )
            risk_distance = entry - stop if direction == "BULLISH" else stop - entry
            if risk_distance <= 0:
                return PaperLevelEvaluation(
                    direction=direction, entry=entry, invalidation=invalidation,
                    stop=stop, entry_source=entry_source,
                    invalidation_source=invalidation_source,
                    buffer_source=buffer_source, buffer_value=buffer,
                    stop_source=f"{invalidation_source}+{buffer_source}",
                    rr_threshold=self.config.minimum_planned_rr,
                    rejection_reason=R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value,
                )
            reward = risk_distance * self.config.default_target_rr
            target = entry + reward if direction == "BULLISH" else entry - reward
            target_source = "paper_fallback_default_target_rr"

        risk_distance = entry - stop if direction == "BULLISH" else stop - entry
        reward_distance = target - entry if direction == "BULLISH" else entry - target
        if risk_distance <= 0 or reward_distance <= 0:
            reason = R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value
            return PaperLevelEvaluation(
                direction=direction, entry=entry, invalidation=invalidation,
                stop=stop, target=target, risk_distance=risk_distance,
                reward_distance=reward_distance, entry_source=entry_source,
                invalidation_source=invalidation_source,
                buffer_source=buffer_source, buffer_value=buffer,
                stop_source=f"{invalidation_source}+{buffer_source}",
                target_source=target_source, rr_threshold=self.config.minimum_planned_rr,
                rejection_reason=reason,
            )
        if self.config.maximum_stop_distance_pct is not None and risk_distance / entry > self.config.maximum_stop_distance_pct:
            reason = R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value
            return PaperLevelEvaluation(
                direction=direction, entry=entry, invalidation=invalidation,
                stop=stop, target=target, risk_distance=risk_distance,
                reward_distance=reward_distance, entry_source=entry_source,
                invalidation_source=invalidation_source,
                buffer_source=buffer_source, buffer_value=buffer,
                stop_source=f"{invalidation_source}+{buffer_source}",
                target_source=target_source, rr_threshold=self.config.minimum_planned_rr,
                rejection_reason=reason,
            )
        if self.config.maximum_target_distance_pct is not None and reward_distance / entry > self.config.maximum_target_distance_pct:
            reason = R.PAPER_REJECT_INVALID_LEVEL_GEOMETRY.value
            return PaperLevelEvaluation(
                direction=direction, entry=entry, invalidation=invalidation,
                stop=stop, target=target, risk_distance=risk_distance,
                reward_distance=reward_distance, entry_source=entry_source,
                invalidation_source=invalidation_source,
                buffer_source=buffer_source, buffer_value=buffer,
                stop_source=f"{invalidation_source}+{buffer_source}",
                target_source=target_source, rr_threshold=self.config.minimum_planned_rr,
                rejection_reason=reason,
            )
        planned_rr = reward_distance / risk_distance
        rr_pass = planned_rr >= self.config.minimum_planned_rr
        return PaperLevelEvaluation(
            direction=direction, entry=entry, invalidation=invalidation,
            stop=stop, target=target, risk_distance=risk_distance,
            reward_distance=reward_distance, raw_rr=round(planned_rr, 8),
            rr_threshold=self.config.minimum_planned_rr,
            entry_source=str(entry_source),
            invalidation_source=str(invalidation_source),
            buffer_source=buffer_source, buffer_value=buffer,
            stop_source=f"{invalidation_source}+{buffer_source}",
            target_source=str(target_source), geometry_pass=True,
            target_pass=True, rr_pass=rr_pass,
            rejection_reason=(
                None if rr_pass else R.PAPER_REJECT_LOW_PLANNED_RR.value
            ),
        )

    @staticmethod
    def _first(context: PaperContext, names: tuple[str, ...]) -> tuple[float | None, str | None]:
        for name in names:
            value = getattr(context, name)
            if value is not None:
                return value, name
        return None, None
