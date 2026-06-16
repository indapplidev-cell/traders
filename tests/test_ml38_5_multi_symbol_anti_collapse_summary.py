import json

from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)


def test_ml38_5_multi_symbol_summary_contains_anti_collapse_block(tmp_path) -> None:
    summary_path = tmp_path / "btc_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "symbol": "BTCUSDT",
                "interval": "15m",
                "start_date": "2025-01-01",
                "candidate_count": 2,
                "evaluated_candidate_count": 2,
                "failed_candidate_count": 0,
                "accepted_candidate_count": 0,
                "rejected_candidate_count": 2,
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
                        "config_id": "lv3_h04_thr02_tp08_sl08_ac",
                        "candidate_status": "REJECTED",
                        "score": -1.0,
                        "failed_gates": ["collapse_gate"],
                        "passed_gates": ["gap_quality_gate"],
                        "anti_collapse_score": 4.5,
                        "anti_collapse_status": "GOOD",
                    },
                    {
                        "config_id": "lv2_h08_thr03_tp10_sl10",
                        "candidate_status": "REJECTED",
                        "score": -3.0,
                        "failed_gates": ["collapse_gate"],
                        "passed_gates": ["gap_quality_gate"],
                        "anti_collapse_score": 0.0,
                        "anti_collapse_status": "WEAK",
                    },
                ],
                "configs_ranked": [
                    {
                        "config_id": "lv3_h04_thr02_tp08_sl08_ac",
                        "candidate_status": "REJECTED",
                        "score": -1.0,
                        "anti_collapse_score": 4.5,
                        "anti_collapse_status": "GOOD",
                    },
                    {
                        "config_id": "lv2_h08_thr03_tp10_sl10",
                        "candidate_status": "REJECTED",
                        "score": -3.0,
                        "anti_collapse_score": 0.0,
                        "anti_collapse_status": "WEAK",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])

    summary = result["anti_collapse_summary"]
    assert summary["diagnostic_version"] == "ml38_5"
    assert summary["good_count"] == 1
    assert summary["weak_count"] == 1
    assert summary["best_by_symbol"]["BTCUSDT"]["config_id"] == "lv3_h04_thr02_tp08_sl08_ac"
