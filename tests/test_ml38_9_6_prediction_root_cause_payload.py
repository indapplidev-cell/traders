from app.experiments.ml38_2_config_ranker import ML382ConfigRanker
from app.experiments.multi_symbol_feature_regime_analyzer import MultiSymbolFeatureRegimeAnalyzer


def test_multi_symbol_analysis_includes_prediction_root_cause_summary() -> None:
    analyzer = MultiSymbolFeatureRegimeAnalyzer()
    candidates = [
        {
            "symbol": "SOLUSDT",
            "config_id": "synthetic",
            "candidate_status": "REJECTED",
            "prediction_root_cause_audit": {
                "diagnostic_name": "prediction_root_cause_audit",
                "diagnostic_version": "ml38_9_6",
                "warnings": ["actual_down_rows_mapped_to_up"],
                "recommendations": ["Inspect per-actual DOWN probability stats."],
            },
        }
    ]

    summary = analyzer._prediction_root_cause_summary(candidates)

    assert summary["diagnostic_name"] == "prediction_root_cause_summary"
    assert summary["diagnostic_version"] == "ml38_9_6"
    assert summary["available_candidate_count"] == 1
    assert summary["warning_counts"]["actual_down_rows_mapped_to_up"] == 1


def test_ml38_2_ranker_preserves_prediction_root_cause_audit() -> None:
    ranking = ML382ConfigRanker().rank(
        [
            {
                "config_id": "synthetic",
                "candidate_status": "REJECTED",
                "failed_gates": [],
                "passed_gates": [],
                "walk_forward_profit_factor": 0.9,
                "walk_forward_total_r": -0.1,
                "model_accuracy": 0.38,
                "baseline_accuracy": 0.40,
                "baseline_edge": -0.02,
                "baseline_edge_status": "NEGATIVE_EDGE",
                "collapse_detected": False,
                "collapse_severity": "WATCH",
                "flat_bias_diagnostics": {},
                "collapse_tuning_summary": {},
                "anti_collapse_diagnostics": {},
                "confidence_profitability_diagnostics": {},
                "calibrated_decision_diagnostics": {},
                "bounded_calibrated_decision_selection": {},
                "decision_policy_grid_diagnostics": {},
                "prediction_root_cause_audit": {
                    "diagnostic_name": "prediction_root_cause_audit",
                    "diagnostic_version": "ml38_9_6",
                    "warnings": ["actual_down_rows_mapped_to_up"],
                },
            }
        ]
    )

    row = ranking["ranking"][0]

    assert row["prediction_root_cause_audit"]["diagnostic_name"] == "prediction_root_cause_audit"
    assert row["prediction_root_cause_audit"]["warnings"] == ["actual_down_rows_mapped_to_up"]
