from __future__ import annotations

import json
from pathlib import Path

import app.experiments.feature_regime_experiment_reporter as feature_regime_experiment_reporter_module
from app.experiments.feature_regime_experiment_reporter import (
    FeatureRegimeExperimentReporter,
)
from app.validation.gate_selector import GateSelector
import run_fv3_cached_tuning


def _gate_probe(index: int) -> dict:
    return {
        "gate_type": "max_prob",
        "threshold": 0.5 + (index * 0.001),
        "signal_count": 10 + index,
        "resolved_signal_count": 10 + index,
        "long_count": 10 + index,
        "short_count": 0,
        "profit_factor": 0.9 + (index * 0.001),
        "total_r": -1.0 + (index * 0.01),
        "expectancy_r": -0.01 + (index * 0.001),
        "max_drawdown_r": 0.5,
        "passed": False,
        "fail_reasons": ["total_r_below_min"],
        "warnings": ["no_short_signals"],
        "primary_blocker": "total_r_below_min",
        "repair_hint": "total_r_relax_minus_1_25_probe_possible",
        "distance_to_pass_score": float(index),
        "threshold_deficits": {"total_r_deficit": 0.25},
        "effective_min_signal_count": 10,
        "effective_min_profit_factor": 0.95,
        "effective_min_total_r": -0.25,
        "effective_min_expectancy_r": -0.02,
        "directional_side_filter_profile": "long_only_research",
        "allowed_signal_directions": ["LONG"],
    }


def _candidate_board_row(index: int) -> dict:
    return {
        "fold_index": index + 1,
        "train_start": "2026-01-01",
        "train_end": "2026-02-01",
        "validation_start": "2026-02-02",
        "validation_end": "2026-02-10",
        "test_start": "2026-02-11",
        "test_end": "2026-02-20",
        "selected_gate_present": False,
        "gate_reject_reason": "no_validation_gate_passed",
        "selection_mode": "side_aware_research_relaxed",
        "directional_side_filter_profile": "long_only_research",
        "allowed_signal_directions": ["LONG"],
        "side_aware_validation_relaxation_enabled": True,
        "effective_min_signal_count": 10,
        "effective_min_profit_factor": 0.95,
        "effective_min_total_r": -0.25,
        "effective_min_expectancy_r": -0.02,
        "primary_failure_reason": "total_r_below_min",
        "has_total_r_below_min_blocker": True,
        "recommended_validation_repair_profile": "TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY",
        "total_r_repair_verdict": "TOTAL_R_REPAIR_PROBE_WORTH_TESTING",
        "total_r_repair_candidate_count": 5,
        "min_total_r_deficit": 0.1,
        "median_total_r_deficit": 0.2,
        "max_total_r_deficit": 0.3,
        "best_failed_gate_by_distance_to_pass": _gate_probe(index),
        "best_failed_gate_candidates": [_gate_probe(index + offset) for offset in range(5)],
    }


