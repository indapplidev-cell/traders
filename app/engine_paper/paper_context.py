"""Allow-listed causal primitives extracted solely from RiskDecision.risk_context."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.engine_risk.risk_decision import RiskDecision


ALLOWED_PRIMITIVES = frozenset({
    "reference_close", "confirmation_close", "current_closed_candle_close",
    "causal_support_level", "causal_resistance_level", "causal_invalidation_level",
    "causal_target_level", "nearest_opposite_level", "atr_value", "volatility_buffer",
    "causal_target_candidates", "causal_support_candidates",
    "causal_resistance_candidates", "higher_timeframe_target_candidates",
    "setup_type", "strategy_type", "direction_hint",
    "opportunity_id",
})
_FORBIDDEN_CONTAINER_TOKENS = ("future", "outcome", "realized", "fill", "pnl", "execution",
                               "position", "order")


def _find_value(payload: dict[str, Any], key: str) -> Any:
    if key in payload and payload[key] is not None:
        return payload[key]
    for container_key, value in payload.items():
        normalized = str(container_key).lower()
        if any(token in normalized for token in _FORBIDDEN_CONTAINER_TOKENS):
            continue
        if isinstance(value, dict):
            found = _find_value(value, key)
            if found is not None:
                return found
    return None


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


@dataclass(frozen=True, slots=True)
class PaperContext:
    reference_close: float | None = None
    confirmation_close: float | None = None
    current_closed_candle_close: float | None = None
    causal_support_level: float | None = None
    causal_resistance_level: float | None = None
    causal_invalidation_level: float | None = None
    causal_target_level: float | None = None
    nearest_opposite_level: float | None = None
    causal_target_candidates: tuple[dict[str, Any], ...] = ()
    atr_value: float | None = None
    volatility_buffer: float | None = None
    setup_type: str | None = None
    strategy_type: str | None = None
    direction_hint: str | None = None
    opportunity_id: str | None = None

    @classmethod
    def from_risk_decision(cls, decision: RiskDecision) -> "PaperContext":
        if not isinstance(decision, RiskDecision):
            raise TypeError("decision must be a RiskDecision")
        source = decision.risk_context if isinstance(decision.risk_context, dict) else {}
        values: dict[str, Any] = {}
        for name in ALLOWED_PRIMITIVES:
            raw = _find_value(source, name)
            if name == "causal_target_candidates":
                values[name] = tuple(
                    dict(item) for item in raw or () if isinstance(item, dict)
                )
            else:
                values[name] = raw if name in {
                    "setup_type", "strategy_type", "direction_hint",
                    "opportunity_id",
                    "causal_support_candidates", "causal_resistance_candidates",
                    "higher_timeframe_target_candidates",
                } else _number(raw)
        for extra in (
            "causal_support_candidates", "causal_resistance_candidates",
            "higher_timeframe_target_candidates",
        ):
            values.pop(extra, None)
        values["strategy_type"] = values["strategy_type"] or decision.source_strategy_type
        direction = str(values["direction_hint"] or decision.direction_hint).upper()
        values["direction_hint"] = direction if direction in {
            "BULLISH", "BEARISH", "NEUTRAL", "NONE"} else "NONE"
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}
