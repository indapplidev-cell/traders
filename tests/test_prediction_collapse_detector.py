from app.diagnostics.prediction_collapse_detector import PredictionCollapseDetector


def test_collapse_detector_flags_dominant_class_and_no_signal_conditions() -> None:
    detector = PredictionCollapseDetector()
    probability_report = {
        "predicted_direction_ratios": {"UP": 0.95, "DOWN": 0.03, "FLAT": 0.02},
        "avg_prob_up": 0.20,
        "avg_prob_down": 0.10,
        "avg_prob_flat": 0.70,
        "margin_q90": 0.03,
        "top_class_by_threshold": [
            {"threshold": 0.45, "rows_above_threshold": 0, "predicted_direction_counts": {"UP": 0, "DOWN": 0, "FLAT": 0}}
        ],
    }

    result = detector.detect(probability_report)

    assert result["collapse_detected"] is True
    assert result["dominant_class"] == "UP"
    assert "dominant_class_collapse" in result["warnings"]
    assert "no_signal_confidence_collapse" in result["warnings"]
    assert "low_margin_collapse" in result["warnings"]
