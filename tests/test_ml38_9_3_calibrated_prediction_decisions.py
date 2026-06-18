from app.diagnostics.calibrated_prediction_decisions import CalibratedPredictionDecisions


def test_calibrated_decision_turns_low_margin_argmax_into_flat() -> None:
    rows = [
        {
            "actual_label": "FLAT",
            "predicted_label": "UP",
            "prob_up": 0.39,
            "prob_down": 0.34,
            "prob_flat": 0.27,
        },
        {
            "actual_label": "DOWN",
            "predicted_label": "UP",
            "prob_up": 0.41,
            "prob_down": 0.38,
            "prob_flat": 0.21,
        },
    ]
    report = CalibratedPredictionDecisions().build_report(
        predictions=rows,
        label_config={
            "config_id": "test_cd",
            "decision_calibration_enabled": True,
            "decision_flat_if_max_prob_below": 0.42,
            "decision_flat_if_margin_below": 0.06,
            "decision_min_direction_prob": 0.40,
            "decision_min_up_down_margin": 0.03,
        },
        symbol="SOLUSDT",
        config_id="test_cd",
    )

    assert report["enabled"] is True
    assert report["calibrated_predicted_counts"]["FLAT"] == 2
    assert report["raw_predicted_counts"]["UP"] == 2
    assert report["changed_prediction_count"] == 2


def test_calibrated_decision_keeps_clear_direction() -> None:
    rows = [
        {
            "actual_label": "UP",
            "predicted_label": "UP",
            "prob_up": 0.62,
            "prob_down": 0.22,
            "prob_flat": 0.16,
        }
    ]

    report = CalibratedPredictionDecisions().build_report(
        predictions=rows,
        label_config={
            "config_id": "test_cd",
            "decision_calibration_enabled": True,
            "decision_flat_if_max_prob_below": 0.42,
            "decision_flat_if_margin_below": 0.06,
            "decision_min_direction_prob": 0.40,
            "decision_min_up_down_margin": 0.03,
        },
        symbol="SOLUSDT",
        config_id="test_cd",
    )

    assert report["calibrated_predicted_counts"]["UP"] == 1
    assert report["changed_prediction_count"] == 0
