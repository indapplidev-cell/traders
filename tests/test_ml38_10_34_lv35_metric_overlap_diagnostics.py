from app.diagnostics.fold_feature_regime_repair_probe import (
    FoldFeatureRegimeRepairProbe,
)
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.feature_regime_experiment_reporter import (
    FeatureRegimeExperimentReporter,
)


def _trade_params():
    return {
        "take_profit_atr": 1.20,
        "stop_loss_atr": 1.50,
        "fee_r": 0.0,
        "slippage_r": 0.0,
        "same_candle_policy": "conservative",
        "exit_policy_profile": None,
        "exit_timeout_bars": None,
        "exit_mitigation_loss_r": None,
        "exit_neutral_abs_r": None,
    }


def test_lv35_metric_overlap_distribution_records_zero_one_and_two_failures():
    evaluator = ProfitAwareEvaluatorV2()
    signal_rows = [
        {
            "signal_date": "2026-06-09",
            "signal_direction": "LONG",
            "market_regime": "trend_down",
            "active_regime_flags": ["trend_down", "high_volatility"],
            "entry_path_quality_score": 0.75,
            "stop_pressure_risk_score": 0.20,
            "mae_pressure_risk_score": 0.20,
            "current_close": 100.0,
            "atr_14": 1.0,
            "future_candles": [{"high": 101.5, "low": 99.8, "close": 101.0}],
        },
        {
            "signal_date": "2026-06-10",
            "signal_direction": "LONG",
            "market_regime": "trend_down",
            "active_regime_flags": ["trend_down", "high_volatility"],
            "entry_path_quality_score": 0.69,
            "stop_pressure_risk_score": 0.20,
            "mae_pressure_risk_score": 0.20,
            "current_close": 100.0,
            "atr_14": 1.0,
            "future_candles": [{"high": 101.2, "low": 99.7, "close": 101.0}],
        },
        {
            "signal_date": "2026-06-11",
            "signal_direction": "LONG",
            "market_regime": "trend_down",
            "active_regime_flags": ["trend_down", "high_volatility"],
            "entry_path_quality_score": 0.69,
            "stop_pressure_risk_score": 0.45,
            "mae_pressure_risk_score": 0.20,
            "current_close": 100.0,
            "atr_14": 1.0,
            "future_candles": [{"high": 100.1, "low": 98.0, "close": 99.0}],
        },
    ]

    filtered, summary = evaluator._apply_fold_feature_regime_filter(
        signal_rows=signal_rows,
        enabled=True,
        profile="TEST_ML38_10_34_METRIC_OVERLAP",
        rules={
            "disable_unconditional_blocked_regime": True,
            "conditional_regime_rules": [
                {
                    "rule_id": "hv_low_entry_and_high_stop",
                    "active_regime_any": ["high_volatility"],
                    "entry_path_quality_below": 0.70,
                    "stop_pressure_above": 0.39,
                    "metric_logic": "all",
                    "min_metric_failure_count": 2,
                }
            ],
            "missing_feature_policy": "pass_with_warning",
        },
        target_dates=(),
        date_blackout_used=False,
        contribution_trade_params=_trade_params(),
    )

    assert len(filtered) == 2
    assert summary["conditional_regime_rule_counts"] == {
        "hv_low_entry_and_high_stop": 1
    }
    assert summary["conditional_regime_rule_metric_failure_count_distribution_by_rule"] == {
        "hv_low_entry_and_high_stop": {
            "failed_0": 1,
            "failed_1": 1,
            "failed_2_plus": 1,
        }
    }
    assert summary["conditional_regime_rule_observed_metric_failure_counts_by_rule"] == {
        "hv_low_entry_and_high_stop": {
            "entry_path_quality_below": 2,
            "stop_pressure_above": 1,
        }
    }
    assert summary["conditional_regime_rule_metric_pair_failure_counts_by_rule"] == {
        "hv_low_entry_and_high_stop": {
            "entry_path_quality_below+stop_pressure_above": 1,
        }
    }

    outcome_by_failure = summary["conditional_regime_rule_outcome_by_failure_count"]
    assert set(outcome_by_failure["hv_low_entry_and_high_stop"]) == {
        "failed_0",
        "failed_1",
        "failed_2_plus",
    }

    board = summary["conditional_regime_metric_overlap_board"]
    assert board[0]["rule_id"] == "hv_low_entry_and_high_stop"
    assert board[0]["eligible_count"] == 3
    assert board[0]["actual_removed_count"] == 1
    assert board[0]["failed_0_count"] == 1
    assert board[0]["failed_1_count"] == 1
    assert board[0]["failed_2_plus_count"] == 1
    assert board[0]["metric_overlap_status"] == "REMOVALS_ACTIVE"


