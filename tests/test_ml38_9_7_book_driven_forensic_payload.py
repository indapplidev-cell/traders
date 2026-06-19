import json
from pathlib import Path
from types import SimpleNamespace

from app.diagnostics.book_driven_forensic_audit import BookDrivenForensicAudit
from app.experiments.feature_regime_experiment_reporter import FeatureRegimeExperimentReporter
from app.experiments.multi_symbol_feature_regime_analyzer import MultiSymbolFeatureRegimeAnalyzer
from app.training.training_pipeline_reporter import TrainingPipelineReporter
from app.training.training_pipeline_runner import TrainingPipelineResult


def _book_audit() -> dict[str, object]:
    rows = [
        SimpleNamespace(
            direction_label="UP",
            predicted_label="UP",
            max_favorable_move_atr=1.1,
            max_adverse_move_atr=0.2,
            tp_before_sl=True,
            features_json={"trend_strength": 1.0, "volume_ratio_20": 1.3, "hammer_score": 0.7, "support_distance_atr": 0.2},
        ),
        {
            "direction_label": "DOWN",
            "predicted_label": "UP",
            "max_favorable_move_atr": 0.3,
            "max_adverse_move_atr": 1.0,
            "tp_before_sl": False,
            "features_json": {"trend_strength": -1.0, "volume_ratio_20": 0.7, "shooting_star_score": 0.7, "resistance_distance_atr": 0.2},
        },
    ]
    return BookDrivenForensicAudit().evaluate(
        rows,
        candidate_payload={
            "candidate_status": "REJECTED",
            "failed_gates": ["collapse_gate"],
            "baseline_edge": -0.02,
            "model_accuracy": 0.34,
            "baseline_accuracy": 0.5,
            "collapse_severity": "CRITICAL",
            "prediction_root_cause_audit": {
                "warnings": ["actual_down_rows_mapped_to_up"],
            },
        },
    )


def test_book_driven_forensic_audit_returns_non_empty_diagnosis_and_recommendation() -> None:
    payload = _book_audit()

    assert payload["diagnostic_name"] == "book_driven_forensic_audit"
    assert payload["final_diagnosis"]
    assert payload["next_action_recommendation"]


def test_training_pipeline_report_contains_book_driven_forensic_audit(tmp_path: Path) -> None:
    audit = _book_audit()
    result = TrainingPipelineResult(
        run_id="book_forensic_case",
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
        book_driven_forensic_audit=audit,
    )

    path = TrainingPipelineReporter().write_json_report(result)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["book_driven_forensic_audit"]["diagnostic_name"] == "book_driven_forensic_audit"
    assert payload["book_driven_forensic_audit"]["final_diagnosis"]


def test_candidate_json_contains_book_driven_forensic_audit(tmp_path: Path) -> None:
    audit = _book_audit()
    candidate = {
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
        "book_driven_forensic_audit": audit,
        "prediction_root_cause_audit": {"warnings": ["actual_down_rows_mapped_to_up"]},
    }

    path = FeatureRegimeExperimentReporter().write_candidate_json(candidate, tmp_path / "candidate.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["book_driven_forensic_audit"]["diagnostic_name"] == "book_driven_forensic_audit"
    assert payload["book_driven_forensic_audit"]["next_action_recommendation"]


def test_multi_symbol_summary_contains_aggregated_forensic_summary(tmp_path: Path) -> None:
    audit = _book_audit()
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
        "candidate_results": [
            {
                "config_id": "cfg_1",
                "candidate_status": "REJECTED",
                "status": "COMPLETED",
                "score": -2.0,
                "baseline_edge": -0.02,
                "baseline_edge_status": "NEGATIVE_EDGE",
                "model_accuracy": 0.34,
                "baseline_accuracy": 0.5,
                "collapse_detected": True,
                "collapse_type": "UP_DOMINANCE",
                "collapse_severity": "CRITICAL",
                "collapse_gate_failed": True,
                "profit_factor": 0.95,
                "profit_total_r": -0.2,
                "walk_forward_profit_factor": 0.97,
                "walk_forward_global_total_r": -0.1,
                "failed_gates": ["collapse_gate", "walk_forward_gate"],
                "passed_gates": [],
                "book_driven_forensic_audit": audit,
                "prediction_root_cause_audit": {
                    "diagnostic_name": "prediction_root_cause_audit",
                    "warnings": ["actual_down_rows_mapped_to_up"],
                },
            }
        ],
        "configs_ranked": [
            {
                "config_id": "cfg_1",
                "candidate_status": "REJECTED",
                "score": -2.0,
                "book_driven_forensic_audit": audit,
                "prediction_root_cause_audit": {
                    "diagnostic_name": "prediction_root_cause_audit",
                    "warnings": ["actual_down_rows_mapped_to_up"],
                },
            }
        ],
    }
    path = tmp_path / "feature_regime_experiment_summary.json"
    path.write_text(json.dumps(summary), encoding="utf-8")

    payload = MultiSymbolFeatureRegimeAnalyzer().analyze([path])

    assert payload["book_driven_forensic_summary"]["diagnostic_name"] == "book_driven_forensic_summary"
    assert payload["book_driven_forensic_summary"]["available_candidate_count"] == 1
    assert payload["book_driven_forensic_summary"]["top_final_diagnoses"]

