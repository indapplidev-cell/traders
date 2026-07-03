import json
from pathlib import Path

from app.diagnostics.fold_feature_regime_repair_probe import (
    FoldFeatureRegimeRepairProbe,
)
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.ml38_2_fv3_tuning_matrix import (
    ML38_10_35_METRIC_RELAXATION_PROBE_CONFIG_IDS,
    ML382FV3TuningMatrix,
)
from app.experiments.multi_symbol_feature_regime_analyzer import (
    MultiSymbolFeatureRegimeAnalyzer,
)
from app.labels.label_quality_grid import LabelQualityGridPlanner
import run_fv3_cached_tuning as wrapper


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


def test_lv36_relaxation_probe_board_reports_hypothetical_min_count_1_outcome():
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
            "future_candles": [{"high": 100.2, "low": 98.7, "close": 99.1}],
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

    _filtered, summary = evaluator._apply_fold_feature_regime_filter(
        signal_rows=signal_rows,
        enabled=True,
        profile="TEST_ML38_10_35_RELAXATION",
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

    board = summary["conditional_regime_rule_relaxation_probe_board"]
    assert board[0]["rule_id"] == "hv_low_entry_and_high_stop"
    assert board[0]["actual_removed_count"] == 1
    assert board[0]["hypothetical_min_count_1_removed_count"] == 2
    assert (
        board[0]["relaxation_effect_label"]
        == "RELAXATION_POTENTIALLY_HELPFUL"
    )


def test_fold_feature_regime_probe_aggregates_relaxation_probe_board():
    probe = FoldFeatureRegimeRepairProbe()
    diagnostics = probe._feature_filter_diagnostics(
        [
            {
                "config_id": "lv35_test",
                "fold_feature_regime_filter_summary": {
                    "removed_signal_count": 1,
                    "conditional_regime_rule_eligible_counts": {
                        "hv_low_entry_and_high_stop": 3
                    },
                    "conditional_regime_rule_blocked_counts": {
                        "hv_low_entry_and_high_stop": 1
                    },
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
                        "hv_low_entry_and_high_stop": {
                            "failed_0": 1,
                            "failed_1": 1,
                            "failed_2_plus": 1,
                        }
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
                            },
                            "failed_2_plus": {
                                "signal_count": 1,
                                "total_r": -1.0,
                                "positive_r": 0.0,
                                "negative_r": -1.0,
                                "win_count": 0,
                                "loss_count": 1,
                                "neutral_count": 0,
                            },
                        }
                    },
                },
            }
        ]
    )

    board = diagnostics["aggregate_conditional_regime_rule_relaxation_probe_board"]
    assert board
    assert board[0]["hypothetical_min_count_1_removed_count"] == 2
    assert (
        board[0]["relaxation_effect_label"]
        == "RELAXATION_POTENTIALLY_HELPFUL"
    )
    assert diagnostics["aggregate_conditional_regime_relaxation_probe_summary"][
        "diagnostic_name"
    ] == "conditional_regime_relaxation_probe_summary"