def test_lv35_metric_overlap_no_removals_still_reports_one_metric_failures():
    evaluator = ProfitAwareEvaluatorV2()
    signal_rows = [
        {
            "signal_date": "2026-06-09",
            "signal_direction": "LONG",
            "market_regime": "trend_down",
            "active_regime_flags": ["trend_down", "high_volatility"],
            "entry_path_quality_score": 0.75,
            "stop_pressure_risk_score": 0.20,
            "current_close": 100.0,
            "atr_14": 1.0,
            "future_candles": [{"high": 101.5, "low": 99.8, "close": 101.0}],
        },
        {
            "signal_date": "2026-06-10",
            "signal_direction": "LONG",
            "market_regime": "trend_down",
            "active_regime_flags": ["trend_down", "high_volatility"],
            "entry_path_quality_score": 0.69,
            "stop_pressure_risk_score": 0.20,
            "current_close": 100.0,
            "atr_14": 1.0,
            "future_candles": [{"high": 101.2, "low": 99.7, "close": 101.0}],
        },
    ]

    filtered, summary = evaluator._apply_fold_feature_regime_filter(
        signal_rows=signal_rows,
        enabled=True,
        profile="TEST_ML38_10_34_NO_REMOVALS",
        rules={
            "disable_unconditional_blocked_regime": True,
            "conditional_regime_rules": [
                {
                    "rule_id": "hv_low_entry_and_high_stop",
                    "active_regime_any": ["high_volatility"],
                    "entry_path_quality_below": 0.70,
                    "stop_pressure_above": 0.39,
                    "metric_logic": "all",
                    "min_metric_failure_count": 2,
                }
            ],
            "missing_feature_policy": "pass_with_warning",
        },
        target_dates=(),
        date_blackout_used=False,
        contribution_trade_params=_trade_params(),
    )

    assert len(filtered) == 2
    assert summary["conditional_regime_rule_counts"] == {}
    assert summary["conditional_regime_rule_metric_failure_count_distribution_by_rule"] == {
        "hv_low_entry_and_high_stop": {
            "failed_0": 1,
            "failed_1": 1,
        }
    }
    board = summary["conditional_regime_metric_overlap_board"]
    assert board[0]["actual_removed_count"] == 0
    assert board[0]["failed_1_count"] == 1
    assert board[0]["failed_2_plus_count"] == 0
    assert board[0]["metric_overlap_status"] == "ONLY_ONE_METRIC_FAILURES"
    assert (
        board[0]["bottleneck_label"]
        == "conditions_too_strict_or_metrics_do_not_overlap"
    )


