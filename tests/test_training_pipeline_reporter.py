import json

from app.training.training_pipeline_reporter import TrainingPipelineReporter
from app.training.training_pipeline_runner import (
    LongHistoryTrainingPipelineRunner,
    TrainingPipelineConfig,
    TrainingPipelineResult,
    TrainingPipelineStageResult,
)


def test_training_pipeline_reporter_compact_summary_contains_counts_and_paths(tmp_path) -> None:
    runner = LongHistoryTrainingPipelineRunner()
    reporter = TrainingPipelineReporter()
    result = runner.run(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            run_id="reporter_case",
            dry_run=True,
            output_dir=tmp_path,
        )
    )

    payload = reporter.compact_summary_to_dict(result)

    assert payload["run_id"] == "reporter_case"
    assert payload["status"] == "DRY_RUN_COMPLETED"
    assert payload["stage_count"] == len(result.stage_results)
    assert payload["log_path"]
    assert payload["events_path"]


def test_training_pipeline_reporter_writes_json_and_markdown(tmp_path) -> None:
    runner = LongHistoryTrainingPipelineRunner()
    reporter = TrainingPipelineReporter()
    result = runner.run(
        TrainingPipelineConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            run_id="report_files_case",
            dry_run=True,
            output_dir=tmp_path,
        )
    )

    json_path = reporter.write_json_report(result)
    markdown_path = reporter.write_markdown_report(result)

    assert json_path.exists()
    assert markdown_path.exists()
    json.loads(json_path.read_text(encoding="utf-8"))

    text = markdown_path.read_text(encoding="utf-8")
    assert "training_pipeline.log" in text
    assert "training_pipeline_events.jsonl" in text
    assert "no live trading" in text
    assert "no orders" in text
    assert "no traders-core integration" in text


def test_training_pipeline_reporter_compact_summary_reports_zero_skips_for_real_result() -> None:
    reporter = TrainingPipelineReporter()
    result = TrainingPipelineResult(
        run_id="real_summary_case",
        status="COMPLETED",
        symbol="BTCUSDT",
        interval="15m",
        start_date="2025-01-01",
        end_date="2025-01-10",
        dry_run=False,
        sample_mode=False,
        run_gate_policy_replay=True,
        export_report=True,
        started_at="2026-06-11T10:00:00+00:00",
        ended_at="2026-06-11T10:01:00+00:00",
        duration_seconds=60.0,
        stage_results=(
            TrainingPipelineStageResult(
                stage="train_model",
                status="COMPLETED",
                message="ok",
                duration_seconds=1.0,
                started_at="2026-06-11T10:00:00+00:00",
                ended_at="2026-06-11T10:00:01+00:00",
                data={"model_version": "ml_test_v1"},
            ),
        ),
        quality_summary={"quality_status": "NEEDS_MORE_DATA"},
        model_summary={"model_version": "ml_test_v1"},
        baseline_summary={"baseline_accuracy": 0.45},
        gate_policy_replay_summary={"gate_policy_replay_status": "SAMPLE_ONLY"},
        gap_quality_summary={"gap_severity": "OK", "dataset_safe_for_training": True, "gap_count": 0},
        anti_collapse_summary={"collapse_detected": False, "collapse_type": "NONE"},
        candidate_selection_summary={"candidate_status": "NEEDS_MORE_DATA", "candidate_decision": "INSUFFICIENT_METRICS"},
        label_config_summary={"label_version": "lv1", "horizon_candles": 8},
        quality_gates_summary={"passed_gates": ["gap_quality_gate"], "failed_gates": ["baseline_edge_gate"]},
        output_dir="reports/training_pipeline_runs/real_summary_case",
        log_path="reports/training_pipeline_runs/real_summary_case/training_pipeline.log",
        events_path="reports/training_pipeline_runs/real_summary_case/training_pipeline_events.jsonl",
        json_report_path="reports/training_pipeline_runs/real_summary_case/training_pipeline_report.json",
        markdown_report_path="reports/training_pipeline_runs/real_summary_case/training_pipeline_report.md",
        safety={
            "approved_for_traders_core_integration": False,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "traders_core_connected": False,
            "live_trading_connected": False,
            "orders_enabled": False,
        },
        command_snapshot={"symbol": "BTCUSDT"},
        next_recommendations=("Keep live trading, orders, and traders-core integration disabled.",),
    )

    payload = reporter.compact_summary_to_dict(result)

    assert payload["status"] == "COMPLETED"
    assert payload["completed_stage_count"] == 1
    assert payload["failed_stage_count"] == 0
    assert payload["skipped_stage_count"] == 0


def test_training_pipeline_report_json_includes_prediction_root_cause_audit(tmp_path) -> None:
    reporter = TrainingPipelineReporter()
    result = TrainingPipelineResult(
        run_id="root_cause_report_case",
        status="COMPLETED",
        symbol="SOLUSDT",
        interval="15m",
        start_date="2025-01-01",
        end_date="2025-01-10",
        dry_run=False,
        sample_mode=False,
        run_gate_policy_replay=True,
        export_report=True,
        started_at="2026-06-11T10:00:00+00:00",
        ended_at="2026-06-11T10:01:00+00:00",
        duration_seconds=60.0,
        stage_results=(),
        quality_summary={"quality_status": "QUALITY_REJECTED"},
        model_summary={"model_version": "ml_test_v1"},
        baseline_summary={"baseline_accuracy": 0.45},
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
        prediction_root_cause_audit={
            "diagnostic_name": "prediction_root_cause_audit",
            "diagnostic_version": "ml38_9_6",
            "warnings": ["actual_down_rows_mapped_to_up"],
        },
    )

    path = reporter.write_json_report(result)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["prediction_root_cause_audit"]["diagnostic_name"] == "prediction_root_cause_audit"
    assert payload["prediction_root_cause_audit"]["warnings"] == ["actual_down_rows_mapped_to_up"]