def test_multi_symbol_analyzer_exposes_top_level_relaxation_aliases(tmp_path: Path):
    experiment_dir = tmp_path / "exp1"
    experiment_dir.mkdir(parents=True, exist_ok=True)
    summary_path = experiment_dir / "feature_regime_experiment_summary.json"
    payload = {
        "experiment_id": "exp1",
        "symbol": "SOLUSDT",
        "interval": "15m",
        "start_date": "2025-01-01",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "candidate_count": 1,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "lv36_test",
        "best_candidate_score": -1.0,
        "feature_version_used": "fv4_book_setup_context",
        "real_feature_diagnostics_used": True,
        "real_feature_diagnostics_row_count": 1,
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "gap_training_safe": True,
        "regime_features_attached": True,
        "regime_specific_training_applied": False,
        "warnings": [],
        "candidate_results": [
            {
                "symbol": "SOLUSDT",
                "config_id": "lv36_test",
                "candidate_status": "CANDIDATE_REJECTED",
                "score": -1.0,
                "model_accuracy": 0.41,
                "baseline_accuracy": 0.39,
                "accuracy_edge": 0.02,
                "baseline_edge": 0.02,
                "baseline_edge_status": "STRONG_EDGE",
                "collapse_detected": True,
                "collapse_type": "MIXED_COLLAPSE",
                "collapse_severity": "WATCH",
                "profit_factor": 0.9,
                "profit_total_r": -1.5,
                "walk_forward_profit_factor": 0.85,
                "walk_forward_global_total_r": -2.0,
                "failed_gates": ["walk_forward_gate"],
                "passed_gates": ["gap_quality_gate"],
                "warnings": [],
                "fold_repair_feature_filter_enabled": True,
                "fold_repair_feature_filter_profile": "TARGETED_CONDITIONAL_REGIME_MIN1_RELAX_PROBE_V1",
                "fold_feature_regime_filter_summary": {
                    "removed_signal_count": 1,
                    "conditional_regime_rule_eligible_counts": {
                        "hv_low_entry_and_high_stop": 3
                    },
                    "conditional_regime_rule_blocked_counts": {
                        "hv_low_entry_and_high_stop": 1
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
                        "hv_low_entry_and_high_stop": {
                            "failed_0": 1,
                            "failed_1": 1,
                            "failed_2_plus": 1,
                        }
                    },
                    "conditional_regime_rule_observed_metric_failure_counts_by_rule": {
                        "hv_low_entry_and_high_stop": {
                            "entry_path_quality_below": 2,
                            "stop_pressure_above": 1,
                        }
                    },
                    "conditional_regime_rule_metric_pair_failure_counts_by_rule": {
                        "hv_low_entry_and_high_stop": {
                            "entry_path_quality_below+stop_pressure_above": 1
                        }
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
                            },
                            "failed_2_plus": {
                                "signal_count": 1,
                                "total_r": -1.0,
                                "positive_r": 0.0,
                                "negative_r": -1.0,
                                "win_count": 0,
                                "loss_count": 1,
                                "neutral_count": 0,
                            },
                        }
                    },
                    "conditional_regime_metric_overlap_board": [
                        {
                            "rule_id": "hv_low_entry_and_high_stop",
                            "eligible_count": 3,
                            "actual_removed_count": 1,
                            "failed_0_count": 1,
                            "failed_1_count": 1,
                            "failed_2_plus_count": 1,
                        }
                    ],
                    "conditional_regime_rule_relaxation_probe_board": [
                        {
                            "rule_id": "hv_low_entry_and_high_stop",
                            "eligible_count": 3,
                            "actual_removed_count": 1,
                            "failed_1_count": 1,
                            "failed_2_plus_count": 1,
                            "hypothetical_min_count_1_removed_count": 2,
                            "hypothetical_min_count_1_total_r": -1.5,
                            "hypothetical_min_count_1_win_rate": 0.0,
                            "relaxation_effect_label": "RELAXATION_POTENTIALLY_HELPFUL",
                            "recommended_action": "review_as_research_only_probe_not_trading_rule",
                        }
                    ],
                    "conditional_regime_relaxation_probe_summary": {
                        "diagnostic_name": "conditional_regime_relaxation_probe_summary",
                        "diagnostic_version": "ml38.10.35",
                        "rule_count": 1,
                        "effect_counts": {
                            "RELAXATION_POTENTIALLY_HELPFUL": 1
                        },
                        "recommended_action_counts": {
                            "review_as_research_only_probe_not_trading_rule": 1
                        },
                        "potentially_helpful_rule_ids": [
                            "hv_low_entry_and_high_stop"
                        ],
                        "harmful_rule_ids": [],
                        "research_only_warning": "min_count_1_relaxation_is_diagnostic_only_not_a_trading_rule",
                    },
                },
            }
        ],
        "configs_ranked": [],
    }
    summary_path.write_text(json.dumps(payload), encoding="utf-8")

    result = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])

    assert "aggregate_conditional_regime_metric_overlap_board" in result
    assert (
        "aggregate_conditional_regime_rule_metric_failure_count_distribution_by_rule"
        in result
    )
    assert "aggregate_conditional_regime_rule_relaxation_probe_board" in result
    assert "aggregate_conditional_regime_relaxation_probe_summary" in result
    assert (
        result["feature_filter_diagnostics_top_level_source"]
        == "fold_feature_regime_adaptive_repair_probe.feature_filter_diagnostics"
    )


def test_ml38_10_35_metric_relaxation_configs_registered_and_research_only():
    grid = LabelQualityGridPlanner().build_grid()
    by_id = {item["config_id"]: item for item in grid["configs"]}
    for config_id in ML38_10_35_METRIC_RELAXATION_PROBE_CONFIG_IDS:
        assert config_id in by_id
        config = by_id[config_id]
        assert config["experimental"] is True
        assert (
            config["research_only_acceptance_block_reason"]
            == "research_only_lv36_metric_relaxation_probe"
        )
        rules = config["fold_repair_feature_filter_rules"]
        assert rules["research_only"] is True
        assert rules["relaxation_probe_only"] is True
        for rule in rules["conditional_regime_rules"]:
            assert rule["metric_logic"] == "min_count"
            assert rule["min_metric_failure_count"] == 1
            assert rule["relaxation_probe_only"] is True

    matrix = ML382FV3TuningMatrix().build()
    matrix_ids = set(matrix["config_ids"])
    for config_id in ML38_10_35_METRIC_RELAXATION_PROBE_CONFIG_IDS:
        assert config_id in matrix_ids


def test_ml38_10_35_shortlist_counts():
    assert len(wrapper.FAST_DEBUG_CONFIGS) == 22
    assert len(wrapper.QUICK_QUALITY_CONFIGS) == 46
    for config_id in (
        "lv36_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_probe",
        "lv36_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_exit45_probe",
    ):
        assert config_id in wrapper.FAST_DEBUG_CONFIGS
    for config_id in (
        "lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_probe",
        "lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_exit45_probe",
        "lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_metric_relax_probe",
        "lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_metric_relax_exit45_probe",
    ):
        assert config_id in wrapper.QUICK_QUALITY_CONFIGS
