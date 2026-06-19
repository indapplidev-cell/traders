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
