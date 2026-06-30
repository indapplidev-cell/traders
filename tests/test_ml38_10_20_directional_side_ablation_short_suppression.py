from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
from app.labels.label_quality_grid import LabelQualityGridPlanner
import run_fv3_cached_tuning


def _row(direction: str, future_candles: list[dict]) -> dict:
    label = "UP" if direction == "LONG" else "DOWN"
    return {
        "predicted_label": label,
        "entry_path_original_predicted_label": label,
        "entry_path_filtered_predicted_label": label,
        "actual_label": label,
        "prob_up": 0.85 if direction == "LONG" else 0.05,
        "prob_down": 0.85 if direction == "SHORT" else 0.05,
        "prob_flat": 0.10,
        "confidence": 0.85,
        "margin": 0.80,
        "directional_edge": 0.80,
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": future_candles,
        "future_move_atr": 1.0 if direction == "LONG" else -1.0,
        "entry_path_filter_enabled": True,
        "entry_path_filter_blocked": False,
        "entry_path_filter_block_reason": None,
        "entry_path_filter_threshold": 0.70,
        "entry_path_filter_stop_threshold": 0.45,
        "entry_path_filter_mae_threshold": 0.52,
        "entry_path_quality_score": 0.80,
        "stop_pressure_risk_score": 0.20,
        "mae_pressure_risk_score": 0.20,
    }


def test_ml38_10_20_long_only_filter_removes_short_side() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    payload = evaluator.evaluate_single_gate(
        predictions=[
            _row("LONG", [{"high": 101.4, "low": 99.9, "close": 101.0}]),
            _row("SHORT", [{"high": 101.6, "low": 99.8, "close": 101.2}]),
        ],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.4,
        exit_policy_profile="stop_loss_mitigation_recovery_guard_v1",
        exit_timeout_bars=9,
        exit_mitigation_loss_r=0.62,
        exit_neutral_abs_r=0.15,
        directional_side_filter_profile="long_only_research",
        allowed_signal_directions=("LONG",),
    )

    summary = payload["summary"]
    side = summary["directional_side_filter_summary"]

    assert summary["resolved_signal_count"] == 1
    assert summary["long_count"] == 1
    assert summary["short_count"] == 0
    assert side["active"] is True
    assert side["original_signal_count"] == 2
    assert side["filtered_signal_count"] == 1
    assert side["removed_short_count"] == 1
    assert side["allowed_signal_directions"] == ["LONG"]


def test_ml38_10_20_short_only_filter_keeps_only_short_side() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    payload = evaluator.evaluate_single_gate(
        predictions=[
            _row("LONG", [{"high": 101.4, "low": 99.9, "close": 101.0}]),
            _row("SHORT", [{"high": 100.1, "low": 98.6, "close": 99.0}]),
        ],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.4,
        directional_side_filter_profile="short_only_research",
        allowed_signal_directions=("SHORT",),
    )

    summary = payload["summary"]
    side = summary["directional_side_filter_summary"]

    assert summary["resolved_signal_count"] == 1
    assert summary["long_count"] == 0
    assert summary["short_count"] == 1
    assert side["removed_long_count"] == 1
    assert side["filtered_short_count"] == 1
    assert side["allowed_signal_directions"] == ["SHORT"]


def test_ml38_10_20_grid_matrix_and_runtime_include_lv28_side_ablation() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}

    assert grid["directional_side_ablation_stage"] == "ML38.10.20"
    assert "lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_only" in configs_by_id
    assert "lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_short_only" in configs_by_id
    assert "lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short" in configs_by_id

    long_only = configs_by_id["lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_only"]
    short_only = configs_by_id["lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_short_only"]
    suppress_short = configs_by_id["lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short"]

    assert long_only["directional_side_filter_profile"] == "long_only_research"
    assert long_only["allowed_signal_directions"] == ["LONG"]
    assert short_only["directional_side_filter_profile"] == "short_only_research"
    assert short_only["allowed_signal_directions"] == ["SHORT"]
    assert suppress_short["directional_side_filter_profile"] == "suppress_short_research"
    assert suppress_short["allowed_signal_directions"] == ["LONG"]
    assert len(long_only["label_version"]) <= 50
    assert len(short_only["label_version"]) <= 50
    assert len(suppress_short["label_version"]) <= 50

    matrix = ML382FV3TuningMatrix().build()
    assert matrix["directional_side_ablation_stage"] == "ML38.10.20"
    assert "lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_only" in matrix["config_ids"]

    assert run_fv3_cached_tuning.FAST_DEBUG_CONFIGS[0].startswith("lv31_")
    assert len(run_fv3_cached_tuning.FAST_DEBUG_CONFIGS) == 16
    assert run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS[0].startswith("lv31_")
    assert len(run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS) == 34
