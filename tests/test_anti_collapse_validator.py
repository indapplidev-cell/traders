import json

from app.evaluation.anti_collapse_validator import AntiCollapseValidator


def test_anti_collapse_validator_detects_bad_run_collapse() -> None:
    payload = AntiCollapseValidator().validate(
        actual_class_counts={"UP": 3661, "DOWN": 3787, "FLAT": 2449},
        predicted_class_counts={"UP": 8516, "DOWN": 421, "FLAT": 960},
        avg_prob_up=0.3505,
        avg_prob_down=0.3243,
        avg_prob_flat=0.3252,
        confidence_stats={"q90": 0.3655, "rows_above_0_45": 0},
        margin_stats={"q90": 0.0431, "q50": 0.0201},
    )

    assert payload["collapse_detected"] is True
    assert payload["directional_bias_detected"] is True
    assert payload["low_margin_detected"] is True
    assert payload["collapse_type"] != "NONE"
    assert "directional_bias_warning" in payload["warnings"]
    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_anti_collapse_validator_accepts_balanced_distribution() -> None:
    payload = AntiCollapseValidator().validate(
        actual_class_counts={"UP": 300, "DOWN": 320, "FLAT": 180},
        predicted_class_counts={"UP": 290, "DOWN": 305, "FLAT": 205},
        avg_prob_up=0.36,
        avg_prob_down=0.34,
        avg_prob_flat=0.30,
        confidence_stats={"q90": 0.49, "rows_above_0_45": 120},
        margin_stats={"q90": 0.08, "q50": 0.05},
    )

    assert payload["collapse_detected"] is False
    assert payload["collapse_type"] == "NONE"
