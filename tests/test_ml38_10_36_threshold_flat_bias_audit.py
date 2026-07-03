import json
from pathlib import Path

from app.diagnostics.fold_feature_regime_repair_probe import (
    FoldFeatureRegimeRepairProbe,
)
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)


def _outcome(total_r: float, signal_count: int = 1) -> dict:
    return {
        "signal_count": signal_count,
        "total_r": total_r,
        "positive_r": max(0.0, total_r),
        "negative_r": min(0.0, total_r),
        "win_count": int(total_r > 0),
        "loss_count": int(total_r < 0),
        "neutral_count": int(total_r == 0),
    }


def _condition_stats(*, failed_r: float, near_r: float = 0.0) -> dict:
    return {
        "rule": {
            "entry_path_quality_below": {
                "metric_key": "entry_path_quality",
                "direction": "below",
                "threshold": 0.60,
                "eligible_count": 4,
                "value_present_count": 4,
                "value_missing_count": 0,
                "failed_count": 1,
                "passed_count": 3,
                "near_0_02_count": 0,
                "near_0_05_count": 1,
                "near_0_10_count": 0,
                "far_count": 2,
                "failed_outcome": _outcome(failed_r),
                "near_0_02_outcome": _outcome(0.0, 0),
                "near_0_05_outcome": _outcome(near_r),
                "near_0_10_outcome": _outcome(0.0, 0),
            }
        }
    }


def test_profitable_failed_threshold_group_is_harmful() -> None:
    board = ProfitAwareEvaluatorV2._conditional_regime_rule_threshold_sensitivity_board(
        eligible_counts={"rule": 4},
        threshold_condition_stats=_condition_stats(failed_r=1.5),
    )
    summary = ProfitAwareEvaluatorV2._conditional_regime_threshold_sensitivity_summary(board)

    assert board[0]["failure_effect_label"] == "THRESHOLD_FAILURES_HARMFUL"
    assert board[0]["threshold_diagnosis"] == "FAILED_GROUP_PROFITABLE_DO_NOT_FILTER"
    assert summary["primary_bottleneck"] == "failed_groups_are_profitable_or_missing_overlap"


def test_negative_failed_threshold_group_remains_diagnostic_only() -> None:
    board = ProfitAwareEvaluatorV2._conditional_regime_rule_threshold_sensitivity_board(
        eligible_counts={"rule": 4},
        threshold_condition_stats=_condition_stats(failed_r=-1.5),
    )
    summary = ProfitAwareEvaluatorV2._conditional_regime_threshold_sensitivity_summary(board)

    assert board[0]["failure_effect_label"] == "THRESHOLD_FAILURES_POTENTIALLY_USEFUL"
    assert summary["research_only_warning"] == (
        "threshold_sensitivity_is_diagnostic_only_not_a_trading_rule"
    )
    assert "accepted" not in summary


def test_profitable_near_miss_group_says_do_not_relax() -> None:
    stats = _condition_stats(failed_r=0.0, near_r=1.2)
    stats["rule"]["entry_path_quality_below"]["failed_outcome"] = _outcome(0.0, 0)
    board = ProfitAwareEvaluatorV2._conditional_regime_rule_threshold_sensitivity_board(
        eligible_counts={"rule": 4}, threshold_condition_stats=stats
    )

    assert board[0]["near_0_05_total_r"] == 1.2
    assert board[0]["near_miss_effect_label"] == "RELAXING_THRESHOLD_WOULD_HURT"
    assert board[0]["threshold_diagnosis"] == "NEAR_MISS_PROFITABLE_DO_NOT_RELAX"


def test_fold_probe_aggregates_threshold_board() -> None:
    source_board = ProfitAwareEvaluatorV2._conditional_regime_rule_threshold_sensitivity_board(
        eligible_counts={"rule": 4},
        threshold_condition_stats=_condition_stats(failed_r=1.5),
    )
    diagnostics = FoldFeatureRegimeRepairProbe()._feature_filter_diagnostics(
        [
            {
                "config_id": "threshold_test",
                "fold_feature_regime_filter_summary": {
                    "removed_signal_count": 0,
                    "conditional_regime_rule_threshold_sensitivity_board": source_board,
                },
            }
        ]
    )

    assert diagnostics["aggregate_conditional_regime_rule_threshold_sensitivity_board"]
    assert diagnostics["aggregate_conditional_regime_threshold_sensitivity_summary"][
        "diagnostic_version"
    ] == "ml38.10.36"


