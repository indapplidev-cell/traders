from __future__ import annotations

from app.labels.label_models import LABEL_DOWN, LABEL_UP
from app.labels.opportunity_label_builder import (
    OPPORTUNITY_REASON_SETUP_DIRECTION_CONFLICT,
    OpportunityLabelBuilder,
)


def test_opportunity_builder_rejects_setup_direction_conflict() -> None:
    payload = OpportunityLabelBuilder().build(
        features_json={
            "near_support": True,
            "support_distance_atr": 0.10,
            "nison_bullish_engulfing": 0.90,
        },
        direction_label=LABEL_DOWN,
        tp_before_sl=True,
        future_move_atr=-1.0,
        max_favorable_move_atr=1.25,
        max_adverse_move_atr=0.25,
    )

    assert payload.setup_type != "no_setup"
    assert payload.opportunity_label == 0
    assert payload.opportunity_direction == "NONE"
    assert payload.opportunity_reason == OPPORTUNITY_REASON_SETUP_DIRECTION_CONFLICT


def test_opportunity_builder_accepts_aligned_setup_direction() -> None:
    payload = OpportunityLabelBuilder().build(
        features_json={
            "near_support": True,
            "support_distance_atr": 0.10,
            "nison_bullish_engulfing": 0.90,
        },
        direction_label=LABEL_UP,
        tp_before_sl=True,
        future_move_atr=1.0,
        max_favorable_move_atr=1.25,
        max_adverse_move_atr=0.25,
    )

    assert payload.opportunity_label == 1
    assert payload.opportunity_direction == LABEL_UP
