import json

from app.experiments.feature_regime_result_analyzer import FeatureRegimeResultAnalyzer


def test_feature_regime_result_analyzer_better_score_is_improved_or_partial() -> None:
    payload = FeatureRegimeResultAnalyzer().analyze(
        current_result=_current_result(-5.8),
        baseline_result={"experiment_id": "ml31", "best_candidate_score": -6.372101},
    )

    assert payload["overall_status"] in {"FEATURE_REGIME_IMPROVED", "FEATURE_REGIME_PARTIAL"}
    assert payload["score_delta"] > 0
    assert json.dumps(payload)


def test_feature_regime_result_analyzer_worse_score_is_degraded() -> None:
    payload = FeatureRegimeResultAnalyzer().analyze(
        current_result=_current_result(-7.0),
        baseline_result={"experiment_id": "ml31", "best_candidate_score": -6.372101},
    )

    assert payload["overall_status"] == "FEATURE_REGIME_DEGRADED"
    assert payload["score_delta"] < 0


def test_feature_regime_result_analyzer_without_baseline_is_insufficient() -> None:
    payload = FeatureRegimeResultAnalyzer().analyze(
        current_result={k: v for k, v in _current_result(-6.2).items() if k != "baseline_reference"},
        baseline_result=None,
    )

    assert payload["overall_status"] == "INSUFFICIENT_DATA"
    assert payload["feature_weak_signal_detected"] is True
    assert payload["regime_training_applied"] is False


def _current_result(best_score: float) -> dict:
    return {
        "experiment_id": "fr_current",
        "best_candidate_score": best_score,
        "accepted_candidate_count": 0,
        "failed_gates_summary": {
            "collapse_gate": 2,
            "baseline_edge_gate": 1,
            "walk_forward_gate": 2,
            "profit_aware_gate": 1,
        },
        "feature_quality_summary": {"weak_signal_detected": True},
        "regime_feature_summary": {"regime_data_available": True},
        "regime_training_applied": False,
        "baseline_reference": {
            "experiment_id": "ml31",
            "best_candidate_score": -6.372101,
        },
    }
