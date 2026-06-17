import json

from app.experiments.multi_symbol_feature_regime_analyzer import MultiSymbolFeatureRegimeAnalyzer


def test_ml38_6_multi_symbol_summary_contains_confidence_profitability_block(tmp_path) -> None:
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
                "configs_ranked": [
                    {
                        "config_id": "lv4_h06_thr035_tp12_sl08_cp",
                        "candidate_status": "REJECTED",
                        "score": 2.0,
                        "confidence_profitability_score": 6.0,
                        "confidence_profitability_status": "GOOD",
                        "confidence_profitability_diagnostics": {
                            "margin_q50": 0.04,
                            "margin_q90": 0.08,
                            "max_prob_q90": 0.48,
                            "rows_above_045": 120,
                        },
                        "walk_forward_profit_factor": 1.03,
                        "walk_forward_total_r": 15.0,
                    },
                    {
                        "config_id": "lv2_h08_thr03_tp10_sl10",
                        "candidate_status": "REJECTED",
                        "score": -4.0,
                        "confidence_profitability_score": -3.0,
                        "confidence_profitability_status": "WEAK",
                    },
                ],
                "candidate_results": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])

    summary = result["confidence_profitability_summary"]
    assert summary["diagnostic_version"] == "ml38_6"
    assert summary["good_count"] == 1
    assert summary["weak_count"] == 1
    assert summary["best_by_symbol"]["BTCUSDT"]["config_id"] == "lv4_h06_thr035_tp12_sl08_cp"
    assert summary["accepts_candidate"] is False
    assert summary["softens_gates"] is False
