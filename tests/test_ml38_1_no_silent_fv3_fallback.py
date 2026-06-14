import json
from pathlib import Path

from app.experiments.feature_regime_experiment_runner import (
    FeatureRegimeCandidateResult,
    FeatureRegimeExperimentConfig,
    FeatureRegimeExperimentRunner,
)


def test_ml38_1_summary_exposes_explicit_missing_reasons_when_fv3_attachment_is_missing(
    tmp_path: Path,
) -> None:
    runner = FeatureRegimeExperimentRunner()
    runner._select_base_configs = lambda config: [  # type: ignore[method-assign]
        {
            "config_id": "lv2_h12_thr05_tp15_sl10",
            "label_version": "lv2_h12_thr05_tp15_sl10",
            "horizon": 12,
            "threshold": 0.5,
            "take_profit_atr": 1.5,
            "stop_loss_atr": 1.0,
        }
    ]
    runner._select_regime_configs = lambda config, selected: [  # type: ignore[method-assign]
        {"config_id": "regime_preview"}
    ]
    runner._collect_diagnostics = lambda config, selected_base_configs, logger: {  # type: ignore[method-assign]
        "feature_quality_summary": {"weak_signal_detected": False},
        "feature_group_quality_summary": {"groups": []},
        "regime_feature_summary": {"regime_data_available": False, "warnings": ["regime_data_unavailable"]},
        "feature_leakage_summary": {"leakage_risk_detected": False},
        "regime_experiment_plan_summary": {"ready_for_real_regime_training": False, "recommendations": []},
        "real_feature_diagnostics": {"row_count": 0, "candle_ta_context_features_attached": False},
        "regime_label_builder_status": {
            "regime_label_builder_status": "blocked",
            "regime_label_builder_used_in_training": False,
            "regime_specific_training_applied": False,
            "missing_requirements": ["regime_runtime_labels_not_built"],
        },
        "real_feature_diagnostics_used": False,
        "real_feature_diagnostics_row_count": 0,
        "regime_features_attached": False,
        "regime_feature_count": 8,
        "regime_features_missing_reason": "regime_data_unavailable",
        "candle_ta_context_features_attached": False,
        "candle_ta_context_feature_count": 0,
        "candle_ta_context_missing_reason": "fv3_candle_ta_context_rows_unavailable",
        "regime_feature_source": "runtime_context",
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "gap_training_safe": True,
        "warnings": ["dataset_rows_unavailable"],
        "real_feature_diagnostics_missing_reason": "dataset_rows_unavailable",
    }
    runner._sample_candidates = lambda *args, **kwargs: [  # type: ignore[method-assign]
        FeatureRegimeCandidateResult(
            candidate_id="lv2_h12_thr05_tp15_sl10",
            config_id="lv2_h12_thr05_tp15_sl10",
            label_config={"label_version": "lv2_h12_thr05_tp15_sl10"},
            status="COMPLETED",
            quality_status="QUALITY_REJECTED",
            candidate_status="REJECTED",
            raw_candidate_status="CANDIDATE_REJECTED",
            score=-3.0,
            failed_gates=("collapse_gate",),
            passed_gates=("gap_quality_gate",),
            model_quality_validation_status="COMPLETED",
        )
    ]

    result = runner.run(
        FeatureRegimeExperimentConfig(
            symbol="ETHUSDT",
            interval="15m",
            start_date="2025-01-01",
            feature_version="fv3_candle_ta_context",
            sample_mode=True,
            output_dir=tmp_path,
        )
    )

    summary = json.loads(Path(result.summary_json_path).read_text(encoding="utf-8"))
    assert summary["candidate_status"] == "REJECTED"
    assert summary["candle_ta_context_features_attached"] is False
    assert summary["candle_ta_context_missing_reason"] == "fv3_candle_ta_context_rows_unavailable"
    assert summary["real_feature_diagnostics_missing_reason"] == "dataset_rows_unavailable"
    assert summary["regime_features_attached"] is False
    assert summary["regime_features_missing_reason"] == "regime_data_unavailable"
