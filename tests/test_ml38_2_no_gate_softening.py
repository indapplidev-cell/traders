from app.experiments.ml38_2_config_ranker import ML382ConfigRanker


def test_ml38_2_no_gate_softening_keeps_walk_forward_and_baseline_failures_visible() -> None:
    payload = ML382ConfigRanker().rank(
        [
            {
                "config_id": "reject_cfg",
                "candidate_status": "REJECTED",
                "walk_forward_profit_factor": 0.92,
                "walk_forward_total_r": -11.0,
                "model_accuracy": 0.34,
                "baseline_accuracy": 0.39,
                "baseline_edge": -0.05,
                "collapse_severity": "CRITICAL",
                "passed_gates": ["gap_quality_gate"],
                "failed_gates": ["collapse_gate", "baseline_edge_gate", "walk_forward_gate"],
                "collapse_detected": True,
                "flat_bias_diagnostics": {
                    "flat_bias_detected": True,
                    "down_blindness_detected": False,
                    "symbol_bias_severity": "HIGH",
                },
                "collapse_tuning_summary": {"collapse_type": "flat_bias"},
            }
        ]
    )

    row = payload["ranking"][0]
    assert row["candidate_status"] == "REJECTED"
    assert "baseline_edge_gate" in row["failed_gates"]
    assert "walk_forward_gate" in row["failed_gates"]
    assert row["score_components"]["baseline_edge_negative_penalty"] == -3.0
    assert row["score_components"]["critical_collapse_penalty"] == -5.0
    assert row["score_components"]["walk_forward_gate_penalty"] == -3.0
