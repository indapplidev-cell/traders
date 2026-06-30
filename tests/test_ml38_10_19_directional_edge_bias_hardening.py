from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner
import run_fv3_cached_tuning


def _row(direction: str, future_candles: list[dict]) -> dict:
    direction = direction.upper()
    return {
        "predicted_label": "UP" if direction == "LONG" else "DOWN",
        "entry_path_original_predicted_label": "UP" if direction == "LONG" else "DOWN",
        "entry_path_filtered_predicted_label": "UP" if direction == "LONG" else "DOWN",
        "actual_label": "UP" if direction == "LONG" else "DOWN",
        "prob_up": 0.80 if direction == "LONG" else 0.10,
        "prob_down": 0.80 if direction == "SHORT" else 0.10,
        "prob_flat": 0.10,
        "confidence": 0.80,
        "margin": 0.70,
        "directional_edge": 0.70,
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": future_candles,
        "future_move_atr": -0.8 if direction == "LONG" else 0.8,
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


def test_ml38_10_19_profit_evaluator_reports_directional_edge_bias_audit() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    payload = evaluator.evaluate_single_gate(
        predictions=[
            _row("LONG", [{"high": 100.2, "low": 98.5, "close": 98.6}]),
            _row("LONG", [{"high": 100.2, "low": 98.5, "close": 98.6}]),
            _row("LONG", [{"high": 100.2, "low": 98.5, "close": 98.6}]),
            _row("SHORT", [{"high": 100.2, "low": 98.7, "close": 98.8}]),
        ],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.4,
        exit_policy_profile="stop_loss_mitigation_recovery_guard_v1",
        exit_timeout_bars=9,
        exit_mitigation_loss_r=0.62,
        exit_neutral_abs_r=0.15,
    )
    summary = payload["summary"]
    audit = summary["directional_edge_bias_audit"]
    assert audit["diagnostic_name"] == "directional_edge_bias_audit"
    assert audit["diagnostic_version"] == "ml38.10.19"
    assert audit["long_count"] == 3
    assert audit["short_count"] == 1
    assert audit["dominant_direction"] == "LONG"
    assert audit["directional_edge_bias_warning"] is True
    assert "DIRECTION_COUNT_IMBALANCE" in audit["warnings"]
    assert summary["direction_balance_ratio"] == audit["direction_balance_ratio"]
    assert summary["directional_profit_skew_r"] == audit["directional_profit_skew_r"]


def test_ml38_10_19_grid_matrix_and_runtime_include_lv27_dirbias_configs() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}
    assert grid["directional_edge_bias_hardening_stage"] == "ML38.10.19"
    assert "lv27_h08_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias" in configs_by_id
    assert "lv27_h12_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias" in configs_by_id
    assert "lv27_h12_tts_thr065_sqmask060_epq072_sp043_rguard_dirbias_strict" in configs_by_id

    primary = configs_by_id["lv27_h12_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias"]
    assert primary["exit_policy_profile"] == "stop_loss_mitigation_recovery_guard_v1"
    assert primary["decision_policy_grid_stage"] == "ML38.10.19"
    assert primary["decision_max_dominant_class_ratio"] <= 0.82
    assert primary["decision_min_down_ratio_when_actual_down_high"] >= 0.08
    assert primary["decision_min_up_ratio_when_actual_up_high"] >= 0.08
    assert len(primary["label_version"]) <= 50

    matrix = ML382FV3TuningMatrix().build()
    assert matrix["directional_edge_bias_hardening_stage"] == "ML38.10.19"
    assert "lv27_h12_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias" in matrix["config_ids"]
    assert run_fv3_cached_tuning.FAST_DEBUG_CONFIGS[0].startswith("lv31_")
    assert run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS[0].startswith("lv31_")
    assert len(run_fv3_cached_tuning.FAST_DEBUG_CONFIGS) == 16
    assert len(run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS) == 34
