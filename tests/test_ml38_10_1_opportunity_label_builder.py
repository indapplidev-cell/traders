from app.labels.label_models import LABEL_FLAT, LABEL_UP
from app.labels.opportunity_label_builder import (
    OPPORTUNITY_REASON_NO_SETUP,
    OpportunityLabelBuilder,
)


def test_opportunity_label_builder_marks_clear_long_setup() -> None:
    payload = OpportunityLabelBuilder().build(
        features_json={
            "nison_bullish_engulfing": 0.92,
            "near_support": True,
            "support_distance_atr": 0.10,
        },
        direction_label=LABEL_UP,
        tp_before_sl=True,
        future_move_atr=0.90,
        max_favorable_move_atr=1.20,
        max_adverse_move_atr=0.25,
    )

    assert payload.opportunity_label == 1
    assert payload.opportunity_direction == LABEL_UP
    assert payload.opportunity_reason in {"setup_first_touch_long", "strong_confluence_long"}
    assert payload.setup_type != "no_setup"
    assert payload.setup_quality_score >= 0.55


def test_opportunity_label_builder_keeps_no_setup_as_no_trade() -> None:
    payload = OpportunityLabelBuilder().build(
        features_json={},
        direction_label=LABEL_FLAT,
        tp_before_sl=None,
        future_move_atr=0.04,
        max_favorable_move_atr=0.15,
        max_adverse_move_atr=0.10,
    )

    assert payload.opportunity_label == 0
    assert payload.opportunity_direction == "NONE"
    assert payload.opportunity_reason == OPPORTUNITY_REASON_NO_SETUP
