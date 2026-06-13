from pathlib import Path
from types import SimpleNamespace

from app.experiments.feature_regime_experiment_runner import (
    FeatureRegimeExperimentConfig,
    FeatureRegimeExperimentRunner,
)
from app.experiments.label_grid_experiment_runner import LabelGridExperimentRunner
from app.labels.label_quality_grid import LabelQualityGridConfig


def _label_config() -> LabelQualityGridConfig:
    return LabelQualityGridConfig(
        config_id="lv2_h12_thr05_tp15_sl10",
        label_version="lv2_h12_thr05_tp15_sl10",
        horizon=12,
        threshold=0.5,
        take_profit_atr=1.5,
        stop_loss_atr=1.0,
        flat_threshold=0.5,
        description="test",
        risk_note="test",
    )


def test_ml36_2_top_level_regime_summary_prefers_final_candidate_runtime_state(
    tmp_path: Path,
) -> None:
    label_grid_runner = LabelGridExperimentRunner()
    label_candidate = label_grid_runner._build_candidate_result(
        label_config=_label_config(),
        quality_payload={
            "quality_status": "QUALITY_REJECTED",
            "model_version": "mv",
            "training_run_id": "run",
            "candidate_selection": {
                "candidate_status": "CANDIDATE_REJECTED",
                "failed_gates": ["collapse_gate"],
                "passed_gates": ["baseline_edge_gate"],
            },
            "quality_gates_summary": {
                "failed_gates": ["collapse_gate"],
                "passed_gates": ["baseline_edge_gate"],
            },
            "gap_quality": {
                "gap_severity": "OK",
                "gap_severity_for_training": "OK",
                "dataset_safe_for_training": True,
            },
            "probability_diagnostics": {"predicted_direction_counts": {"UP": 20}},
            "collapse_diagnostics_v2": {"collapse_detected": True},
            "walk_forward_profit_diagnostics": {"walk_forward_profit_factor": 0.97},
            "profit_aware_diagnostics": {"profit_factor": 0.98},
            "regime_label_builder_status": {
                "regime_label_builder_status": "built",
                "regime_label_builder_used_in_training": True,
                "regime_specific_training_applied": True,
                "missing_requirements": [],
                "warnings": [],
            },
        },
        class_distribution={},
        gate_policy_summary={},
    )
    fake_inner_result = SimpleNamespace(
        candidate_results=(label_candidate,),
        candidate_ranking=(
            {
                "config_id": label_candidate.config_id,
                "candidate_id": label_candidate.config_id,
                "score": -2.0,
                "candidate_status": label_candidate.candidate_status,
                "failed_gates": list(label_candidate.failed_gates),
            },
        ),
        feature_version_used="fv2",
        experiment_status="COMPLETED_NO_ACCEPTED_CANDIDATE",
    )

    class FakeLabelGridRunner:
        def run(self, config: object) -> SimpleNamespace:
            return fake_inner_result

    runner = FeatureRegimeExperimentRunner(label_grid_runner=FakeLabelGridRunner())
    runner._collect_diagnostics = lambda **kwargs: {
        "feature_quality_summary": {"weak_signal_detected": False},
        "feature_group_quality_summary": {},
        "regime_feature_summary": {},
        "feature_leakage_summary": {"leakage_risk_detected": False},
        "regime_experiment_plan_summary": {},
        "real_feature_diagnostics": {
            "row_count": 123,
            "real_feature_diagnostics_used": True,
            "regime_label_builder_status": {
                "regime_label_builder_status": "blocked",
                "regime_label_builder_used_in_training": False,
                "regime_specific_training_applied": False,
                "missing_requirements": ["regime_runtime_labels_not_built"],
                "warnings": [],
            },
        },
        "regime_label_builder_status": {
            "regime_label_builder_status": "blocked",
            "regime_label_builder_used_in_training": False,
            "regime_specific_training_applied": False,
            "missing_requirements": ["regime_runtime_labels_not_built"],
            "warnings": [],
        },
        "real_feature_diagnostics_used": True,
        "real_feature_diagnostics_row_count": 123,
        "regime_features_attached": True,
        "regime_feature_count": 5,
        "regime_feature_source": "runtime_regime_label_builder",
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "gap_training_safe": True,
        "warnings": ["regime_runtime_labels_not_built"],
        "real_feature_diagnostics_missing_reason": None,
    }
    runner._build_regime_status = lambda **kwargs: {
        "regime_specific_labeling_available": True,
        "regime_specific_training_applied": False,
        "missing_requirements": ["regime_runtime_labels_not_built"],
    }

    result = runner.run(
        FeatureRegimeExperimentConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            experiment_id="ml36_2_top_level",
            feature_version="fv2",
            output_dir=tmp_path,
        )
    )

    assert result.regime_label_builder_status["regime_label_builder_status"] == "built"
    assert result.regime_label_builder_status["regime_label_builder_used_in_training"] is True
    assert result.regime_specific_training_applied is True
    assert result.regime_label_builder_used_in_training_any is True
    assert result.regime_specific_training_applied_any is True
    assert "regime_runtime_labels_not_built" not in result.missing_requirements
    assert result.real_feature_diagnostics["row_count"] == 123