def _candidate_payload(index: int) -> dict:
    board_rows = [_candidate_board_row(row_index) for row_index in range(50)]
    return {
        "candidate_id": f"cand_{index}",
        "config_id": f"cfg_{index}",
        "symbol": "SOLUSDT",
        "interval": "15m",
        "status": "COMPLETED",
        "candidate_status": "REJECTED",
        "quality_status": "QUALITY_REJECTED",
        "score": float(100 - index),
        "label_config": {
            "directional_side_filter_profile": "long_only_research",
            "allowed_signal_directions": ["LONG"],
            "research_only_total_r_repair_enabled": True,
            "validation_total_r_repair_profile": "TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY",
        },
        "failed_gates": ["walk_forward_gate"],
        "passed_gates": [],
        "warnings": [],
        "recommendations": [],
        "profit_factor": 1.05,
        "profit_total_r": -0.25,
        "walk_forward_profit_factor": 0.95,
        "walk_forward_total_r": -0.5,
        "walk_forward_profit_diagnostics": {
            "diagnostic_name": "walk_forward_profit_diagnostics",
            "diagnostic_version": "ml38.10.26",
            "symbol": "SOLUSDT",
            "feature_version": "fv3_candle_ta_context",
            "model_version": "mv",
            "walk_forward_profit_factor": 0.95,
            "walk_forward_total_r": -0.5,
            "fold_count": 50,
            "profitable_fold_count": 10,
            "unprofitable_fold_count": 40,
            "worst_fold": {"fold_index": 1, "total_r": -1.0},
            "best_fold": {"fold_index": 2, "total_r": 0.5},
            "fold_snapshots": [
                {"fold_index": fold_index, "resolved_signal_count": 5, "profit_factor": 0.9, "total_r": -0.1}
                for fold_index in range(20)
            ],
            "low_signal_folds": [{"fold_index": fold_index} for fold_index in range(10)],
            "fold_signal_summary": {"total_resolved_signal_count": 100},
            "fold_profit_summary": {"profitable_fold_count": 10},
            "zero_signal_fold_count": 0,
            "low_signal_fold_count": 10,
            "min_resolved_signal_count": 1,
            "median_resolved_signal_count": 3,
            "max_resolved_signal_count": 5,
            "total_resolved_signal_count": 100,
            "walk_forward_stability_status": "LOW_SIGNAL_WALK_FORWARD",
            "walk_forward_stability_verdict": "REJECT_LOW_SIGNAL_WALK_FORWARD",
            "walk_forward_stability_warnings": ["walk_forward_has_low_signal_folds"],
            "validation_gate_failure_reason_counts": {"total_r_below_min": 50},
            "side_aware_relaxed_fold_count": 50,
            "walk_forward_validation_candidate_board_status": "NO_GATE_PASSED",
            "walk_forward_validation_candidate_board_verdict": "TOTAL_R_REPAIR_PROBE_WORTH_TESTING",
            "recommended_validation_repair_profile": "TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY",
            "total_r_below_min_fold_count": 50,
            "total_r_repair_candidate_fold_count": 50,
            "median_best_total_r_deficit": 0.2,
            "max_best_total_r_deficit": 0.4,
            "best_failed_total_r_by_fold": [{"fold_index": fold_index + 1} for fold_index in range(20)],
            "gate_probes": [_gate_probe(gate_index) for gate_index in range(30)],
            "passed_gates": [],
            "walk_forward_validation_candidate_board": {
                "diagnostic_name": "walk_forward_validation_candidate_board",
                "diagnostic_version": "ml38.10.26",
                "diagnostic_status": "NO_GATE_PASSED",
                "fold_count": 50,
                "folds_with_selected_gate": 0,
                "no_gate_fold_count": 50,
                "candidate_board_rows": board_rows,
                "fold_root_cause_count": 1,
                "worst_fold_root_cause": {
                    "diagnostic_status": "COMPLETED",
                    "fold_index": 1,
                    "validation_total_r": -5.9,
                    "primary_root_cause": "large_negative_validation_total_r",
                },
                "total_r_below_min_fold_count": 50,
                "total_r_repair_candidate_fold_count": 50,
                "best_failed_total_r_by_fold": [{"fold_index": fold_index + 1} for fold_index in range(20)],
                "median_best_total_r_deficit": 0.2,
                "max_best_total_r_deficit": 0.4,
                "recommended_validation_repair_profile": "TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY",
                "repair_profile_counts": {"TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY": 50},
                "verdict": "TOTAL_R_REPAIR_PROBE_WORTH_TESTING",
                "warnings": [],
                "recommendations": [],
            },
            "directional_side_signal_recovery_diagnostics": {
                "diagnostic_name": "directional_side_signal_recovery_diagnostics",
                "diagnostic_version": "ml38.10.26",
                "diagnostic_status": "COMPLETED",
                "verdict": "SIDE_FILTER_TOO_STRICT_RESEARCH_ONLY",
                "fold_count": 50,
                "side_profile": "long_only_research",
                "zero_signal_fold_count": 0,
                "low_signal_fold_count": 10,
                "side_filter_removed_all_fold_count": 5,
                "raw_signal_available_but_filtered_out_count": 6,
                "threshold_too_strict_fold_count": 7,
                "side_aware_relaxed_fold_count": 50,
                "total_original_signal_count": 150,
                "total_filtered_signal_count": 100,
                "total_removed_signal_count": 50,
                "primary_signal_loss_reason_counts": {"side_filter_removed_all": 5},
                "validation_gate_failure_reason_counts": {"total_r_below_min": 50},
                "fold_signal_recovery_rows": [{"fold_index": fold_index + 1} for fold_index in range(20)],
                "warnings": [],
                "recommendations": [],
            },
            "validation_fold_root_cause_summary": {
                "diagnostic_name": "validation_fold_root_cause_summary",
                "primary_root_cause_counts": {"large_negative_validation_total_r": 1},
            },
            "worst_fold_root_cause": {
                "diagnostic_name": "walk_forward_fold_root_cause_diagnostics",
                "diagnostic_version": "ml38.10.26",
                "diagnostic_status": "COMPLETED",
                "fold_index": 1,
                "validation_total_r": -5.9,
                "primary_root_cause": "large_negative_validation_total_r",
                "root_cause_flags": ["large_negative_validation_total_r"],
                "time_slice_summary": [{"time_slice": f"2026-05-{day:02d}"} for day in range(1, 20)],
                "outcome_summary": [{"result": "SL", "count": day} for day in range(1, 20)],
                "stop_pressure_summary": [{"bucket": day} for day in range(1, 10)],
                "mae_pressure_summary": [{"bucket": day} for day in range(1, 10)],
                "setup_quality_summary": [{"bucket": day} for day in range(1, 10)],
                "direction_summary": [{"direction": "LONG", "count": day} for day in range(1, 10)],
                "sample_losing_trades": [{"trade_id": day} for day in range(1, 10)],
            },
            "primary_validation_root_cause_counts": {"large_negative_validation_total_r": 1},
        },
        "research_only_total_r_repair_enabled": True,
        "validation_total_r_repair_profile": "TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY",
        "directional_side_filter_profile": "long_only_research",
        "allowed_signal_directions": ["LONG"],
    }


