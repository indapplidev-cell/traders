from __future__ import annotations

from app.training.metrics import TrainingMetrics
from app.training.training_service import TrainingConfig
from app.training.training_pipeline_runner import TrainingPipelineConfig
from app.experiments.label_grid_experiment_runner import LabelGridExperimentCandidateResult
from app.experiments.feature_regime_experiment_runner import FeatureRegimeCandidateResult
from app.experiments.multi_symbol_feature_regime_analyzer import MultiSymbolFeatureRegimeAnalyzer
from app.labels.label_quality_grid import LabelQualityGridPlanner


def test_ml38_10_16_1_training_configs_carry_mae_threshold() -> None:
    service_config = TrainingConfig(
        symbol="SOLUSDT",
        interval="15m",
        horizon_candles=12,
        feature_version="fv3",
        label_version="lv24_test",
        model_name="ml",
        model_version="v1",
        mae_pressure_max_risk_score=0.55,
    )
    pipeline_config = TrainingPipelineConfig(
        symbol="SOLUSDT",
        interval="15m",
        start_date="2026-04-01",
        mae_pressure_max_risk_score=0.55,
    )

    assert service_config.mae_pressure_max_risk_score == 0.55
    assert pipeline_config.mae_pressure_max_risk_score == 0.55


def test_ml38_10_16_1_label_grid_lv24_has_real_mae_threshold() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    by_id = {item["config_id"]: item for item in grid["configs"]}

    assert by_id["lv24_h12_tts_thr065_sqmask060_epq068_sp047_mae"]["mae_pressure_max_risk_score"] == 0.55
    assert by_id["lv24_h12_tts_thr065_sqmask060_epq070_sp045_mae_rr"]["mae_pressure_max_risk_score"] == 0.52


def test_ml38_10_16_1_metrics_mae_threshold_blocks_rows() -> None:
    metrics = TrainingMetrics().compute(
        direction_probabilities=[[0.80, 0.10, 0.10], [0.80, 0.10, 0.10]],
        direction_targets=[0, 2],
        tp_sl_probabilities=[0.9, 0.1],
        tp_sl_targets=[True, None],
        expected_move_predictions=[1.0, -1.0],
        expected_move_targets=[1.0, -1.0],
        opportunity_probabilities=[0.90, 0.90],
        opportunity_targets=[1, 0],
        opportunity_probability_threshold=0.50,
        setup_quality_scores=[0.80, 0.80],
        setup_quality_decision_mask_enabled=False,
        entry_path_quality_filter_enabled=True,
        entry_path_quality_scores=[0.80, 0.80],
        stop_pressure_risk_scores=[0.20, 0.20],
        mae_pressure_risk_scores=[0.20, 0.80],
        entry_path_quality_min_threshold=0.68,
        stop_pressure_max_risk_score=0.47,
        mae_pressure_max_risk_score=0.55,
        training_objective="trade_two_stage",
    )

    assert metrics["mae_pressure_max_risk_score"] == 0.55
    assert metrics["entry_path_quality_masked_row_count"] == 1
    assert metrics["entry_path_quality_filter_summary"]["mae_pressure_max_risk_score"] == 0.55


def test_ml38_10_16_1_result_objects_serialize_mae_threshold() -> None:
    label_result = LabelGridExperimentCandidateResult(
        config_id="lv24_test",
        label_config={},
        status="REJECTED",
        quality_status="REJECTED",
        candidate_status="REJECTED",
        raw_candidate_status="REJECTED",
        model_version=None,
        training_run_id=None,
        dataset_rows=10,
        train_rows=6,
        val_rows=2,
        test_rows=2,
        mae_pressure_max_risk_score=0.55,
    )
    feature_result = FeatureRegimeCandidateResult(
        candidate_id="lv24_test_fv3",
        config_id="lv24_test",
        label_config={},
        status="REJECTED",
        quality_status="REJECTED",
        candidate_status="REJECTED",
        raw_candidate_status="REJECTED",
        score=0.0,
        mae_pressure_max_risk_score=0.55,
    )

    assert label_result.to_dict()["mae_pressure_max_risk_score"] == 0.55
    assert feature_result.to_dict()["mae_pressure_max_risk_score"] == 0.55


def test_ml38_10_16_1_multi_symbol_audit_extracts_mae_threshold() -> None:
    payload = MultiSymbolFeatureRegimeAnalyzer._entry_path_audit_payload(
        {
            "entry_path_quality_filter_enabled": True,
            "entry_path_quality_min_threshold": 0.68,
            "stop_pressure_max_risk_score": 0.47,
            "mae_pressure_max_risk_score": 0.55,
            "entry_path_prediction_filter_summary": {
                "mae_pressure_threshold": 0.55,
                "blocked_by_high_mae_pressure_count": 3,
            },
            "stop_pressure_effectiveness_audit": {
                "mae_pressure_threshold": 0.55,
                "blocked_by_high_mae_pressure_count": 3,
            },
        }
    )

    assert payload["mae_pressure_max_risk_score"] == 0.55
    assert payload["entry_path_prediction_filter_summary"]["blocked_by_high_mae_pressure_count"] == 3
