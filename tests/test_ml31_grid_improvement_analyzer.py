import json

from app.experiments.ml31_grid_improvement_analyzer import ML31GridImprovementAnalyzer


def test_ml31_grid_improvement_analyzer_detects_improvement_and_lower_collapse() -> None:
    payload = ML31GridImprovementAnalyzer().analyze(
        current_experiment_summary=_current_summary(),
        current_analysis=_current_analysis(),
        previous_baseline_summary=_previous_analysis(),
    )

    assert payload["overall_improvement_status"] in {"IMPROVED", "PARTIAL_IMPROVEMENT"}
    assert payload["score_delta"] == 1.7
    assert payload["accepted_candidate_improved"] is True
    assert payload["collapse_improved"] is True
    assert payload["baseline_edge_improved"] is True
    assert json.dumps(payload)


def test_ml31_grid_improvement_analyzer_detects_regression() -> None:
    payload = ML31GridImprovementAnalyzer().analyze(
        current_experiment_summary={**_current_summary(), "accepted_candidate_count": 0},
        current_analysis={
            **_current_analysis(),
            "best_candidate_score": -4.5,
            "gate_failure_counts": {
                "collapse_gate": 3,
                "profit_aware_gate": 2,
                "walk_forward_gate": 2,
                "gap_quality_gate": 2,
            },
            "baseline_edge_summary": {
                "above_threshold_count": 0,
                "best_accuracy_edge": 0.002,
            },
        },
        previous_baseline_summary=_previous_analysis(),
    )

    assert payload["overall_improvement_status"] == "REGRESSED"
    assert payload["accepted_candidate_improved"] is False
    assert payload["score_delta"] == -0.8


def test_ml31_grid_improvement_analyzer_handles_missing_previous_data() -> None:
    payload = ML31GridImprovementAnalyzer().analyze(
        current_experiment_summary=_current_summary(),
        current_analysis=_current_analysis(),
        previous_baseline_summary=None,
    )

    assert payload["overall_improvement_status"] == "INSUFFICIENT_COMPARISON_DATA"
    assert payload["previous_experiment_id"] is None
    assert payload["score_delta"] is None


def _current_summary() -> dict:
    return {
        "experiment_id": "ml31_current",
        "config_count": 3,
        "accepted_candidate_count": 1,
        "rejected_candidate_count": 2,
        "best_candidate_config_id": "cfg_best",
        "best_candidate_score": -2.0,
    }


def _current_analysis() -> dict:
    return {
        "experiment_id": "ml31_current",
        "best_candidate_score": -2.0,
        "gate_failure_counts": {
            "collapse_gate": 1,
            "profit_aware_gate": 1,
            "walk_forward_gate": 1,
            "gap_quality_gate": 1,
        },
        "baseline_edge_summary": {
            "above_threshold_count": 1,
            "best_accuracy_edge": 0.012,
        },
        "top_failed_gate": "collapse_gate",
    }


def _previous_analysis() -> dict:
    return {
        "experiment_id": "ml29_previous",
        "accepted_candidate_count": 0,
        "best_candidate_score": -3.7,
        "gate_failure_counts": {
            "collapse_gate": 3,
            "profit_aware_gate": 2,
            "walk_forward_gate": 2,
            "gap_quality_gate": 2,
        },
        "baseline_edge_summary": {
            "above_threshold_count": 0,
            "best_accuracy_edge": 0.003,
        },
    }
