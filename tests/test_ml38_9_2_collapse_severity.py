from app.diagnostics.collapse_diagnostics_v2 import classify_collapse_severity


def test_collapse_severity_marks_extreme_up_bias_as_critical() -> None:
    result = classify_collapse_severity(
        {
            "collapse_detected": True,
            "collapse_type": "FLAT_UNDERPREDICTION",
            "dominant_class_ratio": 0.91,
            "flat_prediction_rate": 0.0,
            "down_prediction_rate": 0.05,
            "up_prediction_rate": 0.95,
            "actual_distribution": {"DOWN": 0.30, "FLAT": 0.25, "UP": 0.45},
        }
    )

    assert result["collapse_severity"] == "CRITICAL"
    assert result["collapse_gate_failed"] is True


def test_collapse_severity_marks_mild_collapse_as_watch() -> None:
    result = classify_collapse_severity(
        {
            "collapse_detected": True,
            "collapse_type": "MIXED_COLLAPSE",
            "dominant_class_ratio": 0.65,
            "flat_prediction_rate": 0.12,
            "down_prediction_rate": 0.20,
            "up_prediction_rate": 0.68,
            "actual_distribution": {"DOWN": 0.30, "FLAT": 0.25, "UP": 0.45},
        }
    )

    assert result["collapse_severity"] == "WATCH"
    assert result["collapse_gate_failed"] is False
