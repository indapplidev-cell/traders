from app.experiments.ml38_2_config_ranker import ML382ConfigRanker


def test_ranker_does_not_select_failed_candidate_as_best() -> None:
    payload = ML382ConfigRanker().rank(
        [
            {
                "config_id": "failed_config",
                "candidate_id": "failed_config",
                "candidate_status": "FAILED",
                "failed_gates": [],
                "passed_gates": [],
                "walk_forward_profit_factor": 10.0,
                "walk_forward_total_r": 1000.0,
                "model_accuracy": 0.99,
                "baseline_accuracy": 0.33,
            },
            {
                "config_id": "rejected_config",
                "candidate_id": "rejected_config",
                "candidate_status": "REJECTED",
                "failed_gates": ["collapse_gate"],
                "passed_gates": ["gap_quality_gate"],
                "walk_forward_profit_factor": 0.9,
                "walk_forward_total_r": -1.0,
                "model_accuracy": 0.34,
                "baseline_accuracy": 0.33,
            },
        ]
    )

    assert payload["best_candidate_config_id"] == "rejected_config"
    assert payload["ranking"][0]["config_id"] == "rejected_config"
    assert payload["ranking"][0]["excluded_from_best_selection"] is False
    assert payload["ranking"][-1]["config_id"] == "failed_config"
    assert payload["ranking"][-1]["excluded_from_best_selection"] is True
    assert payload["ranking"][-1]["score"] == -1_000_000.0


def test_ranker_returns_no_best_when_all_candidates_failed() -> None:
    payload = ML382ConfigRanker().rank(
        [
            {
                "config_id": "failed_config",
                "candidate_id": "failed_config",
                "candidate_status": "FAILED",
                "failed_gates": [],
                "passed_gates": [],
            }
        ]
    )

    assert payload["best_candidate"] is None
    assert payload["best_candidate_config_id"] is None
    assert payload["best_candidate_score"] is None
    assert payload["failed_candidate_count"] == 1
