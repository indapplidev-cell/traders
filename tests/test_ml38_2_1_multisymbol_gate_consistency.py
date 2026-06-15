import json
from pathlib import Path

from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)


def _write_summary(root: Path, symbol: str, config_id: str, score: float) -> Path:
    experiment_dir = root / f"{symbol.lower()}_ml38_2_1"
    experiment_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment_id": f"{symbol.lower()}_ml38_2_1",
        "symbol": symbol,
        "interval": "15m",
        "start_date": "2025-01-01",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "candidate_count": 1,
        "evaluated_candidate_count": 1,
        "failed_candidate_count": 0,
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
                "profit_factor": 0.95,
                "profit_total_r": -5.0,
                "walk_forward_profit_factor": 0.97,
                "walk_forward_global_total_r": -10.0,
                "failed_gates": ["collapse_gate", "gap_quality_gate"],
                "passed_gates": [],
            }
        ],
        "configs_ranked": [
            {
                "rank": 1,
                "config_id": config_id,
                "candidate_status": "REJECTED",
                "score": score,
                "failed_gates": ["collapse_gate", "gap_quality_gate"],
                "passed_gates": [],
            }
        ],
        "reasons_why_best_still_rejected": ["collapse_type=flat_bias"],
    }
    path = experiment_dir / "feature_regime_experiment_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_candidate_level_gap_gate_is_normalized_for_ok_safe_gaps(tmp_path: Path) -> None:
    root = tmp_path / "feature_regime_experiments"
    paths = [_write_summary(root, "BTCUSDT", "lv2_h08_thr03_tp10_sl10", -1.0)]

    payload = MultiSymbolFeatureRegimeAnalyzer().analyze(paths)
    symbol_payload = payload["symbol_results"][0]

    assert symbol_payload["gap_training_safe"] is True
    assert symbol_payload["gap_severity_for_training"] == "OK"
    assert "gap_quality_gate" not in symbol_payload["failed_gates"]
    assert "gap_quality_gate" in symbol_payload["passed_gates"]


def test_multisymbol_gap_gate_consistency_holds_for_all_ok_safe_symbols(tmp_path: Path) -> None:
    root = tmp_path / "feature_regime_experiments"
    paths = [
        _write_summary(root, "BTCUSDT", "lv2_h08_thr03_tp10_sl10", -1.0),
        _write_summary(root, "ETHUSDT", "lv2_h08_thr04_tp10_sl10", -2.0),
        _write_summary(root, "SOLUSDT", "lv2_h08_thr05_tp15_sl10", -3.0),
    ]

    payload = MultiSymbolFeatureRegimeAnalyzer().analyze(paths)

    assert payload["all_gap_training_safe"] is True
    for symbol_payload in payload["symbol_results"]:
        assert "gap_quality_gate" not in symbol_payload["failed_gates"]
