from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.labels.first_touch_label_builder import resolve_setup_direction, resolve_setup_type
from app.labels.label_config import LabelConfig
from app.labels.label_models import LABEL_DOWN, LABEL_FLAT, LABEL_UP


OPPORTUNITY_DIRECTION_NONE = "NONE"
OPPORTUNITY_REASON_SETUP_FIRST_TOUCH_LONG = "setup_first_touch_long"
OPPORTUNITY_REASON_SETUP_FIRST_TOUCH_SHORT = "setup_first_touch_short"
OPPORTUNITY_REASON_STRONG_CONFLUENCE_LONG = "strong_confluence_long"
OPPORTUNITY_REASON_STRONG_CONFLUENCE_SHORT = "strong_confluence_short"
OPPORTUNITY_REASON_NO_SETUP = "no_setup"
OPPORTUNITY_REASON_AMBIGUOUS_TOUCH = "ambiguous_touch"
OPPORTUNITY_REASON_VOLATILE_FLAT = "volatile_flat"
OPPORTUNITY_REASON_LOW_EDGE_CONTEXT = "low_edge_context"
OPPORTUNITY_REASON_SETUP_DIRECTION_CONFLICT = "setup_direction_conflict"
OPPORTUNITY_REASON_SETUP_DIRECTION_UNAVAILABLE = "setup_direction_unavailable"
OPPORTUNITY_REASON_SETUP_QUALITY_BELOW_THRESHOLD = "setup_quality_below_threshold"


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


@dataclass(frozen=True, slots=True)
class OpportunityLabelPayload:
    opportunity_label: int
    opportunity_direction: str
    opportunity_reason: str
    opportunity_score: float
    setup_type: str
    setup_quality_score: float
    setup_invalidation_distance_atr: float
    setup_expected_move_atr: float
    label_ambiguity_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_label": int(self.opportunity_label),
            "opportunity_direction": self.opportunity_direction,
            "opportunity_reason": self.opportunity_reason,
            "opportunity_score": float(self.opportunity_score),
            "setup_type": self.setup_type,
            "setup_quality_score": float(self.setup_quality_score),
            "setup_invalidation_distance_atr": float(self.setup_invalidation_distance_atr),
            "setup_expected_move_atr": float(self.setup_expected_move_atr),
            "label_ambiguity_score": float(self.label_ambiguity_score),
        }


