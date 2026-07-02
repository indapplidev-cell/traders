from __future__ import annotations

from app.diagnostics.fold_feature_regime_repair_probe import (
    FoldFeatureRegimeRepairProbe,
)
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.feature_regime_experiment_reporter import (
    FeatureRegimeExperimentReporter,
)
from run_fv3_cached_tuning import FAST_DEBUG_CONFIGS, QUICK_QUALITY_CONFIGS


def _signal_row(
    *,
    date: str,
    entry_quality: float,
    high_volatility: bool,
    trend_down: bool,
    future_high: float,
    future_low: float,
) -> dict:
    active_flags = []
    if high_volatility:
        active_flags.append("high_volatility")
    if trend_down:
        active_flags.append("trend_down")
    return {
        "signal_date": date,
        "signal_direction": "LONG",
        "market_regime": "trend_down" if trend_down else "trend_up",
        "active_regime_flags": active_flags,
        "entry_path_quality_score": entry_quality,
        "setup_quality_score": 0.70,
        "stop_pressure_risk_score": 0.20,
        "mae_pressure_risk_score": 0.20,
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": [
            {
                "high": future_high,
                "low": future_low,
                "close": 100.0,
            }
        ],
    }


def test_evaluator_builds_conditional_regime_ablation_and_contribution_board():
    evaluator = ProfitAwareEvaluatorV2()
    signal_rows = [
        _signal_row(
            date="2026-06-09",
            entry_quality=0.70,
            high_volatility=True,
            trend_down=True,
            future_high=100.1,
            future_low=98.0,
        ),
        _signal_row(
            date="2026-06-10",
            entry_quality=0.80,
            high_volatility=True,
            trend_down=True,
            future_high=101.5,
            future_low=99.5,
        ),
    ]

    filtered, summary = evaluator._apply_fold_feature_regime_filter(
        signal_rows=signal_rows,
        enabled=True,
        profile="TEST_CONDITIONAL_ABLATION",
        rules={
            "disable_unconditional_blocked_regime": True,
            "conditional_regime_rules": [
                {
                    "rule_id": "high_volatility_low_entry_quality",
                    "active_regime_any": ["high_volatility"],
                    "entry_path_quality_below": 0.74,
                }
            ],
            "missing_feature_policy": "pass_with_warning",
        },
        target_dates=("2026-06-09",),
        date_blackout_used=False,
        contribution_trade_params={
            "take_profit_atr": 1.20,
            "stop_loss_atr": 1.50,
            "fee_r": 0.0,
            "slippage_r": 0.0,
            "same_candle_policy": "conservative",
            "exit_policy_profile": None,
            "exit_timeout_bars": None,
            "exit_mitigation_loss_r": None,
            "exit_neutral_abs_r": None,
        },
    )

    assert len(filtered) == 1
    assert summary["removed_signal_count"] == 1
    assert summary["conditional_regime_rule_eligible_counts"] == {
        "high_volatility_low_entry_quality": 2
    }
    assert summary["conditional_regime_rule_counts"] == {
        "high_volatility_low_entry_quality": 1
    }
    assert summary["conditional_regime_rule_passed_counts"] == {
        "high_volatility_low_entry_quality": 1
    }
    assert summary["conditional_regime_rule_metric_failure_counts"] == {
        "entry_path_quality_below": 1
    }
    assert summary["conditional_regime_rule_metric_failure_counts_by_rule"] == {
        "high_volatility_low_entry_quality": {"entry_path_quality_below": 1}
    }

    removed_stats = summary["conditional_regime_rule_removed_outcome_by_rule"][
        "high_volatility_low_entry_quality"
    ]
    passed_stats = summary["conditional_regime_rule_passed_outcome_by_rule"][
        "high_volatility_low_entry_quality"
    ]

    assert removed_stats["signal_count"] == 1
    assert removed_stats["total_r"] < 0
    assert passed_stats["signal_count"] == 1
    assert passed_stats["total_r"] > 0

    board = summary["conditional_regime_ablation_board"]
    assert board[0]["rule_id"] == "high_volatility_low_entry_quality"
    assert board[0]["eligible_count"] == 2
    assert board[0]["removed_count"] == 1
    assert board[0]["passed_count"] == 1
    assert board[0]["effect_label"] == "REMOVAL_HELPFUL"


