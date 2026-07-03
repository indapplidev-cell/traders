from __future__ import annotations

from app.diagnostics.fold_time_slice_exit_repair_probe import (
    FoldTimeSliceExitRepairProbe,
)
from app.evaluation.profit_aware_evaluator_v2 import ProfitAwareEvaluatorV2
from app.experiments.label_grid_experiment_runner import LabelGridExperimentRunner
from app.labels.label_quality_grid import LabelQualityGridPlanner
import run_fv3_cached_tuning


def _prediction_row(*, date_text: str) -> dict:
    return {
        "predicted_label": "UP",
        "entry_path_original_predicted_label": "UP",
        "entry_path_filtered_predicted_label": "UP",
        "actual_label": "UP",
        "prob_up": 0.85,
        "prob_down": 0.05,
        "prob_flat": 0.10,
        "confidence": 0.85,
        "margin": 0.75,
        "directional_edge": 0.70,
        "current_close": 100.0,
        "atr_14": 1.0,
        "future_candles": [{"high": 101.4, "low": 99.9, "close": 101.0}],
        "future_move_atr": 1.0,
        "entry_path_filter_enabled": True,
        "entry_path_filter_blocked": False,
        "entry_path_filter_block_reason": None,
        "entry_path_filter_threshold": 0.70,
        "entry_path_filter_stop_threshold": 0.45,
        "entry_path_filter_mae_threshold": 0.52,
        "entry_path_quality_score": 0.80,
        "stop_pressure_risk_score": 0.20,
        "mae_pressure_risk_score": 0.20,
        "timestamp": f"{date_text}T00:00:00Z",
    }


def test_ml38_10_27_lv31_configs_exist_and_are_research_only() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}

    for config_id in (
        "lv31_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit45_probe",
        "lv31_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_probe",
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit45_probe",
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit75_probe",
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_probe",
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_bad_dates_probe",
        "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe",
    ):
        payload = configs_by_id[config_id]
        assert payload["research_only_fold_repair_probe_enabled"] is True
        assert payload["research_only_acceptance_block_reason"] == (
            "research_only_fold_1_exit_time_slice_repair_probe"
        )
        assert payload["fold_repair_target_dates"] == [
            "2026-05-25",
            "2026-05-26",
            "2026-05-28",
        ]


def test_ml38_10_27_blackout_filter_removes_only_target_date_rows() -> None:
    evaluator = ProfitAwareEvaluatorV2()
    payload = evaluator.evaluate_single_gate(
        predictions=[
            _prediction_row(date_text="2026-05-25"),
            _prediction_row(date_text="2026-05-26"),
            _prediction_row(date_text="2026-05-28"),
            _prediction_row(date_text="2026-05-29"),
        ],
        gate_type="max_prob",
        threshold=0.50,
        take_profit_atr=1.2,
        stop_loss_atr=1.5,
        directional_side_filter_profile="long_only_research",
        allowed_signal_directions=("LONG",),
        research_only_fold_repair_probe_enabled=True,
        fold_repair_probe_profile="LONG_ONLY_BAD_DATES",
        fold_repair_target_dates=("2026-05-25", "2026-05-26", "2026-05-28"),
        fold_repair_time_slice_blackout_enabled=True,
        fold_repair_blackout_dates=("2026-05-25", "2026-05-26", "2026-05-28"),
    )

    summary = payload["summary"]["fold_time_slice_blackout_summary"]
    assert summary["enabled"] is True
    assert summary["removed_signal_count"] == 3
    assert summary["output_signal_count"] == 1
    assert summary["removed_counts_by_date"] == {
        "2026-05-25": 1,
        "2026-05-26": 1,
        "2026-05-28": 1,
    }


