import json
from pathlib import Path

from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)


def _write_summary(
    root: Path,
    *,
    experiment_id: str,
    symbol: str,
    real_feature_diagnostics_used: bool,
    row_count: int,
    regime_features_attached: bool,
    regime_feature_count: int,
    regime_features_missing_reason: str | None,
    candle_ta_context_features_attached: bool,
    candle_ta_context_feature_count: int,
    candle_ta_context_missing_reason: str | None,
    real_feature_diagnostics_missing_reason: str | None,
) -> Path:
    experiment_dir = root / experiment_id
    experiment_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiment_id": experiment_id,
        "symbol": symbol,
        "interval": "15m",
        "start_date": "2025-01-01",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "candidate_count": 1,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "lv2_h12_thr05_tp15_sl10",
        "best_candidate_score": -1.5,
        "feature_version_used": "fv3_candle_ta_context",
        "real_feature_diagnostics_used": real_feature_diagnostics_used,
        "real_feature_diagnostics_row_count": row_count,
        "real_feature_diagnostics_missing_reason": real_feature_diagnostics_missing_reason,
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "gap_training_safe": True,
        "regime_features_attached": regime_features_attached,
        "regime_feature_count": regime_feature_count,
        "regime_features_missing_reason": regime_features_missing_reason,
        "candle_ta_context_features_attached": candle_ta_context_features_attached,
        "candle_ta_context_feature_count": candle_ta_context_feature_count,
        "candle_ta_context_missing_reason": candle_ta_context_missing_reason,
        "regime_specific_training_applied": True,
        "warnings": [],
        "candidate_results": [
            {
                "config_id": "lv2_h12_thr05_tp15_sl10",
                "candidate_status": "REJECTED",
                "score": -1.5,
                "model_accuracy": 0.40,
                "baseline_accuracy": 0.39,
                "accuracy_edge": 0.01,
                "collapse_detected": True,
                "collapse_type": "MIXED_COLLAPSE",
                "profit_factor": 0.95,
                "profit_total_r": -3.0,
                "walk_forward_profit_factor": 0.96,
                "walk_forward_global_total_r": -5.0,
                "failed_gates": ["collapse_gate"],
                "passed_gates": ["gap_quality_gate"],
                "warnings": [],
                "model_quality_validation_status": "COMPLETED",
            }
        ],
    }
    path = experiment_dir / "feature_regime_experiment_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_ml38_1_multisymbol_analysis_preserves_attachment_counts_and_missing_reasons(
    tmp_path: Path,
) -> None:
    root = tmp_path / "feature_regime_experiments"
    btc = _write_summary(
        root,
        experiment_id="btc_exp",
        symbol="BTCUSDT",
        real_feature_diagnostics_used=True,
        row_count=400,
        regime_features_attached=True,
        regime_feature_count=8,
        regime_features_missing_reason=None,
        candle_ta_context_features_attached=True,
        candle_ta_context_feature_count=170,
        candle_ta_context_missing_reason=None,
        real_feature_diagnostics_missing_reason=None,
    )
    eth = _write_summary(
        root,
        experiment_id="eth_exp",
        symbol="ETHUSDT",
        real_feature_diagnostics_used=False,
        row_count=0,
        regime_features_attached=False,
        regime_feature_count=0,
        regime_features_missing_reason="regime_data_unavailable",
        candle_ta_context_features_attached=False,
        candle_ta_context_feature_count=0,
        candle_ta_context_missing_reason="fv3_candle_ta_context_rows_unavailable",
        real_feature_diagnostics_missing_reason="dataset_rows_unavailable",
    )

    payload = MultiSymbolFeatureRegimeAnalyzer().analyze([btc, eth])

    eth_summary = next(item for item in payload["symbol_results"] if item["symbol"] == "ETHUSDT")
    assert eth_summary["candle_ta_context_feature_count"] == 0
    assert eth_summary["candle_ta_context_missing_reason"] == "fv3_candle_ta_context_rows_unavailable"
    assert eth_summary["real_feature_diagnostics_missing_reason"] == "dataset_rows_unavailable"
    assert eth_summary["regime_feature_count"] == 0
    assert eth_summary["regime_features_missing_reason"] == "regime_data_unavailable"
    assert payload["regime_integration_summary"]["candle_ta_context_missing_reason_by_symbol"]["ETHUSDT"] == (
        "fv3_candle_ta_context_rows_unavailable"
    )
    assert payload["real_feature_diagnostics_summary"]["missing_reason_by_symbol"]["ETHUSDT"] == (
        "dataset_rows_unavailable"
    )
