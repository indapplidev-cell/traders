from app.experiments.ml38_2_config_ranker import ML382ConfigRanker


def test_ml38_6_ranker_prioritizes_confidence_profitability_without_accepting() -> None:
    payload = ML382ConfigRanker().rank(
        [
            {
                "config_id": "weak_cp",
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
                "confidence_profitability_score": -5.0,
                "confidence_profitability_status": "WEAK",
                "flat_bias_diagnostics": {
                    "flat_bias_detected": True,
                    "down_blindness_detected": True,
                    "symbol_bias_severity": "CRITICAL",
                },
                "collapse_tuning_summary": {"collapse_type": "LOW_MARGIN"},
            },
            {
                "config_id": "better_cp",
                "candidate_status": "REJECTED",
                "walk_forward_profit_factor": 1.03,
                "walk_forward_total_r": 15.0,
                "model_accuracy": 0.34,
                "baseline_accuracy": 0.35,
                "passed_gates": ["profit_aware_gate"],
                "failed_gates": ["collapse_gate"],
                "collapse_detected": True,
                "anti_collapse_score": 4.0,
                "anti_collapse_status": "GOOD",
                "confidence_profitability_score": 6.0,
                "confidence_profitability_status": "GOOD",
                "flat_bias_diagnostics": {
                    "flat_bias_detected": False,
                    "down_blindness_detected": False,
                    "symbol_bias_severity": "OK",
                },
                "collapse_tuning_summary": {"collapse_type": "LOW_MARGIN"},
            },
        ]
    )

    assert payload["ranking"][0]["config_id"] == "better_cp"
    assert payload["ranking"][0]["candidate_status"] == "REJECTED"
    assert payload["ranking"][0]["score_components"]["confidence_profitability_bonus"] == 2.0
    assert payload["model_accepted"] is False
