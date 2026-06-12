import json

from app.diagnostics.collapse_diagnostics_v2 import CollapseDiagnosticsV2


def test_collapse_diagnostics_v2_detects_dominant_class_and_flat_underprediction() -> None:
    payload = CollapseDiagnosticsV2().analyze(
        probability_report={
            "actual_direction_counts": {"UP": 350, "DOWN": 280, "FLAT": 370},
            "predicted_direction_counts": {"UP": 910, "DOWN": 60, "FLAT": 30},
            "avg_prob_up": 0.36,
            "avg_prob_down": 0.33,
            "avg_prob_flat": 0.31,
            "max_prob_q50": 0.37,
            "max_prob_q90": 0.39,
            "rows_above_thresholds": {"0.45": 0},
            "margin_q50": 0.02,
            "margin_q90": 0.04,
        },
        symbol="BTCUSDT",
        feature_version="fv2",
        label_version="lv2_h08_thr04_tp10_sl10",
        accuracy_edge=0.02,
        walk_forward_summary={"walk_forward_status": "UNSTABLE"},
    )

    assert payload["collapse_detected"] is True
    assert payload["collapse_type"] == "MIXED_COLLAPSE"
    assert payload["dominant_class"] == "UP"
    assert payload["flat_underprediction_detected"] is True
    assert payload["low_margin_detected"] is True
    assert payload["uniform_probability_detected"] is True
    assert "Increase flat-aware labeling/calibration or add flat threshold diagnostics." in payload["recommendations"]
    assert "Tune class weighting, thresholds, or balanced sampling to reduce dominant-class collapse." in payload["recommendations"]
    assert "Run temporal stability analysis because walk-forward fails despite positive baseline edge." in payload["recommendations"]
    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_collapse_diagnostics_v2_returns_stable_recommendation_when_not_collapsed() -> None:
    payload = CollapseDiagnosticsV2().analyze(
        probability_report={
            "actual_direction_counts": {"UP": 330, "DOWN": 320, "FLAT": 350},
            "predicted_direction_counts": {"UP": 340, "DOWN": 310, "FLAT": 350},
            "avg_prob_up": 0.41,
            "avg_prob_down": 0.30,
            "avg_prob_flat": 0.29,
            "max_prob_q50": 0.44,
            "max_prob_q90": 0.61,
            "rows_above_thresholds": {"0.45": 180},
            "margin_q50": 0.06,
            "margin_q90": 0.18,
        },
        symbol="ETHUSDT",
        feature_version="fv2",
        label_version="lv2_h12_thr05_tp15_sl10",
    )

    assert payload["collapse_detected"] is False
    assert payload["collapse_type"] == "NONE"
    assert payload["recommendations"] == ["Collapse profile looks stable enough for research review."]