class _ExplodingFullResult:
    def __init__(self) -> None:
        self.experiment_id = "ml38_10_25_1_case"
        self.symbol = "SOLUSDT"
        self.interval = "15m"
        self.start_date = "2026-04-01"
        self.end_date = "2026-06-01"
        self.status = "COMPLETED"
        self.experiment_status = "COMPLETED_NO_ACCEPTED_CANDIDATE"
        self.config_count = 20
        self.candidate_count = 20
        self.evaluated_candidate_count = 20
        self.failed_candidate_count = 0
        self.accepted_candidate_count = 0
        self.rejected_candidate_count = 20
        self.best_candidate_id = "cand_0"
        self.best_candidate_config_id = "cfg_0"
        self.best_candidate_score = 100.0
        self.feature_quality_summary = {"weak_signal_detected": False}
        self.feature_group_quality_summary = {"groups": []}
        self.regime_feature_summary = {"regime_data_available": True}
        self.feature_leakage_summary = {"leakage_risk_detected": False}
        self.regime_experiment_plan_summary = {"ready_for_real_regime_training": False}
        self.candidate_results = tuple(_candidate_payload(index) for index in range(20))
        self.ranking = tuple(
            {
                "rank": index + 1,
                "candidate_id": f"cand_{index}",
                "config_id": f"cfg_{index}",
                "score": float(100 - index),
                "candidate_status": "REJECTED",
                "failed_gates": ["walk_forward_gate"],
            }
            for index in range(20)
        )
        self.failed_gates_summary = {"walk_forward_gate": 20}
        self.warnings = ()
        self.recommendations = ()
        self.regime_training_applied = False
        self.real_feature_diagnostics_used = False
        self.real_feature_diagnostics_row_count = 0
        self.feature_version_used = "fv3_candle_ta_context"
        self.regime_features_attached = False
        self.regime_feature_count = 0
        self.regime_feature_source = "none"
        self.regime_specific_labeling_available = False
        self.regime_specific_training_applied = False
        self.missing_requirements = ()
        self.effective_gap_count_for_training = 0
        self.gap_severity_for_training = "OK"
        self.gap_training_safe = True
        self.output_dir = "reports/feature_regime_experiments/ml38_10_25_1_case"
        self.log_path = "reports/feature_regime_experiments/ml38_10_25_1_case/run.log"
        self.events_path = "reports/feature_regime_experiments/ml38_10_25_1_case/events.jsonl"
        self.summary_json_path = "reports/feature_regime_experiments/ml38_10_25_1_case/feature_regime_experiment_summary.json"
        self.summary_markdown_path = "reports/feature_regime_experiments/ml38_10_25_1_case/feature_regime_experiment_summary.md"
        self.baseline_reference = {}
        self.probability_diagnostics = {}
        self.probability_diagnostics_missing_reason = None
        self.real_feature_diagnostics = {}
        self.real_feature_diagnostics_missing_reason = None
        self.collapse_diagnostics_v2 = {}
        self.collapse_diagnostics_v2_missing_reason = None
        self.regime_label_builder_status = {}
        self.regime_label_builder_status_missing_reason = None
        self.walk_forward_profit_diagnostics = {}
        self.walk_forward_profit_diagnostics_missing_reason = None
        self.profit_aware_diagnostics = {}
        self.profit_aware_diagnostics_missing_reason = None
        self.regime_label_builder_used_in_training_any = False
        self.regime_label_builder_used_in_training_all = False
        self.regime_specific_training_applied_any = False
        self.regime_specific_training_applied_all = False
        self.candle_ta_context_features_attached = False
        self.candle_ta_context_feature_count = 0
        self.candle_ta_context_missing_reason = None
        self.book_setup_context_features_attached = False
        self.book_setup_context_feature_count = 0
        self.book_setup_context_missing_reason = None
        self.fv4_feature_count = 0
        self.nison_feature_count = 0
        self.altunina_feature_count = 0
        self.path_context_feature_count = 0
        self.htf_context_feature_count = 0
        self.missing_context_feature_count = 0
        self.regime_features_missing_reason = None
        self.candidate_status = "REJECTED"
        self.model_quality_validation_status = None
        self.model_accepted = False
        self.reasons_why_best_still_rejected = ()
        self.configs_ranked = self.ranking
        self.flat_bias_summary = {}
        self.down_blindness_summary = {}
        self.baseline_edge_summary = {}
        self.label_mode_comparison_audit = {}
        self.flat_subtype_audit = {}
        self.setup_aware_label_diagnostics = {}
        self.schwager_slice_robustness = {}
        self.schwager_robustness_decision_board = {}
        self.class_margin_objective_decision = {}

    def to_dict(self) -> dict:
        raise AssertionError("summary writer must not call full result.to_dict()")


