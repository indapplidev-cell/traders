import json

from app.experiments.label_grid_candidate_ranker import LabelGridCandidateRanker


def test_label_grid_candidate_ranker_prefers_profitable_non_collapsed_candidate() -> None:
    ranker = LabelGridCandidateRanker()

    payload = ranker.rank(
        [
            {
                "config_id": "bad_cfg",
                "model_version": "ml_bad",
                "candidate_status": "CANDIDATE_REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "accuracy_edge": 0.002,
                "collapse_detected": True,
                "collapse_type": "MIXED_COLLAPSE",
                "profit_factor": 0.91,
                "profit_total_r": -20.0,
                "walk_forward_global_total_r": -4.0,
                "walk_forward_profit_factor": 0.97,
                "gap_severity": "HIGH",
                "failed_gates": ["collapse_gate", "profit_aware_gate"],
            },
            {
                "config_id": "good_cfg",
                "model_version": "ml_good",
                "candidate_status": "CANDIDATE_ACCEPTED_FOR_RESEARCH",
                "quality_status": "QUALITY_APPROVED",
                "accuracy_edge": 0.012,
                "collapse_detected": False,
                "collapse_type": "NONE",
                "profit_factor": 1.12,
                "profit_total_r": 18.0,
                "walk_forward_global_total_r": 7.0,
                "walk_forward_profit_factor": 1.04,
                "gap_severity": "LOW",
                "failed_gates": [],
            },
        ]
    )

    assert payload["experiment_status"] == "COMPLETED_WITH_ACCEPTED_CANDIDATE"
    assert payload["best_candidate"]["config_id"] == "good_cfg"
    assert payload["ranking"][0]["score"] > payload["ranking"][1]["score"]


def test_label_grid_candidate_ranker_marks_all_rejected_when_no_candidate_passes() -> None:
    ranker = LabelGridCandidateRanker()

    payload = ranker.rank(
        [
            {
                "config_id": "cfg_1",
                "candidate_status": "CANDIDATE_REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "accuracy_edge": 0.001,
                "collapse_detected": True,
                "collapse_type": "SINGLE_CLASS_COLLAPSE",
                "profit_factor": 0.9,
                "profit_total_r": -3.0,
                "walk_forward_global_total_r": -1.0,
                "walk_forward_profit_factor": 0.95,
                "gap_severity": "MEDIUM",
                "failed_gates": ["collapse_gate"],
            }
        ]
    )

    assert payload["experiment_status"] == "COMPLETED_NO_ACCEPTED_CANDIDATE"
    assert payload["accepted_candidate_count"] == 0
    assert payload["rejected_candidate_count"] == 1


def test_label_grid_candidate_ranker_scores_are_json_safe() -> None:
    ranker = LabelGridCandidateRanker()

    payload = ranker.rank(
        [
            {
                "config_id": "cfg_json",
                "candidate_status": "CANDIDATE_ACCEPTED_FOR_RESEARCH",
                "quality_status": "QUALITY_APPROVED",
                "accuracy_edge": 0.01,
                "collapse_detected": False,
                "profit_factor": 1.1,
                "profit_total_r": 5.0,
                "walk_forward_global_total_r": 2.0,
                "walk_forward_profit_factor": 1.02,
                "gap_severity": "OK",
                "failed_gates": [],
            }
        ]
    )

    json.dumps(payload, ensure_ascii=False, sort_keys=True)
