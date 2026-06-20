from __future__ import annotations

from app.experiments.ml38_2_config_ranker import ML382ConfigRanker


def _base_candidate() -> dict:
    return {
        "candidate_status": "REJECTED",
        "training_objective": "trade_two_stage",
        "failed_gates": ["profit_aware_gate"],
        "passed_gates": ["collapse_gate"],
        "baseline_edge": 0.02,
        "collapse_severity": "OK",
        "direction_accuracy_on_trade_rows": 1.0,
    }


def test_ranker_prefers_balanced_two_stage_candidate_over_precision_trap() -> None:
    balanced = {
        **_base_candidate(),
        "config_id": "lv19_h12_tts_thr065_sqmask060",
        "opportunity_precision": 0.3113,
        "opportunity_recall": 0.5789,
        "opportunity_f1": 0.4049,
        "predicted_trade_rate": 0.1089,
        "actual_trade_rate": 0.0586,
        "predicted_to_actual_trade_rate_ratio": 1.86,
        "opportunity_false_positive_rate": 0.0797,
        "direction_trade_rows": 65,
        "two_stage_trade_diagnostics": {
            "two_stage_quality_gate_passed": True,
            "anti_undertrading_gate_passed": True,
            "setup_quality_bucket_metrics_after_mask": {
                "missing_or_zero": {"row_count": 748, "false_positive_count": 0},
            },
            "setup_quality_decision_mask_summary": {"enabled": True, "forced_no_trade_count": 18},
        },
    }
    precision_trap = {
        **_base_candidate(),
        "config_id": "lv18_h12_tts_thr065_sq060_precision_trap",
        "opportunity_precision": 1.0,
        "opportunity_recall": 0.0233,
        "opportunity_f1": 0.0455,
        "predicted_trade_rate": 0.0017,
        "actual_trade_rate": 0.0703,
        "predicted_to_actual_trade_rate_ratio": 0.02,
        "opportunity_false_positive_rate": 0.0,
        "direction_trade_rows": 1,
        "two_stage_trade_diagnostics": {
            "two_stage_quality_gate_passed": False,
            "anti_undertrading_gate_passed": False,
            "setup_quality_bucket_metrics_after_mask": {
                "missing_or_zero": {"row_count": 700, "false_positive_count": 0},
            },
            "setup_quality_decision_mask_summary": {"enabled": True, "forced_no_trade_count": 120},
        },
    }

    payload = ML382ConfigRanker().rank([precision_trap, balanced])
    best = payload["best_candidate"]

    assert best["config_id"] == "lv19_h12_tts_thr065_sqmask060"
    assert best["two_stage_quality_gate_passed"] is True
    assert best["anti_undertrading_gate_passed"] is True
    assert payload["accepted_candidate_count"] == 0
    assert payload["model_accepted"] is False

    trap_row = next(
        row for row in payload["ranking"] if row["config_id"] == "lv18_h12_tts_thr065_sq060_precision_trap"
    )
    assert trap_row["undertrading_risk_detected"] is True
    assert trap_row["score_components"]["precision_trap_penalty"] < 0
