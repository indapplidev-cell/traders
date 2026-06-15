import json

from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)


def test_failed_candidate_is_not_selected_as_best_when_rejected_exists(tmp_path) -> None:
    summary_path = tmp_path / "eth_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "symbol": "ETHUSDT",
                "interval": "15m",
                "start_date": "2025-01-01",
                "candidate_count": 2,
                "evaluated_candidate_count": 2,
                "failed_candidate_count": 1,
                "accepted_candidate_count": 0,
                "rejected_candidate_count": 1,
                "best_candidate_config_id": "failed_config",
                "best_candidate_score": 0.0,
                "gap_severity_for_training": "OK",
                "gap_training_safe": True,
                "effective_gap_count_for_training": 0,
                "feature_version_used": "fv3_candle_ta_context",
                "candle_ta_context_features_attached": True,
                "real_feature_diagnostics_used": True,
                "regime_features_attached": True,
                "regime_label_builder_status": {
                    "regime_label_builder_used_in_training": True,
                },
                "regime_specific_training_applied": True,
                "candidate_results": [
                    {
                        "config_id": "failed_config",
                        "candidate_status": "FAILED",
                        "score": 0.0,
                        "failed_gates": [],
                        "passed_gates": [],
                        "warnings": ["runtime failure"],
                    },
                    {
                        "config_id": "rejected_config",
                        "candidate_status": "REJECTED",
                        "score": -3.5,
                        "failed_gates": ["collapse_gate"],
                        "passed_gates": ["gap_quality_gate"],
                        "model_accuracy": 0.35,
                        "baseline_accuracy": 0.36,
                    },
                ],
                "configs_ranked": [
                    {
                        "config_id": "failed_config",
                        "candidate_status": "FAILED",
                        "score": 0.0,
                    },
                    {
                        "config_id": "rejected_config",
                        "candidate_status": "REJECTED",
                        "score": -3.5,
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])

    assert result["best_candidate_config_id"] == "rejected_config"
    assert result["best_symbol"] == "ETHUSDT"

    symbol_result = result["symbol_results"][0]
    assert symbol_result["best_candidate_config_id"] == "rejected_config"
    assert symbol_result["candidate_status"] == "REJECTED"

    ranked = result["configs_ranked"]
    assert ranked[0]["config_id"] == "rejected_config"
    assert ranked[0]["excluded_from_best_selection"] is False
    assert ranked[1]["config_id"] == "failed_config"
    assert ranked[1]["excluded_from_best_selection"] is True


def test_all_failed_candidates_do_not_create_best_candidate(tmp_path) -> None:
    summary_path = tmp_path / "failed_only_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "symbol": "ETHUSDT",
                "interval": "15m",
                "start_date": "2025-01-01",
                "candidate_count": 1,
                "evaluated_candidate_count": 1,
                "failed_candidate_count": 1,
                "accepted_candidate_count": 0,
                "rejected_candidate_count": 0,
                "best_candidate_config_id": "failed_config",
                "best_candidate_score": 0.0,
                "gap_severity_for_training": "OK",
                "gap_training_safe": True,
                "effective_gap_count_for_training": 0,
                "feature_version_used": "fv3_candle_ta_context",
                "candidate_results": [
                    {
                        "config_id": "failed_config",
                        "candidate_status": "FAILED",
                        "score": 0.0,
                    },
                ],
                "configs_ranked": [
                    {
                        "config_id": "failed_config",
                        "candidate_status": "FAILED",
                        "score": 0.0,
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])

    assert result["best_symbol"] is None
    assert result["best_candidate_config_id"] is None
    assert result["best_candidate_score"] is None

    symbol_result = result["symbol_results"][0]
    assert symbol_result["best_candidate_config_id"] is None
    assert symbol_result["best_candidate_score"] is None
