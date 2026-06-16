from app.experiments.ml38_2_config_ranker import ML382ConfigRanker


def test_ml38_5_ranker_adds_anti_collapse_bonus_without_accepting_candidate() -> None:
    payload = ML382ConfigRanker().rank(
        [
            {
                "config_id": "weak_ac",
                "candidate_status": "REJECTED",
                "walk_forward_profit_factor": 0.95,
                "walk_forward_total_r": -10.0,
                "model_accuracy": 0.34,
                "baseline_accuracy": 0.35,
                "passed_gates": [],
                "failed_gates": ["collapse_gate"],
                "collapse_detected": True,
                "anti_collapse_score": 0.0,
                "anti_collapse_status": "WEAK",
                "flat_bias_diagnostics": {
                    "flat_bias_detected": True,
                    "down_blindness_detected": True,
                    "symbol_bias_severity": "CRITICAL",
                },
                "collapse_tuning_summary": {"collapse_type": "mixed"},
            },
            {
                "config_id": "better_ac",
                "candidate_status": "REJECTED",
                "walk_forward_profit_factor": 0.95,
                "walk_forward_total_r": -10.0,
                "model_accuracy": 0.34,
                "baseline_accuracy": 0.35,
                "passed_gates": [],
                "failed_gates": ["collapse_gate"],
                "collapse_detected": True,
                "anti_collapse_score": 4.5,
                "anti_collapse_status": "GOOD",
                "flat_bias_diagnostics": {
                    "flat_bias_detected": True,
                    "down_blindness_detected": True,
                    "symbol_bias_severity": "CRITICAL",
                },
                "collapse_tuning_summary": {"collapse_type": "mixed"},
            },
        ]
    )

    assert payload["ranking"][0]["config_id"] == "better_ac"
    assert payload["ranking"][0]["candidate_status"] == "REJECTED"
    assert payload["ranking"][0]["score_components"]["anti_collapse_bonus"] == 1.5
    assert payload["model_accepted"] is False
