from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner
import run_fv3_cached_tuning


def _row(*, direction: str = "UP", future_candles: list[dict] | None = None) -> dict:
    return {
        "predicted_label": direction,
        "entry_path_original_predicted_label": direction,
        "entry_path_filtered_predicted_label": direction,
        "actual_label": direction,
        "prob_up": 0.80 if direction == "UP" else 0.10,
        "prob_down": 0.80 if direction == "DOWN" else 0.10,
        "prob_flat": 0.10,
        "confidence": 0.80,
        "margin": 0.70,
        "directional_edge": 0.70,
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": future_candles or [{"high": 100.2, "low": 99.05, "close": 99.2}],
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


def test_ml38_10_17_exit_policy_can_mitigate_before_full_stop_loss() -> None:
    evaluator = ProfitAwareEvaluatorV2()

    classic = evaluator.evaluate_single_gate(
        predictions=[_row(future_candles=[{"high": 100.2, "low": 98.55, "close": 98.70}])],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.4,
    )
    mitigated = evaluator.evaluate_single_gate(
        predictions=[_row(future_candles=[{"high": 100.2, "low": 99.05, "close": 99.15}])],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.4,
        exit_policy_profile="stop_loss_mitigation_v1",
        exit_timeout_bars=9,
        exit_mitigation_loss_r=0.62,
        exit_neutral_abs_r=0.15,
    )

    assert classic["outcomes"][0]["result"] == "SL"
    assert mitigated["outcomes"][0]["result"] == "EXIT_MITIGATED"
    assert mitigated["summary"]["exit_mitigated_count"] == 1
    assert mitigated["summary"]["loss_count"] == 0
    audit = mitigated["summary"]["profit_exit_root_cause_audit"]
    assert audit["diagnostic_version"] == "ml38.10.18"
    assert audit["exit_policy_profile"] == "stop_loss_mitigation_v1"
    assert audit["exit_mitigated_count"] == 1
    assert audit["root_cause_counts"]["stop_loss_mitigated_before_full_sl"] == 1


def test_ml38_10_17_timeout_neutral_exit_is_reported() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    payload = evaluator.evaluate_single_gate(
        predictions=[_row(future_candles=[{"high": 100.05, "low": 99.95, "close": 100.03}])],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.4,
        exit_policy_profile="stop_loss_mitigation_v1",
        exit_timeout_bars=1,
        exit_mitigation_loss_r=0.62,
        exit_neutral_abs_r=0.15,
    )
    assert payload["outcomes"][0]["result"] == "TIMEOUT_NEUTRAL"
    assert payload["summary"]["timeout_neutral_count"] == 1
    assert payload["summary"]["profit_exit_root_cause_audit"]["timeout_neutral_count"] == 1


def test_ml38_10_17_matrix_and_runtime_include_lv25_exit_configs() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}
    assert grid["exit_outcome_stop_loss_mitigation_stage"] == "ML38.10.17"
    assert "lv25_h08_tts_thr065_sqmask060_epq070_sp045_exit_mit" in configs_by_id
    assert "lv25_h12_tts_thr065_sqmask060_epq070_sp045_exit_mit" in configs_by_id
    assert "lv25_h12_tts_thr065_sqmask060_epq072_sp043_exit_mit_strict" in configs_by_id

    primary = configs_by_id["lv25_h12_tts_thr065_sqmask060_epq070_sp045_exit_mit"]
    assert primary["exit_policy_profile"] == "stop_loss_mitigation_v1"
    assert primary["exit_timeout_bars"] == 9
    assert primary["exit_mitigation_loss_r"] == 0.62
    assert primary["exit_neutral_abs_r"] == 0.15

    matrix = ML382FV3TuningMatrix().build()
    assert matrix["exit_outcome_stop_loss_mitigation_stage"] == "ML38.10.17"
    assert "lv25_h12_tts_thr065_sqmask060_epq070_sp045_exit_mit" in matrix["config_ids"]
    assert "lv25_h08_tts_thr065_sqmask060_epq070_sp045_exit_mit" in run_fv3_cached_tuning.FAST_DEBUG_CONFIGS
    assert "lv25_h12_tts_thr065_sqmask060_epq070_sp045_exit_mit" in run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS
