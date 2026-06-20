from __future__ import annotations

from app.diagnostics.two_stage_trade_diagnostics import TwoStageTradeDiagnostics
from app.training.metrics import TrainingMetrics


def test_two_stage_diagnostics_include_raw_and_masked_setup_quality_payloads() -> None:
    metrics = TrainingMetrics().compute(
        direction_probabilities=[
            [0.90, 0.10, 0.0],
            [0.85, 0.15, 0.0],
            [0.80, 0.20, 0.0],
            [0.75, 0.25, 0.0],
        ],
        direction_targets=[2, 0, 0, 2],
        tp_sl_probabilities=[0.0] * 4,
        tp_sl_targets=[None] * 4,
        expected_move_predictions=[0.0] * 4,
        expected_move_targets=[0.0] * 4,
        opportunity_probabilities=[0.90, 0.88, 0.80, 0.75],
        opportunity_targets=[0, 1, 1, 0],
        opportunity_probability_threshold=0.65,
        setup_quality_scores=[0.0, 0.85, 0.70, 0.30],
        setup_quality_min_threshold=0.60,
        setup_quality_decision_mask_enabled=True,
        setup_quality_decision_mask_min_threshold=0.60,
        training_objective="trade_two_stage",
    )

    diagnostics = TwoStageTradeDiagnostics().evaluate_metrics(metrics)

    assert diagnostics["setup_quality_decision_mask_summary"]["enabled"] is True
    assert diagnostics["setup_quality_decision_mask_summary"]["min_threshold"] == 0.60
    assert diagnostics["setup_quality_bucket_metrics_raw"]["missing_or_zero"]["false_positive_count"] == 1
    assert diagnostics["setup_quality_bucket_metrics_after_mask"]["missing_or_zero"]["false_positive_count"] == 0
    assert diagnostics["setup_quality_bucket_metrics_after_mask"]["missing_or_zero"]["predicted_trade_count"] == 0
