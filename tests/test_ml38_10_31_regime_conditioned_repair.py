from __future__ import annotations

from app.diagnostics.fold_feature_regime_repair_probe import (
    FoldFeatureRegimeRepairProbe,
)
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.labels.label_quality_grid import LabelQualityGridPlanner
from run_fv3_cached_tuning import FAST_DEBUG_CONFIGS, QUICK_QUALITY_CONFIGS


def test_conditional_regime_rule_blocks_only_bad_high_volatility_entry():
    evaluator = ProfitAwareEvaluatorV2()
    signal_rows = [
        {
            "signal_date": "2026-06-09",
            "market_regime": "trend_up",
            "active_regime_flags": ["trend_up", "high_volatility"],
            "entry_path_quality_score": 0.70,
            "setup_quality_score": 0.70,
            "stop_pressure_risk_score": 0.20,
            "mae_pressure_risk_score": 0.20,
        },
        {
            "signal_date": "2026-06-10",
            "market_regime": "trend_up",
            "active_regime_flags": ["trend_up", "high_volatility"],
            "entry_path_quality_score": 0.80,
            "setup_quality_score": 0.70,
            "stop_pressure_risk_score": 0.20,
            "mae_pressure_risk_score": 0.20,
        },
    ]

    filtered, summary = evaluator._apply_fold_feature_regime_filter(
        signal_rows=signal_rows,
        enabled=True,
        profile="TEST_CONDITIONAL_REGIME",
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
    )

    assert len(filtered) == 1
    assert summary["removed_signal_count"] == 1
    assert summary["conditional_regime_rule_counts"] == {
        "high_volatility_low_entry_quality": 1
    }
    assert summary["primary_removed_counts_by_reason"] == {
        "conditional_regime_rule:high_volatility_low_entry_quality": 1
    }


def test_conditional_regime_rules_do_not_hard_block_regime_without_metric_failure():
    evaluator = ProfitAwareEvaluatorV2()
    signal_rows = [
        {
            "signal_date": "2026-06-09",
            "market_regime": "trend_up",
            "active_regime_flags": ["trend_up", "high_volatility"],
            "entry_path_quality_score": 0.80,
            "setup_quality_score": 0.70,
            "stop_pressure_risk_score": 0.20,
            "mae_pressure_risk_score": 0.20,
        },
    ]

    filtered, summary = evaluator._apply_fold_feature_regime_filter(
        signal_rows=signal_rows,
        enabled=True,
        profile="TEST_CONDITIONAL_REGIME",
        rules={
            "blocked_regime_values": ["high_volatility"],
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
        target_dates=(),
        date_blackout_used=False,
    )

    assert len(filtered) == 1
    assert summary["removed_signal_count"] == 0
    assert summary["matched_removed_counts_by_reason"] == {}


def test_lv34_regime_conditioned_configs_registered_and_research_only():
    grid = LabelQualityGridPlanner().build_grid()
    configs = {item["config_id"]: item for item in grid["configs"]}

    expected_ids = {
        "lv34_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_probe",
        "lv34_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_exit45_probe",
        "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_probe",
        "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_exit45_probe",
        "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_cond_regime_probe",
        "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_cond_regime_exit45_probe",
    }

    assert expected_ids.issubset(configs)

    for config_id in expected_ids:
        config = configs[config_id]
        rules = config["fold_repair_feature_filter_rules"]
        assert config["research_only_fold_repair_probe_enabled"] is True
        assert config["fold_repair_time_slice_blackout_enabled"] is False
        assert config["fold_repair_feature_filter_enabled"] is True
        assert rules["disable_unconditional_blocked_regime"] is True
        assert rules["conditional_regime_rules"]
        assert config["research_only_acceptance_block_reason"] == (
            "research_only_conditional_regime_fold_repair_probe"
        )


def test_ml38_10_31_runtime_counts_include_lv34_configs():
    assert len(FAST_DEBUG_CONFIGS) == 18
    assert len(QUICK_QUALITY_CONFIGS) == 38
    assert "lv34_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_probe" in FAST_DEBUG_CONFIGS
    assert "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_probe" in QUICK_QUALITY_CONFIGS


def test_fold_feature_probe_aggregates_conditional_regime_rules():
    candidates = [
        {
            "symbol": "SOLUSDT",
            "config_id": "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_exit45_probe",
            "fold_repair_feature_filter_enabled": True,
            "fold_feature_regime_filter_summary": {
                "input_signal_count": 82,
                "removed_signal_count": 2,
                "conditional_regime_rule_counts": {
                    "high_volatility_low_entry_quality": 2
                },
                "conditional_regime_rule_counts_by_primary_regime": {
                    "trend_up": 2
                },
                "conditional_regime_rule_counts_by_active_flag": {
                    "high_volatility": 2
                },
                "removed_counts_by_regime": {"trend_up": 2},
                "regime_source_counts": {"features_json_regime_flags": 82},
                "missing_feature_counts": {},
            },
            "profit_factor": 1.1,
            "profit_total_r": 2.0,
            "walk_forward_total_r": 0.0,
        }
    ]

    result = FoldFeatureRegimeRepairProbe().analyze(candidates)
    diagnostics = result["feature_filter_diagnostics"]

    assert diagnostics["conditional_regime_filter_status"] == (
        "CONDITIONAL_REGIME_FILTER_ACTIVE"
    )
    assert diagnostics["aggregate_conditional_regime_rule_counts"] == {
        "high_volatility_low_entry_quality": 2
    }
