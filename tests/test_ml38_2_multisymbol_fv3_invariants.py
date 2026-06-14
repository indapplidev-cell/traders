import json
from pathlib import Path

from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)


def _write_summary(root: Path, symbol: str, config_id: str, score: float) -> Path:
    experiment_dir = root / f"{symbol.lower()}_ml38_2"
    experiment_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment_id": f"{symbol.lower()}_ml38_2",
        "symbol": symbol,
        "interval": "15m",
        "start_date": "2025-01-01",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "candidate_count": 1,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": config_id,
        "best_candidate_score": score,
        "feature_version_used": "fv3_candle_ta_context",
        "real_feature_diagnostics_used": True,
        "real_feature_diagnostics_row_count": 123,
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "gap_training_safe": True,
        "regime_features_attached": True,
        "regime_feature_count": 8,
        "candle_ta_context_features_attached": True,
        "candle_ta_context_feature_count": 170,
        "candidate_status": "REJECTED",
        "model_quality_validation_status": "COMPLETED",
        "candidate_results": [
            {
                "config_id": config_id,
                "candidate_status": "REJECTED",
                "score": score,
                "model_accuracy": 0.35,
                "baseline_accuracy": 0.34,
                "accuracy_edge": 0.01,
                "collapse_detected": True,
                "collapse_type": "MIXED_COLLAPSE",
                "flat_bias_detected": True,
                "down_blindness_detected": False,
                "symbol_bias_severity": "HIGH",
                "collapse_tuning_summary": {"collapse_type": "flat_bias"},
                "predicted_class_distribution": {"DOWN": 0.12, "FLAT": 0.51, "UP": 0.37},
                "actual_class_distribution": {"DOWN": 0.36, "FLAT": 0.24, "UP": 0.40},
                "profit_factor": 0.95,
                "profit_total_r": -5.0,
                "walk_forward_profit_factor": 0.97,
                "walk_forward_global_total_r": -10.0,
                "failed_gates": ["collapse_gate"],
                "passed_gates": ["gap_quality_gate"],
            }
        ],
        "configs_ranked": [
            {
                "rank": 1,
                "config_id": config_id,
                "candidate_status": "REJECTED",
                "score": score,
            }
        ],
        "reasons_why_best_still_rejected": ["collapse_type=flat_bias"],
    }
    path = experiment_dir / "feature_regime_experiment_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ml38_2_multisymbol_fv3_invariants_hold_for_btc_eth_sol(tmp_path: Path) -> None:
    root = tmp_path / "feature_regime_experiments"
    paths = [
        _write_summary(root, "BTCUSDT", "lv2_h08_thr03_tp10_sl10", -1.0),
        _write_summary(root, "ETHUSDT", "lv2_h12_thr04_tp15_sl10", -2.0),
        _write_summary(root, "SOLUSDT", "lv2_h16_thr05_tp20_sl10", -3.0),
    ]

    payload = MultiSymbolFeatureRegimeAnalyzer().analyze(paths)

    assert payload["feature_version_summary"]["all_feature_version_fv3_candle_ta_context"] is True
    assert payload["real_feature_diagnostics_summary"]["all_real_feature_diagnostics_used"] is True
    assert payload["regime_integration_summary"]["symbols_missing_regime_features"] == []
    assert payload["regime_integration_summary"]["symbols_missing_candle_ta_context_features"] == []
    assert payload["best_config_by_symbol"]["BTCUSDT"] == "lv2_h08_thr03_tp10_sl10"
    assert payload["best_global_config"] == "lv2_h08_thr03_tp10_sl10"
