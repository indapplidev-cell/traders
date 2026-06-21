from app.experiments.label_grid_experiment_runner import (
    LabelGridExperimentCandidateResult,
    LabelGridExperimentRunner,
)
from app.labels.label_quality_grid import LabelQualityGridConfig


def test_ml38_10_14_1_candidate_result_reads_entry_path_fields_from_test_metrics() -> None:
    runner = LabelGridExperimentRunner()
    label_config = LabelQualityGridConfig(
        config_id="test_epq",
        label_version="test_epq",
        horizon=12,
        threshold=0.60,
        take_profit_atr=1.2,
        stop_loss_atr=1.2,
        flat_threshold=0.60,
        description="Unit test config for ML38.10.14.1 entry-path propagation.",
        risk_note="Test-only config. No live trading, no auto-activation.",
    )

    result = runner._build_candidate_result(
        label_config=label_config,
        quality_payload={
            "quality_status": "REJECTED",
            "candidate_selection": {"candidate_status": "REJECTED"},
            "test_metrics": {
                "entry_path_quality_filter_enabled": True,
                "entry_path_quality_min_threshold": 0.70,
                "stop_pressure_max_risk_score": 0.45,
                "entry_path_quality_masked_row_count": 100,
                "entry_path_quality_forced_no_trade_count": 7,
                "entry_path_quality_mask_false_positive_removed_count": 5,
                "entry_path_quality_filter_summary": {"rows_blocked_by_entry_path_filter": 100},
                "entry_path_quality_filter_diagnostics": {"diagnostic_version": "ml38.10.14"},
                "opportunity_precision": 0.33,
                "opportunity_recall": 0.44,
                "opportunity_false_positive_rate": 0.08,
                "predicted_trade_rate": 0.10,
            },
        },
        class_distribution={},
        gate_policy_summary={},
    )

    assert isinstance(result, LabelGridExperimentCandidateResult)
    assert result.entry_path_quality_filter_enabled is True
    assert result.entry_path_quality_min_threshold == 0.70
    assert result.stop_pressure_max_risk_score == 0.45
    assert result.entry_path_quality_masked_row_count == 100
    assert result.entry_path_quality_forced_no_trade_count == 7
    assert result.entry_path_quality_mask_false_positive_removed_count == 5
    assert result.entry_path_quality_filter_summary["rows_blocked_by_entry_path_filter"] == 100
    assert result.entry_path_quality_filter_diagnostics["diagnostic_version"] == "ml38.10.14"
    assert result.opportunity_precision == 0.33
    assert result.opportunity_recall == 0.44
    assert result.opportunity_false_positive_rate == 0.08
