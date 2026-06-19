from app.diagnostics.calibrated_prediction_decisions import (
    BoundedDecisionCalibrationConfig,
    choose_bounded_calibrated_decisions,
    evaluate_decision_distribution,
)


def test_bounded_calibration_rejects_flat_collapse_and_falls_back_to_raw() -> None:
    actual = ["DOWN"] * 35 + ["FLAT"] * 25 + ["UP"] * 40
    raw = ["DOWN"] * 10 + ["UP"] * 90
    calibrated = ["FLAT"] * 99 + ["DOWN"]

    result = choose_bounded_calibrated_decisions(
        actual_labels=actual,
        raw_predicted_labels=raw,
        calibrated_predicted_labels=calibrated,
        config=BoundedDecisionCalibrationConfig(max_flat_ratio=0.45),
    )

    assert result["selected_decision_source"] == "raw_argmax_fallback_distribution_guard"
    assert result["fallback_reason"] == "calibrated_distribution_guard_failed"
    assert result["calibrated"]["distribution_safe"] is False
    assert any("flat_ratio>" in reason for reason in result["calibrated"]["distribution_rejection_reasons"])


def test_bounded_calibration_falls_back_when_baseline_edge_worse() -> None:
    actual = ["DOWN"] * 30 + ["FLAT"] * 30 + ["UP"] * 40
    raw = ["DOWN"] * 25 + ["FLAT"] * 25 + ["UP"] * 50
    calibrated = ["DOWN"] * 5 + ["FLAT"] * 45 + ["UP"] * 50

    result = choose_bounded_calibrated_decisions(
        actual_labels=actual,
        raw_predicted_labels=raw,
        calibrated_predicted_labels=calibrated,
        config=BoundedDecisionCalibrationConfig(
            max_flat_ratio=0.50,
            require_non_worse_baseline_edge=True,
            baseline_edge_tolerance=0.0,
        ),
    )

    assert result["selected_decision_source"] in {
        "raw_argmax_fallback_baseline_edge_guard",
        "raw_argmax_fallback_distribution_guard",
    }
    assert result["selected"]["baseline_edge"] >= result["calibrated"]["baseline_edge"]


def test_bounded_calibration_can_select_safe_calibrated_decisions() -> None:
    actual = ["DOWN"] * 30 + ["FLAT"] * 30 + ["UP"] * 40
    raw = ["UP"] * 100
    calibrated = ["DOWN"] * 25 + ["FLAT"] * 30 + ["UP"] * 45

    result = choose_bounded_calibrated_decisions(
        actual_labels=actual,
        raw_predicted_labels=raw,
        calibrated_predicted_labels=calibrated,
        config=BoundedDecisionCalibrationConfig(
            max_flat_ratio=0.45,
            max_dominant_class_ratio=0.75,
            min_down_ratio_when_actual_down_high=0.10,
            min_up_ratio_when_actual_up_high=0.10,
        ),
    )

    assert result["selected_decision_source"] == "calibrated_decision_layer"
    assert result["selected"]["distribution_safe"] is True
    assert result["selected"]["baseline_edge"] >= result["raw"]["baseline_edge"]


def test_evaluate_decision_distribution_reports_baseline_edge() -> None:
    actual = ["DOWN", "FLAT", "UP", "UP"]
    predicted = ["DOWN", "UP", "UP", "UP"]

    result = evaluate_decision_distribution(
        actual_labels=actual,
        predicted_labels=predicted,
    )

    assert result["accuracy"] == 0.75
    assert result["baseline_accuracy"] == 0.5
    assert result["baseline_edge"] == 0.25
    assert result["predicted_ratios"]["UP"] == 0.75
