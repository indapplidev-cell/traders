from __future__ import annotations

from app.experiments.ml38_2_config_ranker import evaluate_setup_quality_filter


def test_setup_quality_filter_passes_with_strong_two_stage_metrics() -> None:
    payload = evaluate_setup_quality_filter(
        opportunity_precision=0.33,
        opportunity_recall=0.50,
        predicted_trade_rate=0.12,
        actual_trade_rate=0.08,
        predicted_to_actual_trade_rate_ratio=2.0,
        opportunity_false_positive_rate=0.09,
    )

    assert payload == {"passed": True, "reason": "passed"}


def test_setup_quality_filter_fails_when_precision_is_too_low() -> None:
    payload = evaluate_setup_quality_filter(
        opportunity_precision=0.26,
        opportunity_recall=0.50,
        predicted_trade_rate=0.12,
        actual_trade_rate=0.08,
        predicted_to_actual_trade_rate_ratio=2.0,
        opportunity_false_positive_rate=0.09,
    )

    assert payload == {"passed": False, "reason": "precision_below_minimum"}


def test_setup_quality_filter_fails_when_trade_rate_ratio_is_too_high() -> None:
    payload = evaluate_setup_quality_filter(
        opportunity_precision=0.33,
        opportunity_recall=0.50,
        predicted_trade_rate=0.12,
        actual_trade_rate=0.08,
        predicted_to_actual_trade_rate_ratio=3.5,
        opportunity_false_positive_rate=0.09,
    )

    assert payload == {
        "passed": False,
        "reason": "predicted_to_actual_trade_rate_ratio_too_high",
    }
