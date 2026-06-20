from __future__ import annotations

from app.labels.label_config import LabelConfig
from app.labels.label_models import LABEL_UP
from app.labels.opportunity_label_builder import (
    OPPORTUNITY_REASON_SETUP_QUALITY_BELOW_THRESHOLD,
    OpportunityLabelBuilder,
)


def _features(*, support_distance_atr: float) -> dict[str, float | bool]:
    return {
        "nison_bullish_engulfing": 0.55,
        "near_support": True,
        "support_distance_atr": support_distance_atr,
        "resistance_distance_atr": 1.50,
    }


def test_setup_quality_threshold_blocks_positive_opportunity() -> None:
    payload = OpportunityLabelBuilder().build(
        features_json=_features(support_distance_atr=1.125),
        direction_label=LABEL_UP,
        tp_before_sl=True,
        future_move_atr=0.80,
        max_favorable_move_atr=0.90,
        max_adverse_move_atr=0.20,
        config=LabelConfig(setup_quality_min_threshold=0.60),
    )

    assert 0.55 <= payload.setup_quality_score < 0.60
    assert payload.opportunity_label == 0
    assert payload.opportunity_reason == OPPORTUNITY_REASON_SETUP_QUALITY_BELOW_THRESHOLD
    assert payload.opportunity_score == 0.0


def test_setup_quality_threshold_allows_positive_opportunity_above_floor() -> None:
    payload = OpportunityLabelBuilder().build(
        features_json=_features(support_distance_atr=0.50),
        direction_label=LABEL_UP,
        tp_before_sl=True,
        future_move_atr=0.80,
        max_favorable_move_atr=0.90,
        max_adverse_move_atr=0.20,
        config=LabelConfig(setup_quality_min_threshold=0.60),
    )

    assert payload.setup_quality_score >= 0.60
    assert payload.opportunity_label == 1
    assert payload.opportunity_reason in {"setup_first_touch_long", "strong_confluence_long"}


def test_setup_quality_threshold_none_keeps_previous_behavior() -> None:
    payload = OpportunityLabelBuilder().build(
        features_json=_features(support_distance_atr=1.125),
        direction_label=LABEL_UP,
        tp_before_sl=True,
        future_move_atr=0.80,
        max_favorable_move_atr=0.90,
        max_adverse_move_atr=0.20,
        config=LabelConfig(setup_quality_min_threshold=None),
    )

    assert payload.setup_quality_score >= 0.55
    assert payload.opportunity_label == 1