class OpportunityLabelBuilder:
    MIN_SETUP_QUALITY_SCORE = 0.55
    MIN_EXPECTED_MOVE_ATR = 0.45
    MAX_INVALIDATION_DISTANCE_ATR = 1.10
    MAX_LABEL_AMBIGUITY_SCORE = 0.45
    MIN_OPPORTUNITY_SCORE = 0.55

    def build(
        self,
        *,
        features_json: Mapping[str, Any] | None,
        direction_label: str,
        tp_before_sl: bool | None,
        future_move_atr: float,
        max_favorable_move_atr: float,
        max_adverse_move_atr: float,
        config: LabelConfig | None = None,
    ) -> OpportunityLabelPayload:
        features = dict(features_json or {})
        setup_quality_min_threshold = self._resolve_setup_quality_min_threshold(config)
        setup_type = resolve_setup_type(features)
        setup_direction = self._setup_direction(
            features_json=features,
            direction_label=direction_label,
        )
        setup_quality_score = self._setup_quality_score(
            features_json=features,
            setup_type=setup_type,
            setup_direction=setup_direction,
        )
        expected_move_atr = self._expected_move_atr(
            direction_label=direction_label,
            future_move_atr=future_move_atr,
            max_favorable_move_atr=max_favorable_move_atr,
        )
        invalidation_distance_atr = max(0.0, float(max_adverse_move_atr))
        label_ambiguity_score = self._label_ambiguity_score(
            direction_label=direction_label,
            tp_before_sl=tp_before_sl,
            expected_move_atr=expected_move_atr,
            invalidation_distance_atr=invalidation_distance_atr,
            max_favorable_move_atr=max_favorable_move_atr,
        )
        opportunity_score = self._opportunity_score(
            setup_quality_score=setup_quality_score,
            expected_move_atr=expected_move_atr,
            invalidation_distance_atr=invalidation_distance_atr,
            label_ambiguity_score=label_ambiguity_score,
            tp_before_sl=tp_before_sl,
        )

        opportunity_label = 0
        opportunity_direction = OPPORTUNITY_DIRECTION_NONE
        opportunity_reason = OPPORTUNITY_REASON_LOW_EDGE_CONTEXT

        if setup_type == "no_setup":
            opportunity_reason = OPPORTUNITY_REASON_NO_SETUP
        elif setup_direction == OPPORTUNITY_DIRECTION_NONE:
            opportunity_reason = OPPORTUNITY_REASON_SETUP_DIRECTION_UNAVAILABLE
        elif direction_label == LABEL_FLAT:
            opportunity_reason = (
                OPPORTUNITY_REASON_VOLATILE_FLAT
                if max_favorable_move_atr >= self.MIN_EXPECTED_MOVE_ATR and invalidation_distance_atr >= 0.35
                else OPPORTUNITY_REASON_LOW_EDGE_CONTEXT
            )
        elif direction_label in {LABEL_UP, LABEL_DOWN} and setup_direction != direction_label:
            opportunity_reason = OPPORTUNITY_REASON_SETUP_DIRECTION_CONFLICT
        elif tp_before_sl is None or label_ambiguity_score > self.MAX_LABEL_AMBIGUITY_SCORE:
            opportunity_reason = OPPORTUNITY_REASON_AMBIGUOUS_TOUCH
        elif tp_before_sl is not True:
            opportunity_reason = OPPORTUNITY_REASON_LOW_EDGE_CONTEXT
        elif (
            setup_quality_min_threshold is not None
            and setup_quality_score < setup_quality_min_threshold
        ):
            return OpportunityLabelPayload(
                opportunity_label=0,
                opportunity_direction=OPPORTUNITY_DIRECTION_NONE,
                opportunity_reason=OPPORTUNITY_REASON_SETUP_QUALITY_BELOW_THRESHOLD,
                opportunity_score=0.0,
                setup_type=setup_type,
                setup_quality_score=setup_quality_score,
                setup_invalidation_distance_atr=invalidation_distance_atr,
                setup_expected_move_atr=expected_move_atr,
                label_ambiguity_score=label_ambiguity_score,
            )
        elif (
            setup_quality_score >= self.MIN_SETUP_QUALITY_SCORE
            and expected_move_atr >= self.MIN_EXPECTED_MOVE_ATR
            and invalidation_distance_atr <= self.MAX_INVALIDATION_DISTANCE_ATR
            and opportunity_score >= self.MIN_OPPORTUNITY_SCORE
        ):
            opportunity_label = 1
            opportunity_direction = setup_direction
            opportunity_reason = self._positive_reason(
                setup_direction=setup_direction,
                setup_quality_score=setup_quality_score,
                features_json=features,
            )
        else:
            opportunity_reason = OPPORTUNITY_REASON_LOW_EDGE_CONTEXT

        return OpportunityLabelPayload(
            opportunity_label=opportunity_label,
            opportunity_direction=opportunity_direction,
            opportunity_reason=opportunity_reason,
            opportunity_score=opportunity_score,
            setup_type=setup_type,
            setup_quality_score=setup_quality_score,
            setup_invalidation_distance_atr=invalidation_distance_atr,
            setup_expected_move_atr=expected_move_atr,
            label_ambiguity_score=label_ambiguity_score,
        )

    @staticmethod
    def _resolve_setup_quality_min_threshold(config: LabelConfig | None) -> float | None:
        if config is None or config.setup_quality_min_threshold is None:
            return None
        return max(0.0, min(1.0, float(config.setup_quality_min_threshold)))

    @staticmethod
    def _setup_direction(
        *,
        features_json: Mapping[str, Any],
        direction_label: str,
    ) -> str:
        del direction_label
        resolved_direction = resolve_setup_direction(features_json)
        if resolved_direction in {LABEL_UP, LABEL_DOWN}:
            return resolved_direction
        return OPPORTUNITY_DIRECTION_NONE

    @staticmethod
    def _setup_quality_score(
        *,
        features_json: Mapping[str, Any],
        setup_type: str,
        setup_direction: str,
    ) -> float:
        if setup_type == "no_setup" or setup_direction == OPPORTUNITY_DIRECTION_NONE:
            return 0.0
        nison_score = max(
            (_safe_float(value) for key, value in features_json.items() if str(key).startswith("nison_")),
            default=0.0,
        )
        alt_score = max(
            (_safe_float(value) for key, value in features_json.items() if str(key).startswith("alt_")),
            default=0.0,
        )
        path_score = max(
            (_safe_float(value) for key, value in features_json.items() if str(key).startswith("path_")),
            default=0.0,
        )
        support_quality = 1.0 - min(_safe_float(features_json.get("support_distance_atr"), 1.5) / 1.5, 1.0)
        resistance_quality = 1.0 - min(_safe_float(features_json.get("resistance_distance_atr"), 1.5) / 1.5, 1.0)
        directional_structure = support_quality if setup_direction == LABEL_UP else resistance_quality
        return _clamp((0.38 * max(nison_score, alt_score, path_score)) + (0.36 * directional_structure) + 0.26)

    @staticmethod
    def _expected_move_atr(
        *,
        direction_label: str,
        future_move_atr: float,
        max_favorable_move_atr: float,
    ) -> float:
        if direction_label == LABEL_FLAT:
            return max(0.0, float(max_favorable_move_atr))
        if direction_label == LABEL_DOWN:
            return max(abs(float(future_move_atr)), float(max_favorable_move_atr))
        return max(abs(float(future_move_atr)), float(max_favorable_move_atr))

    @staticmethod
    def _label_ambiguity_score(
        *,
        direction_label: str,
        tp_before_sl: bool | None,
        expected_move_atr: float,
        invalidation_distance_atr: float,
        max_favorable_move_atr: float,
    ) -> float:
        if direction_label == LABEL_FLAT:
            volatile_component = 1.0 if max_favorable_move_atr >= 0.70 and invalidation_distance_atr >= 0.35 else 0.65
            return _clamp(volatile_component)

        base = 0.15
        if tp_before_sl is None:
            base += 0.45
        elif tp_before_sl is False:
            base += 0.30
        move_gap = abs(float(expected_move_atr) - float(invalidation_distance_atr))
        if move_gap < 0.15:
            base += 0.25
        elif move_gap < 0.30:
            base += 0.15
        if expected_move_atr < 0.35:
            base += 0.10
        return _clamp(base)

    @staticmethod
    def _opportunity_score(
        *,
        setup_quality_score: float,
        expected_move_atr: float,
        invalidation_distance_atr: float,
        label_ambiguity_score: float,
        tp_before_sl: bool | None,
    ) -> float:
        move_score = _clamp(expected_move_atr / 1.5)
        risk_score = 1.0 - _clamp(invalidation_distance_atr / 1.5)
        ambiguity_score = 1.0 - _clamp(label_ambiguity_score)
        tp_bonus = 1.0 if tp_before_sl is True else (0.35 if tp_before_sl is None else 0.0)
        return _clamp(
            (0.35 * setup_quality_score)
            + (0.25 * move_score)
            + (0.20 * risk_score)
            + (0.15 * ambiguity_score)
            + (0.05 * tp_bonus)
        )

    @staticmethod
    def _positive_reason(
        *,
        setup_direction: str,
        setup_quality_score: float,
        features_json: Mapping[str, Any],
    ) -> str:
        confluence_count = 0
        for prefix in ("nison_", "alt_", "path_"):
            if max((_safe_float(value) for key, value in features_json.items() if str(key).startswith(prefix)), default=0.0) >= 0.55:
                confluence_count += 1
        if bool(features_json.get("near_support")) or bool(features_json.get("near_resistance")):
            confluence_count += 1
        if confluence_count >= 2 and setup_quality_score >= 0.78:
            return (
                OPPORTUNITY_REASON_STRONG_CONFLUENCE_LONG
                if setup_direction == LABEL_UP
                else OPPORTUNITY_REASON_STRONG_CONFLUENCE_SHORT
            )
        return (
            OPPORTUNITY_REASON_SETUP_FIRST_TOUCH_LONG
            if setup_direction == LABEL_UP
            else OPPORTUNITY_REASON_SETUP_FIRST_TOUCH_SHORT
        )