def test_feature_regime_reporter_compacts_metric_overlap_diagnostics():
    compact = FeatureRegimeExperimentReporter._compact_fold_feature_summary(
        {
            "input_signal_count": 2,
            "output_signal_count": 2,
            "removed_signal_count": 0,
            "conditional_regime_rule_metric_failure_count_distribution_by_rule": {
                "hv_low_entry_and_high_stop": {"failed_0": 1, "failed_1": 1}
            },
            "conditional_regime_rule_observed_metric_failure_counts_by_rule": {
                "hv_low_entry_and_high_stop": {"entry_path_quality_below": 1}
            },
            "conditional_regime_rule_metric_pair_failure_counts_by_rule": {
                "hv_low_entry_and_high_stop": {}
            },
            "conditional_regime_rule_outcome_by_failure_count": {
                "hv_low_entry_and_high_stop": {
                    "failed_1": {
                        "signal_count": 1,
                        "total_r": -0.5,
                        "positive_r": 0.0,
                        "negative_r": -0.5,
                        "win_count": 0,
                        "loss_count": 1,
                        "neutral_count": 0,
                    }
                }
            },
            "conditional_regime_metric_overlap_board": [
                {
                    "rule_id": "hv_low_entry_and_high_stop",
                    "eligible_count": 2,
                    "actual_removed_count": 0,
                    "failed_0_count": 1,
                    "failed_1_count": 1,
                    "failed_2_plus_count": 0,
                    "metric_overlap_status": "ONLY_ONE_METRIC_FAILURES",
                    "bottleneck_label": "conditions_too_strict_or_metrics_do_not_overlap",
                }
            ],
        }
    )

    assert compact["conditional_regime_rule_metric_failure_count_distribution_by_rule"] == {
        "hv_low_entry_and_high_stop": {"failed_0": 1, "failed_1": 1}
    }
    assert compact["conditional_regime_metric_overlap_board"][0]["metric_overlap_status"] == (
        "ONLY_ONE_METRIC_FAILURES"
    )
    assert compact["conditional_regime_rule_outcome_by_failure_count"]["hv_low_entry_and_high_stop"]["failed_1"]["signal_count"] == 1


def test_fold_feature_regime_probe_aggregates_metric_overlap_diagnostics():
    probe = FoldFeatureRegimeRepairProbe()
    diagnostics = probe._feature_filter_diagnostics(
        [
            {
                "config_id": "lv35_test",
                "fold_feature_regime_filter_summary": {
                    "removed_signal_count": 0,
                    "conditional_regime_rule_eligible_counts": {
                        "hv_low_entry_and_high_stop": 2
                    },
                    "conditional_regime_rule_blocked_counts": {},
                    "conditional_regime_rule_passed_counts": {
                        "hv_low_entry_and_high_stop": 2
                    },
                    "conditional_regime_rule_metric_logic": {
                        "hv_low_entry_and_high_stop": "all"
                    },
                    "conditional_regime_rule_required_metric_failure_count": {
                        "hv_low_entry_and_high_stop": 2
                    },
                    "conditional_regime_rule_metric_condition_count": {
                        "hv_low_entry_and_high_stop": 2
                    },
                    "conditional_regime_rule_metric_failure_count_distribution_by_rule": {
                        "hv_low_entry_and_high_stop": {"failed_0": 1, "failed_1": 1}
                    },
                    "conditional_regime_rule_observed_metric_failure_counts_by_rule": {
                        "hv_low_entry_and_high_stop": {"entry_path_quality_below": 1}
                    },
                    "conditional_regime_rule_metric_pair_failure_counts_by_rule": {
                        "hv_low_entry_and_high_stop": {}
                    },
                    "conditional_regime_rule_outcome_by_failure_count": {
                        "hv_low_entry_and_high_stop": {
                            "failed_1": {
                                "signal_count": 1,
                                "total_r": -0.5,
                                "positive_r": 0.0,
                                "negative_r": -0.5,
                                "win_count": 0,
                                "loss_count": 1,
                                "neutral_count": 0,
                            }
                        }
                    },
                },
            }
        ]
    )

    assert diagnostics["aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule"] == {
        "hv_low_entry_and_high_stop": {"failed_0": 1, "failed_1": 1}
    }
    board = diagnostics["aggregate_conditional_regime_metric_overlap_board"]
    assert board[0]["rule_id"] == "hv_low_entry_and_high_stop"
    assert board[0]["metric_overlap_status"] == "ONLY_ONE_METRIC_FAILURES"
