from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.labels.label_quality_grid import LabelQualityGridPlanner
from app.experiments.ml38_2_fv3_tuning_matrix import (
    ML38_10_33_TARGETED_CONDITIONAL_REGIME_REPAIR_CONFIG_IDS,
    ML382FV3TuningMatrix,
)
from run_fv3_cached_tuning import FAST_DEBUG_CONFIGS, QUICK_QUALITY_CONFIGS
import run_fv3_cached_tuning


def test_metric_logic_all_requires_all_metric_failures():
    evaluator = ProfitAwareEvaluatorV2()
    signal_rows = [
        {
            "signal_date": "2026-06-09",
            "signal_direction": "LONG",
            "market_regime": "trend_down",
            "active_regime_flags": ["trend_down", "high_volatility"],
            "entry_path_quality_score": 0.69,
            "setup_quality_score": 0.70,
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
            "setup_quality_score": 0.70,
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
        profile="TEST_LV35_METRIC_LOGIC_ALL",
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
    assert summary["conditional_regime_rule_eligible_counts"] == {
        "hv_low_entry_and_high_stop": 2
    }
    assert summary["conditional_regime_rule_counts"] == {
        "hv_low_entry_and_high_stop": 1
    }
    assert summary["conditional_regime_rule_passed_counts"] == {
        "hv_low_entry_and_high_stop": 1
    }
    assert summary["conditional_regime_rule_metric_logic"] == {
        "hv_low_entry_and_high_stop": "all"
    }
    assert summary["conditional_regime_rule_required_metric_failure_count"] == {
        "hv_low_entry_and_high_stop": 2
    }

    board = summary["conditional_regime_ablation_board"]
    assert board[0]["rule_id"] == "hv_low_entry_and_high_stop"
    assert board[0]["metric_logic"] == "all"
    assert board[0]["required_metric_failure_count"] == 2
    assert board[0]["metric_condition_count"] == 2


def test_metric_logic_any_remains_backward_compatible_for_lv34_rules():
    evaluator = ProfitAwareEvaluatorV2()
    signal_rows = [
        {
            "signal_date": "2026-06-09",
            "signal_direction": "LONG",
            "market_regime": "trend_down",
            "active_regime_flags": ["trend_down", "high_volatility"],
            "entry_path_quality_score": 0.70,
            "setup_quality_score": 0.70,
            "stop_pressure_risk_score": 0.20,
            "mae_pressure_risk_score": 0.20,
        }
    ]

    filtered, summary = evaluator._apply_fold_feature_regime_filter(
        signal_rows=signal_rows,
        enabled=True,
        profile="TEST_LV34_COMPAT",
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
        target_dates=(),
        date_blackout_used=False,
    )

    assert filtered == []
    assert summary["conditional_regime_rule_counts"] == {
        "high_volatility_low_entry_quality": 1
    }
    assert summary["conditional_regime_rule_metric_logic"] == {
        "high_volatility_low_entry_quality": "any"
    }


def test_lv35_targeted_conditional_regime_configs_registered_and_research_only():
    grid = LabelQualityGridPlanner().build_grid()
    configs = {item["config_id"]: item for item in grid["configs"]}

    expected_ids = {
        "lv35_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_targeted_cond_regime_probe",
        "lv35_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_targeted_cond_regime_exit45_probe",
        "lv35_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_targeted_cond_regime_probe",
        "lv35_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_targeted_cond_regime_exit45_probe",
        "lv35_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_targeted_cond_regime_probe",
        "lv35_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_targeted_cond_regime_exit45_probe",
    }

    assert expected_ids.issubset(configs)
    assert grid["targeted_conditional_regime_repair_stage"] == "ML38.10.33"

    for config_id in expected_ids:
        config = configs[config_id]
        rules = config["fold_repair_feature_filter_rules"]
        rule_ids = {rule["rule_id"] for rule in rules["conditional_regime_rules"]}

        assert config["research_only_fold_repair_probe_enabled"] is True
        assert config["fold_repair_time_slice_blackout_enabled"] is False
        assert config["fold_repair_feature_filter_enabled"] is True
        assert config["research_only_acceptance_block_reason"] == (
            "research_only_lv35_targeted_conditional_regime_fold_repair_probe"
        )

        assert rules["disable_unconditional_blocked_regime"] is True
        assert "high_volatility_low_entry_quality" not in rule_ids

        for rule in rules["conditional_regime_rules"]:
            assert rule["metric_logic"] == "all"
            assert rule["min_metric_failure_count"] == 2


def test_lv35_targeted_configs_registered_in_matrix_and_runtime_shortlists():
    matrix = ML382FV3TuningMatrix().build()
    matrix_ids = set(matrix["config_ids"])

    assert matrix["targeted_conditional_regime_repair_stage"] == "ML38.10.33"

    for config_id in ML38_10_33_TARGETED_CONDITIONAL_REGIME_REPAIR_CONFIG_IDS:
        assert config_id in matrix_ids

    assert len(FAST_DEBUG_CONFIGS) == 20
    assert len(QUICK_QUALITY_CONFIGS) == 42

    assert (
        "lv35_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_targeted_cond_regime_probe"
        in FAST_DEBUG_CONFIGS
    )
    assert (
        "lv35_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_targeted_cond_regime_probe"
        in QUICK_QUALITY_CONFIGS
    )


def test_ml38_10_33_future_expected_candidate_counts():
    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--fast-debug"])
    )
    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(
            ["--quick-quality", "--quick-quality-symbol", "SOLUSDT"]
        )
    )

    assert fast_wrapper._expected_candidate_count() == 40
    assert quick_wrapper._expected_candidate_count() == 42
