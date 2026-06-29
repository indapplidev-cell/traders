from __future__ import annotations

import json
from pathlib import Path

from app.experiments.label_grid_experiment_reporter import LabelGridExperimentReporter


def _large_rows(count: int) -> list[dict[str, object]]:
    return [
        {
            "fold_index": index + 1,
            "trade_ids": list(range(20)),
            "scores": [float(index)] * 10,
        }
        for index in range(count)
    ]


class _ExplodingCandidate:
    def __init__(self, index: int) -> None:
        self.config_id = f"cfg_{index}"
        self.label_config = {
            "config_id": self.config_id,
            "fold_repair_feature_filter_rules": {"max_stop_pressure_risk_score": 0.42},
        }
        self.status = "COMPLETED"
        self.quality_status = "QUALITY_REJECTED"
        self.candidate_status = "REJECTED"
        self.raw_candidate_status = "REJECTED"
        self.model_version = "mv"
        self.training_run_id = f"train_{index}"
        self.dataset_rows = 1000
        self.train_rows = 700
        self.val_rows = 150
        self.test_rows = 150
        self.model_accuracy = 0.51
        self.baseline_accuracy = 0.50
        self.accuracy_edge = 0.01
        self.collapse_detected = False
        self.collapse_type = None
        self.feature_version_used = "fv3_candle_ta_context"
        self.gap_severity = "OK"
        self.gap_count = 0
        self.gap_severity_for_training = "OK"
        self.effective_gap_count_for_training = 0
        self.gap_training_safe = True
        self.profit_total_r = -0.25
        self.profit_factor = 1.01
        self.walk_forward_fold_count = 24
        self.walk_forward_global_total_r = -0.4
        self.walk_forward_profit_factor = 0.97
        self.gate_policy_allowed_count = 10
        self.gate_policy_blocked_count = 2
        self.failed_gates = ("walk_forward_gate",)
        self.passed_gates = ()
        self.warnings = ()
        self.recommendations = ()
        self.directional_side_filter_profile = "long_only_research"
        self.allowed_signal_directions = ("LONG",)
        self.research_only_total_r_repair_enabled = True
        self.validation_total_r_repair_profile = "TOTAL_R_RELAX_MINUS_1_25_RESEARCH_ONLY"
        self.research_only_acceptance_block_reason = "research_only_feature_regime_fold_repair_probe"
        self.research_only_fold_repair_probe_enabled = True
        self.fold_repair_probe_profile = "LONG_ONLY_FEATURE_GUARD_EXIT45"
        self.fold_repair_target_dates = ("2026-05-25", "2026-05-26", "2026-05-28")
        self.fold_repair_time_slice_blackout_enabled = False
        self.fold_repair_blackout_dates = ()
        self.fold_repair_feature_filter_enabled = True
        self.fold_repair_feature_filter_profile = "FEATURE_GUARD_V1_EXIT45"
        self.fold_repair_feature_filter_rules = {"max_stop_pressure_risk_score": 0.42}
        self.fold_repair_probe_diagnostics = {"rows": _large_rows(400)}
        self.fold_feature_regime_filter_summary = {
            "removed_signal_count": 3,
            "rows": _large_rows(400),
        }
        self.opportunity_probability_threshold = 0.70
        self.setup_quality_min_threshold = 0.60
        self.setup_quality_decision_mask_enabled = True
        self.setup_quality_decision_mask_min_threshold = 0.60
        self.selected_opportunity_threshold = 0.70
        self.entry_path_quality_filter_enabled = True
        self.entry_path_quality_min_threshold = 0.71
        self.stop_pressure_max_risk_score = 0.45
        self.mae_pressure_max_risk_score = 0.51
        self.probability_diagnostics = {"rows": _large_rows(400)}
        self.collapse_diagnostics_v2 = {"rows": _large_rows(400)}
        self.walk_forward_profit_diagnostics = {
            "walk_forward_validation_candidate_board_status": "NO_GATE_PASSED",
            "walk_forward_validation_candidate_board_verdict": "TOTAL_R_REPAIR_PROBE_WORTH_TESTING",
            "rows": _large_rows(400),
        }
        self.profit_aware_diagnostics = {
            "fold_feature_regime_filter_summary": {"rows": _large_rows(400)},
            "rows": _large_rows(400),
        }
        self.prediction_root_cause_audit = {"rows": _large_rows(400)}
        self.book_driven_forensic_audit = {"rows": _large_rows(400)}
        self.decision_policy_grid_diagnostics = {"rows": _large_rows(400)}
        self.directional_side_filter_summary = {"rows": _large_rows(400)}
        self.entry_path_prediction_filter_summary = {"rows": _large_rows(400)}
        self.stop_pressure_effectiveness_audit = {"rows": _large_rows(400)}
        self.setup_quality_decision_mask_summary = {"rows": _large_rows(400)}
        self.two_stage_trade_diagnostics = {"rows": _large_rows(400)}

    def to_dict(self) -> dict[str, object]:
        raise AssertionError("summary writer must not call full candidate.to_dict()")


