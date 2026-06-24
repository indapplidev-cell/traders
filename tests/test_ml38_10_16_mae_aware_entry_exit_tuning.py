from app.diagnostics.entry_path_quality_filter import EntryPathQualityFilter
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
import run_fv3_cached_tuning


def test_ml38_10_16_mae_aware_profile_penalizes_opposed_wicky_setup() -> None:
    filter_ = EntryPathQualityFilter()
    feature_names = [
        "alt_pullback_long_score",
        "alt_indicator_confluence_long_score",
        "nison_expected_followthrough_score",
        "schwager_invalidation_quality_score",
        "alt_no_trade_chop_score",
        "schwager_bull_trap_risk_score",
        "path_12_upper_wick_pressure",
        "volume_16_exhaustion_score",
    ]

    result = filter_.score_rows(
        feature_names=feature_names,
        feature_rows=[
            [0.88, 0.82, 0.78, 0.74, 0.08, 0.05, 0.08, 0.05],
            [0.05, 0.05, 0.12, 0.15, 0.75, 0.88, 0.90, 0.80],
        ],
        setup_quality_scores=[0.84, 0.42],
        expected_move_atr=[1.50, 0.65],
        invalidation_distance_atr=[0.85, 1.35],
        predicted_labels=["UP", "UP"],
        score_profile="mae_aware_rr_v3",
    )

    first, second = result["score_rows"]
    assert result["diagnostic_version"] == "ml38.10.16"
    assert result["score_profile"] == "mae_aware_rr_v3"
    assert first["mae_pressure_risk_score"] < second["mae_pressure_risk_score"]
    assert first["rr_adjusted_entry_score"] > second["rr_adjusted_entry_score"]
    assert first["entry_path_quality_score"] > second["entry_path_quality_score"]


def test_ml38_10_16_profit_audit_counts_high_mae_pressure_blocks() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    rows = [
        {
            "predicted_label": "UP",
            "entry_path_original_predicted_label": "UP",
            "entry_path_filtered_predicted_label": "UP",
            "actual_label": "UP",
            "prob_up": 0.80,
            "prob_down": 0.10,
            "prob_flat": 0.10,
            "confidence": 0.80,
            "current_close": 100.0,
            "atr_14": 1.0,
            "future_candles": [{"high": 101.6, "low": 99.4}],
            "future_move_atr": 1.0,
            "entry_path_filter_enabled": True,
            "entry_path_filter_blocked": False,
            "entry_path_filter_block_reason": None,
            "entry_path_filter_threshold": 0.68,
            "entry_path_filter_stop_threshold": 0.47,
            "entry_path_filter_mae_threshold": 0.55,
            "entry_path_quality_score": 0.78,
            "stop_pressure_risk_score": 0.20,
            "mae_pressure_risk_score": 0.20,
        },
        {
            "predicted_label": "FLAT",
            "entry_path_original_predicted_label": "UP",
            "entry_path_filtered_predicted_label": "FLAT",
            "actual_label": "FLAT",
            "prob_up": 0.80,
            "prob_down": 0.10,
            "prob_flat": 0.10,
            "confidence": 0.80,
            "current_close": 100.0,
            "atr_14": 1.0,
            "future_candles": [{"high": 100.4, "low": 98.6}],
            "future_move_atr": -1.0,
            "entry_path_filter_enabled": True,
            "entry_path_filter_blocked": True,
            "entry_path_filter_block_reason": "high_mae_pressure",
            "entry_path_filter_threshold": 0.68,
            "entry_path_filter_stop_threshold": 0.47,
            "entry_path_filter_mae_threshold": 0.55,
            "entry_path_quality_score": 0.72,
            "stop_pressure_risk_score": 0.40,
            "mae_pressure_risk_score": 0.82,
        },
    ]

    payload = evaluator.evaluate_single_gate(
        predictions=rows,
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.4,
        stop_loss_atr=1.4,
    )
    summary = payload["summary"]["entry_path_prediction_filter_summary"]
    audit = payload["summary"]["stop_pressure_effectiveness_audit"]

    assert summary["diagnostic_version"] == "ml38.10.16"
    assert summary["original_final_signal_count"] == 2
    assert summary["filtered_final_signal_count"] == 1
    assert summary["blocked_final_signal_count"] == 1
    assert summary["blocked_by_high_mae_pressure_count"] == 1
    assert audit["mae_pressure_threshold"] == 0.55
    assert audit["blocked_by_high_mae_pressure_count"] == 1
    assert audit["stream_consistency_ok"] is True


def test_ml38_10_16_matrix_and_runtime_include_lv24_configs() -> None:
    payload = ML382FV3TuningMatrix().build()
    config_ids = {item["config_id"] for item in payload["configs"]}

    assert payload["mae_aware_entry_exit_tuning_stage"] == "ML38.10.16"
    assert "lv24_h08_tts_thr065_sqmask060_epq068_sp047_mae" in config_ids
    assert "lv24_h12_tts_thr065_sqmask060_epq068_sp047_mae" in config_ids
    assert "lv24_h12_tts_thr065_sqmask060_epq070_sp045_mae_rr" in config_ids
    assert "lv24_h08_tts_thr065_sqmask060_epq068_sp047_mae" in run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
    assert "lv24_h12_tts_thr065_sqmask060_epq068_sp047_mae" in run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
