from app.experiments.multi_symbol_feature_regime_analyzer import MultiSymbolFeatureRegimeAnalyzer
from app.experiments.multi_symbol_feature_regime_reporter import MultiSymbolFeatureRegimeReporter


def test_ml38_10_14_3_symbol_result_exposes_entry_path_audit_from_best_candidate() -> None:
    summary = {
        "symbol": "SOLUSDT",
        "experiment_id": "exp1",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "candidate_count": 1,
        "evaluated_candidate_count": 1,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "feature_version_used": "fv4_book_setup_context",
        "gap_severity_for_training": "NONE",
        "gap_training_safe": True,
        "candidate_results": [
            {
                "config_id": "lv22_h12_tts_thr065_sqmask060_epq070_sp045",
                "candidate_status": "REJECTED",
                "score": 1.5,
                "failed_gates": ["profit_aware_gate"],
                "passed_gates": [],
                "entry_path_quality_filter_enabled": True,
                "entry_path_quality_min_threshold": 0.70,
                "stop_pressure_max_risk_score": 0.45,
                "entry_path_prediction_filter_summary": {
                    "diagnostic_version": "ml38.10.14.3",
                    "audit_stream": "final_profit_aware_gate_signal_stream",
                    "original_final_signal_count": 10,
                    "filtered_final_signal_count": 7,
                    "blocked_final_signal_count": 3,
                    "stream_consistency_ok": True,
                    "stop_pressure_effectiveness_audit": {
                        "diagnostic_version": "ml38.10.14.3",
                        "status": "STOP_PRESSURE_REMOVED_FALSE_SIGNALS",
                    },
                },
            }
        ],
        "configs_ranked": [
            {
                "config_id": "lv22_h12_tts_thr065_sqmask060_epq070_sp045",
                "candidate_status": "REJECTED",
                "score": 1.5,
                "failed_gates": ["profit_aware_gate"],
                "passed_gates": [],
                "entry_path_quality_filter_enabled": True,
                "entry_path_quality_min_threshold": 0.70,
                "stop_pressure_max_risk_score": 0.45,
                "entry_path_prediction_filter_summary": {
                    "diagnostic_version": "ml38.10.14.3",
                    "audit_stream": "final_profit_aware_gate_signal_stream",
                    "original_final_signal_count": 10,
                    "filtered_final_signal_count": 7,
                    "blocked_final_signal_count": 3,
                    "stream_consistency_ok": True,
                    "stop_pressure_effectiveness_audit": {
                        "diagnostic_version": "ml38.10.14.3",
                        "status": "STOP_PRESSURE_REMOVED_FALSE_SIGNALS",
                    },
                },
            }
        ],
    }

    result = MultiSymbolFeatureRegimeAnalyzer._symbol_result(summary)

    assert result["entry_path_quality_filter_enabled"] is True
    assert result["entry_path_quality_min_threshold"] == 0.70
    assert result["stop_pressure_max_risk_score"] == 0.45
    assert result["entry_path_final_signal_original_count"] == 10
    assert result["entry_path_final_signal_filtered_count"] == 7
    assert result["entry_path_final_signal_blocked_count"] == 3
    assert result["entry_path_stream_consistency_ok"] is True
    assert result["stop_pressure_effectiveness_audit"]["status"] == "STOP_PRESSURE_REMOVED_FALSE_SIGNALS"
    assert result["configs_ranked"][0]["entry_path_final_signal_blocked_count"] == 3


def test_ml38_10_14_3_reporter_compact_summary_contains_entry_path_audit() -> None:
    reporter = MultiSymbolFeatureRegimeReporter()
    payload = reporter.compact_summary_to_dict(
        {
            "status": "ok",
            "symbols": ["SOLUSDT"],
            "experiment_count": 1,
            "candidate_count": 1,
            "evaluated_candidate_count": 1,
            "failed_candidate_count": 0,
            "accepted_candidate_count": 0,
            "rejected_candidate_count": 1,
            "best_symbol": "SOLUSDT",
            "best_candidate_config_id": "lv22_h12_tts_thr065_sqmask060_epq070_sp045",
            "best_candidate_score": 1.5,
            "symbol_results": [
                {
                    "symbol": "SOLUSDT",
                    "best_candidate_config_id": "lv22_h12_tts_thr065_sqmask060_epq070_sp045",
                    "entry_path_quality_filter_enabled": True,
                    "entry_path_quality_min_threshold": 0.70,
                    "stop_pressure_max_risk_score": 0.45,
                    "entry_path_final_signal_original_count": 10,
                    "entry_path_final_signal_filtered_count": 7,
                    "entry_path_final_signal_blocked_count": 3,
                    "entry_path_stream_consistency_ok": True,
                    "stop_pressure_effectiveness_audit": {
                        "status": "STOP_PRESSURE_REMOVED_FALSE_SIGNALS",
                    },
                }
            ],
            "configs_ranked": [
                {
                    "symbol": "SOLUSDT",
                    "config_id": "lv22_h12_tts_thr065_sqmask060_epq070_sp045",
                    "entry_path_final_signal_blocked_count": 3,
                }
            ],
        }
    )

    assert payload["configs_ranked"][0]["entry_path_final_signal_blocked_count"] == 3
    assert payload["entry_path_audit_by_symbol"]["SOLUSDT"]["entry_path_final_signal_blocked_count"] == 3
    assert payload["entry_path_audit_by_symbol"]["SOLUSDT"]["stop_pressure_status"] == "STOP_PRESSURE_REMOVED_FALSE_SIGNALS"
