import json
from pathlib import Path

from app.experiments.feature_regime_experiment_reporter import FeatureRegimeExperimentReporter
from app.experiments.ml38_2_1_wrapper_manifest import build_ml38_2_1_wrapper_manifest
from app.experiments.multi_symbol_feature_regime_analyzer import MultiSymbolFeatureRegimeAnalyzer
from app.training.training_pipeline_reporter import TrainingPipelineReporter
from app.training.training_pipeline_runner import TrainingPipelineResult


def test_training_pipeline_report_json_contains_schwager_board(tmp_path: Path) -> None:
    result = TrainingPipelineResult(
        run_id="ml38_10_2_report_case",
        status="COMPLETED",
        symbol="SOLUSDT",
        interval="15m",
        start_date="2025-01-01",
        end_date="2025-01-10",
        dry_run=False,
        sample_mode=False,
        run_gate_policy_replay=True,
        export_report=True,
        started_at="2026-06-19T10:00:00+00:00",
        ended_at="2026-06-19T10:01:00+00:00",
        duration_seconds=60.0,
        stage_results=(),
        quality_summary={"quality_status": "QUALITY_REJECTED"},
        model_summary={},
        baseline_summary={},
        gate_policy_replay_summary={},
        gap_quality_summary={},
        anti_collapse_summary={},
        candidate_selection_summary={},
        label_config_summary={},
        quality_gates_summary={},
        output_dir=str(tmp_path),
        log_path=str(tmp_path / "training_pipeline.log"),
        events_path=str(tmp_path / "training_pipeline_events.jsonl"),
        json_report_path=str(tmp_path / "training_pipeline_report.json"),
        markdown_report_path=str(tmp_path / "training_pipeline_report.md"),
        safety={},
        command_snapshot={},
        next_recommendations=(),
        schwager_slice_robustness={
            "edge_by_regime": {"trend_up": {"baseline_edge": 0.03}},
            "robustness_flags": ["negative_edge_slice_detected"],
        },
        schwager_robustness_decision_board={
            "diagnostic_name": "schwager_robustness_decision_board",
            "final_research_decision": "DO_NOT_SCALE_RUNTIME",
            "primary_failure": "walk_forward_unstable",
        },
    )

    path = TrainingPipelineReporter().write_json_report(result)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schwager_robustness_decision_board"]["final_research_decision"] == "DO_NOT_SCALE_RUNTIME"
    assert payload["schwager_slice_robustness"]["edge_by_regime"]["trend_up"]["baseline_edge"] == 0.03


def test_candidate_json_and_multi_symbol_analysis_include_schwager_board(tmp_path: Path) -> None:
    candidate_payload = {
        "candidate_id": "cand_1",
        "config_id": "cfg_1",
        "status": "COMPLETED",
        "candidate_status": "REJECTED",
        "raw_candidate_status": "REJECTED",
        "quality_status": "QUALITY_REJECTED",
        "score": -2.0,
        "approved_for_live_trading": False,
        "approved_for_auto_activation": False,
        "orders_enabled": False,
        "traders_core_connected": False,
        "schwager_slice_robustness": {
            "edge_by_time_slice": {"early_window": {"baseline_edge": 0.02}},
            "robustness_flags": ["single_positive_time_slice"],
        },
        "schwager_robustness_decision_board": {
            "diagnostic_name": "schwager_robustness_decision_board",
            "final_research_decision": "NEEDS_MODEL_OBJECTIVE_REWORK",
            "primary_failure": "collapse_not_fixed",
        },
        "prediction_root_cause_audit": {"diagnostic_name": "prediction_root_cause_audit", "warnings": []},
        "book_driven_forensic_audit": {"diagnostic_name": "book_driven_forensic_audit", "final_diagnosis": "GLOBAL_DIRECTION_TASK_TOO_NOISY"},
    }

    candidate_json = FeatureRegimeExperimentReporter().write_candidate_json(
        candidate_payload,
        tmp_path / "candidate.json",
    )
    saved_candidate = json.loads(candidate_json.read_text(encoding="utf-8"))
    assert saved_candidate["schwager_robustness_decision_board"]["primary_failure"] == "collapse_not_fixed"

    summary = {
        "experiment_id": "exp_1",
        "symbol": "SOLUSDT",
        "interval": "15m",
        "start_date": "2025-01-01",
        "status": "COMPLETED",
        "experiment_status": "COMPLETED_NO_ACCEPTED_CANDIDATE",
        "candidate_count": 1,
        "evaluated_candidate_count": 1,
        "failed_candidate_count": 0,
        "accepted_candidate_count": 0,
        "rejected_candidate_count": 1,
        "best_candidate_config_id": "cfg_1",
        "feature_version_used": "fv2",
        "candle_ta_context_features_attached": True,
        "candle_ta_context_feature_count": 5,
        "real_feature_diagnostics_used": True,
        "real_feature_diagnostics_row_count": 10,
        "effective_gap_count_for_training": 0,
        "gap_severity_for_training": "OK",
        "gap_training_safe": True,
        "regime_features_attached": True,
        "regime_feature_count": 8,
        "regime_label_builder_used_in_training_any": True,
        "regime_specific_training_applied_any": True,
        "candidate_results": [candidate_payload],
        "configs_ranked": [candidate_payload],
        "schwager_robustness_decision_board": candidate_payload["schwager_robustness_decision_board"],
        "schwager_slice_robustness": candidate_payload["schwager_slice_robustness"],
    }
    summary_path = tmp_path / "feature_regime_experiment_summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")

    analysis = MultiSymbolFeatureRegimeAnalyzer().analyze([summary_path])

    assert analysis["symbol_results"][0]["schwager_robustness_decision_board"]["final_research_decision"] == "NEEDS_MODEL_OBJECTIVE_REWORK"
    assert analysis["schwager_robustness_summary"]["final_research_decision_counts"]["NEEDS_MODEL_OBJECTIVE_REWORK"] == 1


def test_wrapper_manifest_contains_schwager_summary() -> None:
    payload = build_ml38_2_1_wrapper_manifest(
        branch="ml38_10_2",
        archive_path="reports/feature_regime_experiments/ml38_10_2.zip",
        archive_stage_dir="reports/feature_regime_experiments/ml38_10_2",
        manifest_path="reports/feature_regime_experiments/ml38_10_2/archive_manifest.json",
        script_path="run_wrapper.py",
        source_mode="wrapper",
        wrapper_completed_end_to_end=True,
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        symbols_completed=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        failed_symbols=[],
        run_results=[],
        multi_symbol_result={
            "candidate_count": 3,
            "accepted_candidate_count": 0,
            "rejected_candidate_count": 3,
            "schwager_robustness_summary": {
                "final_research_decision_counts": {"DO_NOT_SCALE_RUNTIME": 3},
            },
        },
        included_files=["archive_manifest.json", "multi_symbol_feature_regime_analysis.json"],
    )

    assert payload["schwager_robustness_summary"]["final_research_decision_counts"]["DO_NOT_SCALE_RUNTIME"] == 3