class _ExplodingLabelGridResult:
    def __init__(self) -> None:
        self.status = "COMPLETED"
        self.experiment_status = "COMPLETED_NO_ACCEPTED_CANDIDATE"
        self.experiment_id = "ml38_10_28_label_grid_case"
        self.symbol = "SOLUSDT"
        self.interval = "15m"
        self.start_date = "2026-04-01"
        self.end_date = "2026-06-15"
        self.dry_run = False
        self.sample_mode = False
        self.config_count = 30
        self.completed_candidate_count = 30
        self.evaluated_candidate_count = 30
        self.failed_candidate_count = 0
        self.accepted_candidate_count = 0
        self.rejected_candidate_count = 30
        self.best_candidate_config_id = "cfg_0"
        self.best_candidate_status = "REJECTED"
        self.best_candidate_score = 1.0
        self.feature_version_used = "fv3_candle_ta_context"
        self.output_dir = "reports/label_grid_experiments/ml38_10_28_label_grid_case"
        self.log_path = "reports/label_grid_experiments/ml38_10_28_label_grid_case/label_grid_experiment.log"
        self.events_path = "reports/label_grid_experiments/ml38_10_28_label_grid_case/label_grid_experiment_events.jsonl"
        self.summary_json_path = "reports/label_grid_experiments/ml38_10_28_label_grid_case/label_grid_experiment_summary.json"
        self.summary_markdown_path = "reports/label_grid_experiments/ml38_10_28_label_grid_case/label_grid_experiment_summary.md"
        self.candidate_results_dir = "reports/label_grid_experiments/ml38_10_28_label_grid_case/candidate_results"
        self.candidate_results = tuple(_ExplodingCandidate(index) for index in range(30))
        self.candidate_ranking = tuple(
            {
                "rank": index + 1,
                "config_id": f"cfg_{index}",
                "candidate_status": "REJECTED",
                "quality_status": "QUALITY_REJECTED",
                "score": float(100 - index),
                "failed_gates": ["walk_forward_gate"],
            }
            for index in range(30)
        )
        self.failed_gates_summary = {"walk_forward_gate": 30}
        self.collapse_summary = {"no_collapse": 30}
        self.profit_summary = {"rows": _large_rows(400)}
        self.walk_forward_summary = {"rows": _large_rows(400)}
        self.gap_quality_summary = {"rows": _large_rows(400)}
        self.recommendations = ("keep_research_only",)
        self.approved_for_live_trading = False
        self.approved_for_auto_activation = False
        self.orders_enabled = False
        self.traders_core_connected = False

    def to_dict(self) -> dict[str, object]:
        raise AssertionError("summary writer must not call full result.to_dict()")


def test_ml38_10_28_label_grid_summary_writer_uses_compact_payload(
    tmp_path: Path,
) -> None:
    reporter = LabelGridExperimentReporter()
    result = _ExplodingLabelGridResult()
    result.summary_json_path = str(tmp_path / "label_grid_experiment_summary.json")

    output_path = reporter.write_json_summary(result)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary_payload_mode"] == "compact_capped_ml38_10_28_label_grid"
    assert payload["summary_payload_compacted"] is True
    assert payload["candidate_results_total_count"] == 30
    assert payload["candidate_results_included_count"] == 30
    assert len(payload["candidate_results"]) == 30
    assert payload["candidate_results"][0]["fold_repair_feature_filter_enabled"] is True
    assert payload["candidate_results"][0]["fold_feature_regime_filter_summary"]["rows"]["_type"] == "list"
    assert payload["candidate_results"][0]["walk_forward_profit_diagnostics"]["rows"]["_type"] == "list"
    assert payload["profit_summary"]["rows"]["_type"] == "list"
    assert output_path.stat().st_size < 15 * 1024 * 1024
