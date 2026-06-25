from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner
import run_fv3_cached_tuning


def _row(future_candles: list[dict]) -> dict:
    return {
        "predicted_label": "UP",
        "entry_path_original_predicted_label": "UP",
        "entry_path_filtered_predicted_label": "UP",
        "actual_label": "UP",
        "prob_up": 0.80,
        "prob_down": 0.10,
        "prob_flat": 0.10,
        "confidence": 0.80,
        "margin": 0.70,
        "directional_edge": 0.70,
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": future_candles,
        "future_move_atr": -0.8,
        "entry_path_filter_enabled": True,
        "entry_path_filter_blocked": False,
        "entry_path_filter_block_reason": None,
        "entry_path_filter_threshold": 0.70,
        "entry_path_filter_stop_threshold": 0.45,
        "entry_path_filter_mae_threshold": 0.52,
        "entry_path_quality_score": 0.78,
        "stop_pressure_risk_score": 0.20,
        "mae_pressure_risk_score": 0.20,
    }


def test_ml38_10_18_exit_path_audit_separates_saved_sl_from_premature_recovery_cut() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    saved = evaluator.evaluate_single_gate(
        predictions=[_row([
            {"high": 100.2, "low": 99.05, "close": 99.10},
            {"high": 99.20, "low": 98.40, "close": 98.50},
        ])],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.4,
        exit_policy_profile="stop_loss_mitigation_v1",
        exit_timeout_bars=9,
        exit_mitigation_loss_r=0.62,
        exit_neutral_abs_r=0.15,
    )
    premature = evaluator.evaluate_single_gate(
        predictions=[_row([
            {"high": 100.2, "low": 99.05, "close": 99.10},
            {"high": 101.3, "low": 99.50, "close": 101.0},
        ])],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.4,
        exit_policy_profile="stop_loss_mitigation_v1",
        exit_timeout_bars=9,
        exit_mitigation_loss_r=0.62,
        exit_neutral_abs_r=0.15,
    )
    assert saved["outcomes"][0]["result"] == "EXIT_MITIGATED"
    assert saved["outcomes"][0]["exit_mitigation_path_class"] == "SAVED_FULL_SL"
    assert saved["summary"]["exit_mitigation_saved_full_sl_count"] == 1
    assert premature["outcomes"][0]["result"] == "EXIT_MITIGATED"
    assert premature["outcomes"][0]["exit_mitigation_path_class"] == "PREMATURE_CUT_TP_RECOVERY"
    assert premature["summary"]["exit_mitigation_premature_recovery_count"] == 1
    audit = premature["summary"]["profit_exit_root_cause_audit"]
    assert audit["diagnostic_version"] == "ml38.10.18"
    assert audit["exit_mitigation_premature_recovery_count"] == 1
    assert audit["root_cause_counts"]["exit_mitigation_premature_recovery_cut"] == 1


def test_ml38_10_18_recovery_guard_skips_premature_mitigation_when_recovery_would_happen_first() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    row = _row([
        {"high": 100.2, "low": 99.05, "close": 99.10},
        {"high": 101.3, "low": 99.50, "close": 101.0},
    ])
    classic_mitigation = evaluator.evaluate_single_gate(
        predictions=[row],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.4,
        exit_policy_profile="stop_loss_mitigation_v1",
        exit_timeout_bars=9,
        exit_mitigation_loss_r=0.62,
        exit_neutral_abs_r=0.15,
    )
    guarded = evaluator.evaluate_single_gate(
        predictions=[row],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.4,
        exit_policy_profile="stop_loss_mitigation_recovery_guard_v1",
        exit_timeout_bars=9,
        exit_mitigation_loss_r=0.62,
        exit_neutral_abs_r=0.15,
    )
    assert classic_mitigation["outcomes"][0]["result"] == "EXIT_MITIGATED"
    assert guarded["outcomes"][0]["result"] == "TP"
    assert guarded["summary"]["exit_mitigated_count"] == 0
    assert guarded["summary"]["win_count"] == 1


def test_ml38_10_18_matrix_and_runtime_include_lv26_recovery_guard_configs() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}
    assert grid["exit_mitigation_path_audit_stage"] == "ML38.10.18"
    assert "lv26_h08_tts_thr065_sqmask060_epq070_sp045_recovery_guard" in configs_by_id
    assert "lv26_h12_tts_thr065_sqmask060_epq070_sp045_recovery_guard" in configs_by_id
    assert "lv26_h12_tts_thr065_sqmask060_epq072_sp043_recovery_guard_strict" in configs_by_id
    primary = configs_by_id["lv26_h12_tts_thr065_sqmask060_epq070_sp045_recovery_guard"]
    assert primary["exit_policy_profile"] == "stop_loss_mitigation_recovery_guard_v1"
    assert len(primary["label_version"]) <= 50
    matrix = ML382FV3TuningMatrix().build()
    assert matrix["exit_mitigation_path_audit_stage"] == "ML38.10.18"
    assert "lv26_h12_tts_thr065_sqmask060_epq070_sp045_recovery_guard" in matrix["config_ids"]
    assert "lv26_h08_tts_thr065_sqmask060_epq070_sp045_recovery_guard" in run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
    assert "lv26_h12_tts_thr065_sqmask060_epq070_sp045_recovery_guard" in run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
