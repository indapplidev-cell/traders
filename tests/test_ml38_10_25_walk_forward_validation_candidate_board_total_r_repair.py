from __future__ import annotations

from app.diagnostics.walk_forward_profit_diagnostics import WalkForwardProfitDiagnostics
from app.diagnostics.walk_forward_validation_candidate_board import (
    WalkForwardValidationCandidateBoard,
)
from app.experiments.label_grid_experiment_runner import LabelGridExperimentRunner
from app.labels.label_quality_grid import LabelQualityGridPlanner
from app.validation.gate_selector import GateSelector
import run_fv3_cached_tuning


def _gate(**overrides):
    payload = {
        "gate_type": "max_prob",
        "threshold": 0.5,
        "signal_count": 15,
        "resolved_signal_count": 15,
        "profit_factor": 1.05,
        "total_r": -1.0,
        "expectancy_r": 0.01,
        "long_count": 15,
        "short_count": 0,
        "max_drawdown_r": 0.5,
    }
    payload.update(overrides)
    return payload


def _no_gate_fold(fold_index: int) -> dict:
    selector_payload = GateSelector().select(
        [
            _gate(total_r=-1.0, profit_factor=1.05, expectancy_r=0.01, signal_count=15),
            _gate(total_r=-3.0, profit_factor=1.20, expectancy_r=0.02, signal_count=30),
        ],
        directional_side_filter_profile="long_only_research",
        allowed_signal_directions=("LONG",),
        side_aware_validation_relaxation_enabled=True,
        side_aware_min_validation_signal_count=10,
        side_aware_min_validation_profit_factor=0.95,
        side_aware_min_validation_total_r=-0.25,
        side_aware_min_validation_expectancy_r=-0.02,
        side_aware_allow_single_direction_validation=True,
    )
    return {
        "fold_index": fold_index,
        "train_start": "2026-01-01",
        "train_end": "2026-02-01",
        "validation_start": "2026-02-02",
        "validation_end": "2026-02-10",
        "test_start": "2026-02-11",
        "test_end": "2026-02-20",
        "selected_gate": selector_payload.get("selected_gate"),
        "gate_reject_reason": selector_payload.get("reject_reason"),
        "validation_gate_selection_diagnostics": selector_payload.get("diagnostics"),
        "test_result": {
            "resolved_signal_count": 0,
            "signal_count": 0,
            "profit_factor": None,
            "total_r": 0.0,
        },
    }


def test_ml38_10_25_gate_selector_ranks_failed_gates_and_reports_deficits() -> None:
    payload = GateSelector().select(
        [
            _gate(total_r=-1.0, profit_factor=1.05, expectancy_r=0.01, signal_count=15),
            _gate(total_r=-3.0, profit_factor=1.20, expectancy_r=0.02, signal_count=30),
        ],
        directional_side_filter_profile="long_only_research",
        allowed_signal_directions=("LONG",),
        side_aware_validation_relaxation_enabled=True,
        side_aware_min_validation_signal_count=10,
        side_aware_min_validation_profit_factor=0.95,
        side_aware_min_validation_total_r=-0.25,
        side_aware_min_validation_expectancy_r=-0.02,
        side_aware_allow_single_direction_validation=True,
    )

    diagnostics = payload["diagnostics"]
    assert payload["selected_gate"] is None
    assert diagnostics["diagnostic_version"] == "ml38.10.25"
    assert diagnostics["best_failed_gate_candidates"]
    assert (
        diagnostics["best_failed_gate_by_distance_to_pass"]["threshold_deficits"]["total_r_deficit"]
        > 0
    )
    assert diagnostics["recommended_validation_repair_profile"] in {
        "TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY",
        "TOTAL_R_RELAX_MINUS_2_50_RESEARCH_ONLY",
    }


def test_ml38_10_25_validation_candidate_board_summarizes_two_no_gate_folds() -> None:
    board = WalkForwardValidationCandidateBoard().analyze(
        walk_forward_summary={
            "summary": {"fold_count": 2, "folds_with_selected_gate": 0},
            "folds": [_no_gate_fold(1), _no_gate_fold(2)],
        }
    )

    assert board["diagnostic_version"] == "ml38.10.26"
    assert board["no_gate_fold_count"] == 2
    assert board["total_r_below_min_fold_count"] == 2
    assert board["candidate_board_rows"]
    assert board["recommended_validation_repair_profile"].startswith("TOTAL_R_RELAX")


def test_ml38_10_25_walk_forward_profit_diagnostics_carries_candidate_board() -> None:
    diagnostics = WalkForwardProfitDiagnostics().analyze(
        symbol="SOLUSDT",
        feature_version="fv3_candle_ta_context",
        model_version="mv",
        profit_aware_summary={"summary": {"profit_factor": 1.1, "total_r": 1.0}},
        walk_forward_summary={
            "summary": {
                "fold_count": 2,
                "folds_with_selected_gate": 0,
                "folds_profitable_on_test": 0,
                "global_profit_factor": None,
                "global_total_r": 0.0,
            },
            "folds": [_no_gate_fold(1), _no_gate_fold(2)],
        },
    )

    board = diagnostics["walk_forward_validation_candidate_board"]
    assert board["diagnostic_name"] == "walk_forward_validation_candidate_board"
    assert board["diagnostic_version"] == "ml38.10.26"
    assert diagnostics["walk_forward_validation_candidate_board_status"] is not None
    assert diagnostics["recommended_validation_repair_profile"] is not None


def test_ml38_10_25_lv30_configs_exist_and_are_research_only_blocked() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}
    long_h12 = configs_by_id[
        "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe"
    ]

    assert long_h12["research_only_total_r_repair_enabled"] is True
    assert long_h12["side_aware_min_validation_total_r"] == -1.25
    assert len(long_h12["label_version"]) <= 50
    assert grid["walk_forward_total_r_failure_repair_stage"] == "ML38.10.25"


def test_ml38_10_25_runtime_shortlists_include_lv30_and_new_counts() -> None:
    assert len(run_fv3_cached_tuning.FAST_DEBUG_CONFIGS) == 12
    assert len(run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS) == 26
    assert run_fv3_cached_tuning.FAST_DEBUG_CONFIGS[0].startswith("lv31_")
    assert run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS[0].startswith("lv31_")


def test_ml38_10_25_research_only_total_r_repair_forces_rejection_gate() -> None:
    failed_gates, passed_gates = LabelGridExperimentRunner._apply_research_only_total_r_repair_block(
        failed_gates=(),
        passed_gates=("walk_forward_gate",),
        research_only_total_r_repair_enabled=True,
    )

    assert "research_only_validation_total_r_repair_gate" in failed_gates
    assert "research_only_validation_total_r_repair_gate" not in passed_gates