def _summary(*, walk_forward_total_r: float | None) -> dict:
    candidate = {
        "config_id": "audit_config",
        "candidate_status": "REJECTED",
        "score": -1.0,
        "baseline_edge": -0.7359,
        "collapse_type": "FLAT_UNDERPREDICTION",
        "collapse_severity": "WATCH",
        "actual_class_distribution": {"FLAT": 0.9239, "DOWN": 0.05, "UP": 0.0261},
        "predicted_class_distribution": {"FLAT": 0.112, "DOWN": 0.70, "UP": 0.188},
        "walk_forward_total_r": walk_forward_total_r,
        "walk_forward_global_total_r": None,
        "walk_forward_profit_factor": 1.0717,
        "failed_gates": ["bias_gate", "baseline_edge_gate"],
        "passed_gates": ["gap_quality_gate"],
        "fold_feature_regime_filter_summary": {
            "removed_signal_count": 0,
            "conditional_regime_rule_threshold_sensitivity_board": (
                ProfitAwareEvaluatorV2._conditional_regime_rule_threshold_sensitivity_board(
                    eligible_counts={"rule": 4},
                    threshold_condition_stats=_condition_stats(failed_r=1.5),
                )
            ),
        },
    }
    return {
        "experiment_id": "audit_exp",
        "symbol": "SOLUSDT",
        "interval": "15m",
        "start_date": "2025-01-01",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "candidate_count": 1,
        "evaluated_candidate_count": 1,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "audit_config",
        "best_candidate_score": -1.0,
        "feature_version_used": "fv4_book_setup_context",
        "real_feature_diagnostics_used": True,
        "real_feature_diagnostics_row_count": 1,
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "gap_training_safe": True,
        "regime_features_attached": True,
        "candidate_results": [candidate],
        "configs_ranked": [dict(candidate)],
    }


def test_multi_symbol_top_level_contains_aggregate_threshold_keys(tmp_path: Path) -> None:
    path = tmp_path / "feature_regime_experiment_summary.json"
    path.write_text(json.dumps(_summary(walk_forward_total_r=2.7304)), encoding="utf-8")
    result = MultiSymbolFeatureRegimeAnalyzer().analyze([path])

    assert "aggregate_conditional_regime_rule_threshold_sensitivity_board" in result
    assert "aggregate_conditional_regime_threshold_sensitivity_summary" in result


def test_walk_forward_total_r_mapping_preserves_value_and_zero() -> None:
    result = MultiSymbolFeatureRegimeAnalyzer._symbol_result(
        _summary(walk_forward_total_r=2.7304)
    )
    assert result["walk_forward_total_r"] == 2.7304

    zero_summary = _summary(walk_forward_total_r=0.0)
    zero_summary["candidate_results"][0]["walk_forward_global_total_r"] = 5.0
    assert MultiSymbolFeatureRegimeAnalyzer._symbol_result(zero_summary)[
        "walk_forward_total_r"
    ] == 0.0


def test_flat_bias_audit_detects_severe_underprediction() -> None:
    symbol_result = MultiSymbolFeatureRegimeAnalyzer._symbol_result(
        _summary(walk_forward_total_r=2.7304)
    )
    audit = MultiSymbolFeatureRegimeAnalyzer._flat_bias_root_cause_audit([symbol_result])

    assert audit["severe_flat_underprediction_symbol_count"] == 1
    assert audit["flat_underprediction_by_symbol"]["SOLUSDT"]["root_cause_label"] == (
        "severe_flat_underprediction_with_negative_baseline_edge"
    )
    assert "audit_label_distribution_vs_prediction_distribution" in audit[
        "recommendations"
    ]


def test_flat_bias_audit_handles_missing_distributions() -> None:
    audit = MultiSymbolFeatureRegimeAnalyzer._flat_bias_root_cause_audit(
        [
            {
                "symbol": "SOLUSDT",
                "best_candidate_config_id": "missing_distribution",
                "failed_gates": ["bias_gate"],
                "baseline_edge": None,
            }
        ]
    )

    assert audit["flat_underprediction_by_symbol"]["SOLUSDT"]["root_cause_label"] == (
        "bias_gate_failed_without_flat_distribution"
    )