def test_ml38_10_27_probe_board_summarizes_synthetic_candidates() -> None:
    result = FoldTimeSliceExitRepairProbe().analyze(
        [
            {
                "symbol": "SOLUSDT",
                "config_id": "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_probe",
                "candidate_id": "cand_1",
                "candidate_status": "REJECTED",
                "research_only_fold_repair_probe_enabled": True,
                "fold_repair_probe_profile": "LONG_ONLY_BAD_DATES",
                "fold_repair_target_dates": ["2026-05-25", "2026-05-26", "2026-05-28"],
                "fold_repair_time_slice_blackout_enabled": True,
                "fold_repair_blackout_dates": ["2026-05-25", "2026-05-26", "2026-05-28"],
                "directional_side_filter_profile": "long_only_research",
                "allowed_signal_directions": ["LONG"],
                "profit_factor": 1.1,
                "profit_total_r": 1.4,
                "walk_forward_profit_factor": 0.95,
                "walk_forward_total_r": 0.2,
                "failed_gates": ["research_only_fold_1_exit_time_slice_repair_probe_gate"],
                "profit_aware_diagnostics": {
                    "fold_time_slice_blackout_summary": {
                        "removed_signal_count": 3,
                        "removed_ratio": 0.75,
                    }
                },
                "worst_fold_root_cause": {
                    "validation_total_r": -1.0,
                    "primary_root_cause": "large_negative_validation_total_r",
                    "outcome_counts": {"SL": 3},
                    "top_bad_time_slices": ["2026-05-25", "2026-05-26"],
                },
            },
            {
                "symbol": "SOLUSDT",
                "config_id": "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit45_probe",
                "candidate_id": "cand_2",
                "candidate_status": "REJECTED",
                "research_only_fold_repair_probe_enabled": True,
                "fold_repair_probe_profile": "LONG_ONLY_EXIT45",
                "fold_repair_target_dates": ["2026-05-25", "2026-05-26", "2026-05-28"],
                "fold_repair_time_slice_blackout_enabled": False,
                "fold_repair_blackout_dates": [],
                "directional_side_filter_profile": "long_only_research",
                "allowed_signal_directions": ["LONG"],
                "profit_factor": 1.2,
                "profit_total_r": 1.9,
                "walk_forward_profit_factor": 1.05,
                "walk_forward_total_r": 0.6,
                "failed_gates": ["research_only_fold_1_exit_time_slice_repair_probe_gate"],
                "profit_aware_diagnostics": {
                    "fold_time_slice_blackout_summary": {
                        "removed_signal_count": 0,
                        "removed_ratio": 0.0,
                    }
                },
                "worst_fold_root_cause": {
                    "validation_total_r": -0.4,
                    "primary_root_cause": "time_slice_loss_cluster",
                    "outcome_counts": {"SL": 1},
                    "top_bad_time_slices": ["2026-05-28"],
                },
            },
        ]
    )

    assert result["diagnostic_name"] == "fold_time_slice_exit_repair_probe"
    assert result["probe_candidate_count"] == 2
    assert result["profile_counts"]["LONG_ONLY_BAD_DATES"] == 1
    assert result["profile_counts"]["LONG_ONLY_EXIT45"] == 1
    assert result["best_by_walk_forward_total_r"][0]["config_id"].startswith("lv31_")
    assert result["verdict"] in {
        "TIME_SLICE_BLACKOUT_IMPROVES_FINAL_ONLY_RESEARCH_OVERFIT_RISK",
        "EXIT_MITIGATION_VARIANT_IMPROVES_WF_RESEARCH_ONLY",
    }
    assert "do_not_accept_lv31" in result["warnings"]


def test_ml38_10_27_runtime_counts_and_expected_candidates() -> None:
    fast_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(["--fast-debug"])
    )
    quick_wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(
        run_fv3_cached_tuning.parse_args(
            ["--quick-quality", "--quick-quality-symbol", "SOLUSDT"]
        )
    )

    assert len(run_fv3_cached_tuning.FAST_DEBUG_CONFIGS) == 20
    assert len(run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS) == 42
    assert fast_wrapper._expected_candidate_count() == 40
    assert quick_wrapper._expected_candidate_count() == 42


def test_ml38_10_27_research_only_fold_probe_forces_rejection_gate() -> None:
    failed_gates, passed_gates = (
        LabelGridExperimentRunner._apply_research_only_fold_repair_probe_block(
            failed_gates=(),
            passed_gates=("walk_forward_gate",),
            research_only_fold_repair_probe_enabled=True,
        )
    )

    assert "research_only_fold_1_exit_time_slice_repair_probe_gate" in failed_gates
    assert "research_only_fold_1_exit_time_slice_repair_probe_gate" not in passed_gates