def test_ml38_10_25_1_summary_writer_uses_compact_payload_without_full_result_to_dict(
    tmp_path: Path,
) -> None:
    reporter = FeatureRegimeExperimentReporter()
    result = _ExplodingFullResult()
    output_path = tmp_path / "feature_regime_experiment_summary.json"

    reporter.write_summary_json(result, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary_payload_mode"] == "compact_capped_ml38_10_25_1"
    assert payload["summary_payload_compacted"] is True
    assert payload["candidate_results_total_count"] == 20
    assert payload["candidate_results_included_count"] == 20
    assert len(payload["candidate_results"]) == 20
    assert output_path.stat().st_size < 15 * 1024 * 1024
    board = payload["candidate_results"][0]["walk_forward_profit_diagnostics"][
        "walk_forward_validation_candidate_board"
    ]
    assert board["candidate_board_rows_total_count"] == 50
    assert board["candidate_board_rows_truncated"] is True
    assert (
        len(board["candidate_board_rows"])
        <= FeatureRegimeExperimentReporter.SUMMARY_VALIDATION_BOARD_ROW_LIMIT
    )
    candidate = payload["candidate_results"][0]
    assert candidate["walk_forward_validation_candidate_board_status"] == "NO_GATE_PASSED"
    assert candidate["walk_forward_validation_candidate_board_verdict"] == "TOTAL_R_REPAIR_PROBE_WORTH_TESTING"
    assert candidate["recommended_validation_repair_profile"] == "TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY"
    assert candidate["best_failed_total_r_by_fold_total_count"] == 20
    assert candidate["validation_candidate_board_rows_total_count"] == 50
    assert candidate["validation_candidate_board_rows_truncated"] is True
    assert candidate["fold_root_cause_count"] == 1
    assert candidate["worst_fold_root_cause"]["fold_index"] == 1
    assert (
        len(candidate["worst_fold_root_cause"].get("time_slice_summary", [])) <= 8
    )
    assert (
        candidate["worst_fold_root_cause"].get("time_slice_summary_total_count", 0)
        >= len(candidate["worst_fold_root_cause"].get("time_slice_summary", []))
    )


def test_ml38_10_25_1_summary_writer_does_not_require_json_dumps(
    monkeypatch,
    tmp_path: Path,
) -> None:
    reporter = FeatureRegimeExperimentReporter()
    result = _ExplodingFullResult()
    output_path = tmp_path / "feature_regime_experiment_summary.json"

    def _raise_memory_error(*args, **kwargs):
        raise MemoryError("simulated json.dumps failure")

    monkeypatch.setattr(
        feature_regime_experiment_reporter_module.json,
        "dumps",
        _raise_memory_error,
    )

    reporter.write_summary_json(result, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary_payload_compacted"] is True
    assert payload["summary_payload_mode"] == "compact_capped_ml38_10_25_1"


def test_ml38_10_25_1_summary_writer_caps_large_auxiliary_diagnostics(
    tmp_path: Path,
) -> None:
    reporter = FeatureRegimeExperimentReporter()
    result = _ExplodingFullResult()
    output_path = tmp_path / "feature_regime_experiment_summary.json"

    huge_rows = [
        {
            "fold_index": index + 1,
            "trade_ids": list(range(20)),
            "scores": [float(index)] * 10,
        }
        for index in range(400)
    ]
    first_candidate = result.candidate_results[0]
    first_candidate["prediction_root_cause_audit"] = {
        "diagnostic_status": "COMPLETED",
        "rows": huge_rows,
    }
    first_candidate["profit_aware_diagnostics"] = {
        "diagnostic_status": "COMPLETED",
        "fold_time_slice_blackout_summary": {
            "rows": huge_rows,
            "status": "RESEARCH_ONLY",
        },
    }
    result.profit_aware_diagnostics = {
        "diagnostic_status": "COMPLETED",
        "rows": huge_rows,
    }

    reporter.write_summary_json(result, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert output_path.stat().st_size < 15 * 1024 * 1024
    assert (
        payload["candidate_results"][0]["prediction_root_cause_audit"]["rows"]["_type"]
        == "list"
    )
    assert (
        payload["candidate_results"][0]["fold_time_slice_blackout_summary"]["rows"]["_type"]
        == "list"
    )
    assert payload["profit_aware_diagnostics"]["rows"]["_type"] == "list"


def test_ml38_10_25_1_gate_selector_caps_gate_probe_payload() -> None:
    rows = [
        {
            "gate_type": "max_prob",
            "threshold": 0.5 + (index * 0.001),
            "signal_count": 12,
            "profit_factor": 0.97,
            "total_r": -0.05,
            "expectancy_r": -0.005,
            "long_count": 12,
            "short_count": 0,
            "max_drawdown_r": 0.5,
        }
        for index in range(200)
    ]

    payload = GateSelector().select(
        rows,
        directional_side_filter_profile="long_only_research",
        allowed_signal_directions=("LONG",),
        side_aware_validation_relaxation_enabled=True,
        side_aware_min_validation_signal_count=10,
        side_aware_min_validation_profit_factor=0.95,
        side_aware_min_validation_total_r=-0.25,
        side_aware_min_validation_expectancy_r=-0.02,
        side_aware_allow_single_direction_validation=True,
    )

    diagnostics = payload["validation_gate_selection_diagnostics"]
    assert diagnostics["gate_probe_count"] == 200
    assert diagnostics["gate_probes_total_count"] == 200
    assert diagnostics["gate_probes_truncated"] is True
    assert len(diagnostics["gate_probes"]) <= GateSelector.MAX_DIAGNOSTIC_GATE_PROBES


def test_ml38_10_25_1_runtime_counts_unchanged() -> None:
    assert len(run_fv3_cached_tuning.FAST_DEBUG_CONFIGS) == 16
    assert len(run_fv3_cached_tuning.FAST_DEBUG_SYMBOLS) == 2
    assert len(run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS) == 34
    assert run_fv3_cached_tuning.FAST_DEBUG_START_DATE == "2026-04-01"
