from pathlib import Path
from types import SimpleNamespace

from app.experiments.feature_regime_experiment_runner import (
    FeatureRegimeExperimentConfig,
    FeatureRegimeExperimentRunner,
    _ExperimentLogger,
)
from app.experiments.label_grid_experiment_runner import (
    LabelGridExperimentCandidateResult,
    LabelGridExperimentRunner,
)
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


def test_ml36_1_candidate_diagnostics_are_propagated_without_silent_empty_dicts(
    tmp_path: Path,
) -> None:
    label_grid_runner = LabelGridExperimentRunner()
    label_config = _label_config()
    label_candidate = label_grid_runner._build_candidate_result(
        label_config=label_config,
        quality_payload={
            "quality_status": "QUALITY_REJECTED",
            "model_version": "mv",
            "training_run_id": "run",
            "probability_diagnostics": {
                "actual_direction_counts": {"UP": 10, "DOWN": 8, "FLAT": 6},
                "predicted_direction_counts": {"UP": 20, "DOWN": 2, "FLAT": 2},
            },
            "collapse_diagnostics_v2": {"collapse_detected": True, "collapse_type": "MIXED"},
            "walk_forward_profit_diagnostics": {"walk_forward_profit_factor": 0.97},
            "profit_aware_diagnostics": {"profit_factor": 0.99},
            "regime_label_builder_status": {
                "regime_label_builder_status": "built",
                "regime_label_builder_used_in_training": True,
                "regime_specific_training_applied": True,
                "missing_requirements": [],
                "warnings": [],
            },
            "candidate_selection": {
                "candidate_status": "CANDIDATE_REJECTED",
                "failed_gates": ["collapse_gate", "walk_forward_gate"],
                "passed_gates": ["baseline_edge_gate"],
            },
            "quality_gates_summary": {
                "failed_gates": ["collapse_gate", "walk_forward_gate"],
                "passed_gates": ["baseline_edge_gate"],
            },
            "gap_quality": {
                "gap_severity": "OK",
                "gap_severity_for_training": "OK",
                "dataset_safe_for_training": True,
            },
            "anti_collapse": {
                "actual_distribution": {"UP": 0.4, "DOWN": 0.3, "FLAT": 0.3},
                "predicted_distribution": {"UP": 0.8, "DOWN": 0.1, "FLAT": 0.1},
                "collapse_type": "MIXED",
            },
        },
        class_distribution={"UP": 10, "DOWN": 8, "FLAT": 6},
        gate_policy_summary={},
    )

    assert label_candidate.probability_diagnostics
    assert label_candidate.probability_diagnostics_missing_reason is None
    assert label_candidate.collapse_diagnostics_v2
    assert label_candidate.walk_forward_profit_diagnostics
    assert label_candidate.profit_aware_diagnostics
    assert label_candidate.regime_label_builder_status

    fake_inner_result = SimpleNamespace(
        candidate_results=(
            LabelGridExperimentCandidateResult(**label_candidate.to_dict()),
        ),
        candidate_ranking=(
            {"config_id": label_config.config_id, "score": -2.0},
        ),
        feature_version_used="fv2",
        experiment_status="COMPLETED_NO_ACCEPTED_CANDIDATE",
    )

    class FakeLabelGridRunner:
        def run(self, config: object) -> SimpleNamespace:
            return fake_inner_result

    runner = FeatureRegimeExperimentRunner(label_grid_runner=FakeLabelGridRunner())
    logger = _ExperimentLogger(experiment_id="ml36_1_diag", output_dir=tmp_path)
    candidates, _, _ = runner._real_candidates(
        config=FeatureRegimeExperimentConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            experiment_id="ml36_1_diag",
            feature_version="fv2",
            output_dir=tmp_path,
        ),
        experiment_id="ml36_1_diag",
        selected_base_configs=[label_config.to_dict()],
        feature_weak_signal_detected=False,
        feature_leakage_risk_detected=False,
        real_feature_diagnostics={
            "row_count": 123,
            "real_feature_diagnostics_used": True,
            "source": "runtime_regime_label_builder",
        },
        real_feature_diagnostics_missing_reason=None,
        gap_severity_for_training="OK",
        gap_training_safe=True,
        logger=logger,
        experiment_dir=tmp_path / "ml36_1_diag",
    )

    candidate = candidates[0]
    assert candidate.probability_diagnostics
    assert candidate.real_feature_diagnostics
    assert candidate.real_feature_diagnostics_missing_reason is None
    assert candidate.collapse_diagnostics_v2
    assert candidate.walk_forward_profit_diagnostics
    assert candidate.profit_aware_diagnostics
