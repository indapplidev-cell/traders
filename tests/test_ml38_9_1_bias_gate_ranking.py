from app.experiments.ml38_2_config_ranker import ML382ConfigRanker


def test_ml38_9_1_ranker_penalizes_bias_gate_and_reports_reasons() -> None:
    payload = ML382ConfigRanker().rank(
        [
            {
                "config_id": "lv6_h12_thr06_tp12_sl12_ba",
                "candidate_status": "REJECTED",
                "model_accuracy": 0.38,
                "baseline_accuracy": 0.39,
                "walk_forward_profit_factor": 1.0,
                "walk_forward_total_r": 0.2,
                "collapse_detected": True,
                "failed_gates": ["bias_gate", "baseline_edge_gate"],
                "passed_gates": ["gap_quality_gate"],
                "flat_bias_diagnostics": {
                    "symbol_bias_severity": "CRITICAL",
                    "bias_gate_failed": True,
                    "flat_underprediction_detected": True,
                    "down_blindness_detected": True,
                    "up_dominance_detected": True,
                    "bias_rejection_reasons": [
                        "flat_underprediction_detected",
                        "down_blindness_detected",
                        "up_dominance_detected",
                    ],
                },
            }
        ]
    )

    row = payload["ranking"][0]
    assert row["candidate_status"] == "REJECTED"
    assert row["score_components"]["bias_gate_penalty"] < 0
    assert row["score_components"]["up_dominance_penalty"] < 0
    assert row["score_components"]["flat_underprediction_penalty"] < 0
    assert "bias_gate_failed" in row["rejection_reasons"]
    assert "up_dominance_detected" in row["rejection_reasons"]