def test_probe_aggregates_conditional_regime_ablation_and_contribution_board():
    candidates = [
        {
            "symbol": "SOLUSDT",
            "config_id": "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_exit45_probe",
            "fold_repair_feature_filter_enabled": True,
            "fold_feature_regime_filter_summary": {
                "input_signal_count": 82,
                "removed_signal_count": 1,
                "conditional_regime_rule_counts": {
                    "high_volatility_low_entry_quality": 1
                },
                "conditional_regime_rule_eligible_counts": {
                    "high_volatility_low_entry_quality": 2
                },
                "conditional_regime_rule_passed_counts": {
                    "high_volatility_low_entry_quality": 1
                },
                "conditional_regime_rule_metric_failure_counts": {
                    "entry_path_quality_below": 1
                },
                "conditional_regime_rule_metric_failure_counts_by_rule": {
                    "high_volatility_low_entry_quality": {
                        "entry_path_quality_below": 1
                    }
                },
                "conditional_regime_rule_removed_outcome_by_rule": {
                    "high_volatility_low_entry_quality": {
                        "signal_count": 1,
                        "total_r": -1.0,
                        "positive_r": 0.0,
                        "negative_r": -1.0,
                        "win_count": 0,
                        "loss_count": 1,
                        "neutral_count": 0,
                    }
                },
                "conditional_regime_rule_passed_outcome_by_rule": {
                    "high_volatility_low_entry_quality": {
                        "signal_count": 1,
                        "total_r": 0.8,
                        "positive_r": 0.8,
                        "negative_r": 0.0,
                        "win_count": 1,
                        "loss_count": 0,
                        "neutral_count": 0,
                    }
                },
                "removed_outcome_by_primary_regime": {
                    "trend_down": {
                        "signal_count": 1,
                        "total_r": -1.0,
                        "negative_r": -1.0,
                        "loss_count": 1,
                    }
                },
                "passed_outcome_by_primary_regime": {
                    "trend_down": {
                        "signal_count": 1,
                        "total_r": 0.8,
                        "positive_r": 0.8,
                        "win_count": 1,
                    }
                },
                "regime_source_counts": {"features_json_regime_flags": 82},
                "missing_feature_counts": {},
            },
            "profit_factor": 1.34,
            "profit_total_r": 8.27,
            "walk_forward_total_r": 0.0,
        }
    ]

    result = FoldFeatureRegimeRepairProbe().analyze(candidates)
    diagnostics = result["feature_filter_diagnostics"]

    assert diagnostics["conditional_regime_filter_status"] == (
        "CONDITIONAL_REGIME_FILTER_ACTIVE"
    )
    assert diagnostics["aggregate_conditional_regime_rule_eligible_counts"] == {
        "high_volatility_low_entry_quality": 2
    }
    assert diagnostics["aggregate_conditional_regime_rule_passed_counts"] == {
        "high_volatility_low_entry_quality": 1
    }
    assert diagnostics["aggregate_conditional_regime_rule_metric_failure_counts"] == {
        "entry_path_quality_below": 1
    }

    board = diagnostics["aggregate_conditional_regime_ablation_board"]
    assert board[0]["rule_id"] == "high_volatility_low_entry_quality"
    assert board[0]["removed_outcome"]["total_r"] == -1.0
    assert board[0]["passed_outcome"]["total_r"] == 0.8
    assert board[0]["effect_label"] == "REMOVAL_HELPFUL"

    regime_board = diagnostics["aggregate_per_regime_contribution_board"]
    assert regime_board[0]["market_regime"] == "trend_down"


def test_reporter_compacts_conditional_ablation_board_without_losing_counts():
    summary = {
        "conditional_regime_rule_eligible_counts": {
            "high_volatility_low_entry_quality": 2
        },
        "conditional_regime_rule_passed_counts": {
            "high_volatility_low_entry_quality": 1
        },
        "conditional_regime_rule_metric_failure_counts": {
            "entry_path_quality_below": 1
        },
        "conditional_regime_rule_removed_outcome_by_rule": {
            "high_volatility_low_entry_quality": {
                "signal_count": 1,
                "total_r": -1.0,
                "negative_r": -1.0,
                "loss_count": 1,
            }
        },
        "conditional_regime_ablation_board": [
            {
                "rule_id": "high_volatility_low_entry_quality",
                "eligible_count": 2,
                "removed_count": 1,
                "passed_count": 1,
                "effect_label": "REMOVAL_HELPFUL",
            }
        ],
        "per_regime_contribution_board": [
            {
                "market_regime": "trend_down",
                "removed_total_r": -1.0,
                "passed_total_r": 0.8,
                "effect_label": "REMOVAL_HELPFUL",
            }
        ],
    }

    compact = FeatureRegimeExperimentReporter._compact_fold_feature_summary(summary)

    assert compact["conditional_regime_rule_eligible_counts"] == {
        "high_volatility_low_entry_quality": 2
    }
    assert compact["conditional_regime_rule_passed_counts"] == {
        "high_volatility_low_entry_quality": 1
    }
    assert compact["conditional_regime_rule_metric_failure_counts"] == {
        "entry_path_quality_below": 1
    }
    assert compact["conditional_regime_rule_removed_outcome_by_rule"][
        "high_volatility_low_entry_quality"
    ]["total_r"] == -1.0
    assert compact["conditional_regime_ablation_board"][0]["rule_id"] == (
        "high_volatility_low_entry_quality"
    )


def test_ml38_10_32_does_not_change_runtime_counts():
    assert len(FAST_DEBUG_CONFIGS) == 18
    assert len(QUICK_QUALITY_CONFIGS) == 38
