import json
from pathlib import Path

from app.experiments.feature_regime_experiment_runner import (
    FeatureRegimeCandidateResult,
    FeatureRegimeExperimentConfig,
    FeatureRegimeExperimentRunner,
)


def test_ml38_feature_regime_summary_contains_fv3_and_candle_ta_context_fields(tmp_path: Path) -> None:
    runner = FeatureRegimeExperimentRunner()
    runner._select_base_configs = lambda config: [  # type: ignore[method-assign]
        {"config_id": "lv2_h12_thr05_tp15_sl10", "label_version": "lv2_h12_thr05_tp15_sl10", "horizon": 12, "threshold": 0.5, "take_profit_atr": 1.5, "stop_loss_atr": 1.0}
    ]
    runner._select_regime_configs = lambda config, selected: [  # type: ignore[method-assign]
        {"config_id": "regime_preview"}
    ]
    runner._collect_diagnostics = lambda config, selected_base_configs, logger: {  # type: ignore[method-assign]
        "feature_quality_summary": {"weak_signal_detected": False},
        "feature_group_quality_summary": {"groups": []},
        "regime_feature_summary": {"regime_data_available": True},
        "feature_leakage_summary": {"leakage_risk_detected": False},
        "regime_experiment_plan_summary": {"ready_for_real_regime_training": True, "recommendations": []},
        "real_feature_diagnostics": {"row_count": 321, "candle_ta_context_features_attached": True},
        "regime_label_builder_status": {
            "regime_label_builder_status": "built",
            "regime_label_builder_used_in_training": True,
            "regime_specific_training_applied": True,
            "missing_requirements": [],
        },
        "real_feature_diagnostics_used": True,
        "real_feature_diagnostics_row_count": 321,
        "regime_features_attached": True,
        "candle_ta_context_features_attached": True,
        "regime_feature_count": 8,
        "regime_feature_source": "runtime_regime_label_builder",
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "gap_training_safe": True,
        "warnings": [],
        "real_feature_diagnostics_missing_reason": None,
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
            score=-1.25,
            failed_gates=("collapse_gate", "walk_forward_gate"),
            passed_gates=("gap_quality_gate",),
            regime_specific_training_applied=True,
            regime_label_builder_status={
                "regime_label_builder_status": "built",
                "regime_label_builder_used_in_training": True,
                "regime_specific_training_applied": True,
            },
            model_quality_validation_status="COMPLETED",
            model_accuracy=0.41,
            baseline_accuracy=0.39,
            accuracy_edge=0.02,
            profit_total_r=-3.0,
            profit_factor=0.98,
            walk_forward_total_r=-7.0,
            walk_forward_profit_factor=0.97,
            predicted_class_distribution={"UP": 0.72, "DOWN": 0.18, "FLAT": 0.10},
            actual_class_distribution={"UP": 0.34, "DOWN": 0.33, "FLAT": 0.33},
            collapse_detected=True,
            collapse_type="MIXED_COLLAPSE",
        )
    ]

    result = runner.run(
        FeatureRegimeExperimentConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            feature_version="fv3_candle_ta_context",
            sample_mode=True,
            output_dir=tmp_path,
        )
    )

    payload = result.to_dict()
    assert payload["feature_version_used"] == "fv3_candle_ta_context"
    assert payload["candle_ta_context_features_attached"] is True
    assert payload["regime_features_attached"] is True
    assert payload["real_feature_diagnostics_used"] is True
    assert payload["candidate_status"] == "REJECTED"
    assert payload["model_quality_validation_status"] == "COMPLETED"
    assert payload["regime_specific_training_applied"] is True
    assert payload["regime_label_builder_used_in_training_any"] is True

    summary = json.loads(Path(payload["summary_json_path"]).read_text(encoding="utf-8"))
    assert summary["feature_version_used"] == "fv3_candle_ta_context"
    assert summary["candle_ta_context_features_attached"] is True
    assert summary["candidate_status"] == "REJECTED"
    assert summary["model_quality_validation_status"] == "COMPLETED"
