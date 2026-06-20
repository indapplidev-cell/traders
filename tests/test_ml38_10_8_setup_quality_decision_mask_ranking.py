from __future__ import annotations

from app.experiments.ml38_2_config_ranker import ML382ConfigRanker


def test_ranker_rewards_masked_precision_control_but_does_not_auto_accept_candidate() -> None:
    good_candidate = {
        "config_id": "lv19_h08_tts_thr065_sqmask060",
        "candidate_status": "REJECTED",
        "training_objective": "trade_two_stage",
        "failed_gates": ["profit_aware_gate"],
        "passed_gates": ["collapse_gate"],
        "baseline_edge": 0.02,
        "collapse_severity": "OK",
        "opportunity_precision": 0.32,
        "opportunity_recall": 0.50,
        "opportunity_f1": 0.39,
        "predicted_trade_rate": 0.12,
        "actual_trade_rate": 0.08,
        "predicted_to_actual_trade_rate_ratio": 1.5,
        "opportunity_false_positive_rate": 0.05,
        "direction_accuracy_on_trade_rows": 0.55,
        "two_stage_trade_diagnostics": {
            "warnings": [],
            "precision_control_passed": True,
            "precision_control_gates": {
                "min_precision": 0.30,
                "min_recall": 0.45,
                "max_predicted_trade_rate": 0.15,
                "max_predicted_to_actual_trade_rate_ratio": 2.5,
                "max_false_positive_rate": 0.12,
            },
            "setup_quality_bucket_metrics_after_mask": {
                "missing_or_zero": {"row_count": 3, "false_positive_count": 0},
                "low_0_00_0_40": {"row_count": 4, "false_positive_count": 0},
                "mid_0_40_0_60": {"row_count": 2, "false_positive_count": 0},
            },
            "setup_quality_decision_mask_summary": {
                "enabled": True,
                "forced_no_trade_count": 1,
            },
        },
    }
    bad_candidate = {
        "config_id": "lv19_h12_tts_thr070_sqmask065",
        "candidate_status": "REJECTED",
        "training_objective": "trade_two_stage",
        "failed_gates": ["profit_aware_gate"],
        "passed_gates": [],
        "baseline_edge": 0.02,
        "collapse_severity": "OK",
        "opportunity_precision": 0.20,
        "opportunity_recall": 0.30,
        "opportunity_f1": 0.24,
        "predicted_trade_rate": 0.18,
        "actual_trade_rate": 0.06,
        "predicted_to_actual_trade_rate_ratio": 3.2,
        "opportunity_false_positive_rate": 0.18,
        "direction_accuracy_on_trade_rows": 0.48,
        "two_stage_trade_diagnostics": {
            "warnings": [
                "opportunity_precision_below_gate",
                "predicted_trade_rate_above_gate",
            ],
            "precision_control_passed": False,
            "precision_control_gates": {
                "min_precision": 0.30,
                "min_recall": 0.45,
                "max_predicted_trade_rate": 0.15,
                "max_predicted_to_actual_trade_rate_ratio": 2.5,
                "max_false_positive_rate": 0.12,
            },
            "setup_quality_bucket_metrics_after_mask": {
                "missing_or_zero": {"row_count": 3, "false_positive_count": 2},
                "low_0_00_0_40": {"row_count": 4, "false_positive_count": 2},
                "mid_0_40_0_60": {"row_count": 2, "false_positive_count": 1},
            },
            "setup_quality_decision_mask_summary": {
                "enabled": True,
                "forced_no_trade_count": 4,
            },
        },
    }

    ranking_payload = ML382ConfigRanker().rank([bad_candidate, good_candidate])
    ranking = ranking_payload["ranking"]

    assert ranking[0]["config_id"] == "lv19_h08_tts_thr065_sqmask060"
    assert ranking[0]["score"] > ranking[1]["score"]
    assert ranking[0]["candidate_status"] == "REJECTED"
    assert ranking_payload["accepted_candidate_count"] == 0
    assert ranking_payload["model_accepted"] is False
