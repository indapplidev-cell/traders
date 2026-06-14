from app.experiments.ml38_2_config_ranker import ML382ConfigRanker


def test_ml38_2_config_ranking_penalizes_collapse_and_flat_bias() -> None:
    payload = ML382ConfigRanker().rank(
        [
            {
                "config_id": "stable_cfg",
                "candidate_status": "REJECTED",
                "walk_forward_profit_factor": 1.05,
                "walk_forward_total_r": 10.0,
                "model_accuracy": 0.41,
                "baseline_accuracy": 0.39,
                "passed_gates": ["profit_aware_gate", "walk_forward_gate"],
                "failed_gates": [],
                "collapse_detected": False,
                "flat_bias_diagnostics": {
                    "flat_bias_detected": False,
                    "down_blindness_detected": False,
                    "symbol_bias_severity": "OK",
                },
                "collapse_tuning_summary": {"collapse_type": "none"},
            },
            {
                "config_id": "collapsed_cfg",
                "candidate_status": "REJECTED",
                "walk_forward_profit_factor": 0.93,
                "walk_forward_total_r": -20.0,
                "model_accuracy": 0.35,
                "baseline_accuracy": 0.39,
                "passed_gates": [],
                "failed_gates": ["baseline_edge_gate", "walk_forward_gate"],
                "collapse_detected": True,
                "flat_bias_diagnostics": {
                    "flat_bias_detected": True,
                    "down_blindness_detected": True,
                    "symbol_bias_severity": "CRITICAL",
                },
                "collapse_tuning_summary": {"collapse_type": "mixed"},
            },
        ]
    )

    assert payload["ranking"][0]["config_id"] == "stable_cfg"
    assert payload["ranking"][0]["score"] > payload["ranking"][1]["score"]
    assert payload["ranking"][1]["score_components"]["collapse_penalty"] == -3.0
    assert "flat_bias_detected" in payload["ranking"][1]["rejection_reasons"]
    assert "down_blindness_detected" in payload["ranking"][1]["rejection_reasons"]
