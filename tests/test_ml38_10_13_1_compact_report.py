from pathlib import Path

from app.reporting.compact_report import (
    COMPACT_REPORT_PROFILE,
    DEBUG_REPORT_PROFILE,
    STRICT_COMPACT_EXCLUSION_REASON,
    CompactReportBuilder,
    build_archive_manifest,
    report_file_exclusion_reason,
    should_include_report_file,
)


def test_compact_report_omits_heavy_prediction_rows_but_keeps_core_audits() -> None:
    payload = {
        "symbol": "SOLUSDT",
        "best_candidate_config_id": "lv19_h12_tts_thr065_sqmask060",
        "profit_exit_root_cause_audit": {"primary_root_cause": "stop_loss_hit"},
        "raw_predictions": [{"row": index} for index in range(500)],
    }

    compact = CompactReportBuilder().compact_payload(payload, profile=COMPACT_REPORT_PROFILE)

    assert compact["symbol"] == "SOLUSDT"
    assert compact["profit_exit_root_cause_audit"]["primary_root_cause"] == "stop_loss_hit"
    assert compact["raw_predictions"]["omitted"] is True
    assert compact["raw_predictions"]["original_count"] == 500


def test_archive_manifest_reports_included_and_pruned_files(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    model_dir = archive_root / "artifacts" / "models" / "candidate"
    model_dir.mkdir(parents=True)
    (model_dir / "model.pt").write_bytes(b"x" * 128)
    (archive_root / "summary.json").write_text("{}", encoding="utf-8")

    manifest = build_archive_manifest(archive_root, report_profile=COMPACT_REPORT_PROFILE)

    assert manifest["stage_file_count"] == 2
    assert manifest["file_count"] == 1
    assert manifest["pruned_file_count"] == 1
    assert manifest["model_artifacts_present_in_stage"] is True
    assert manifest["model_artifacts_included"] is False
    assert manifest["largest_files"][0]["path"] == "summary.json"
    assert manifest["largest_pruned_files"][0]["path"].endswith("model.pt")


def test_should_include_report_file_excludes_model_binaries(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    model_file = archive_root / "artifacts" / "models" / "candidate" / "model.pt"
    normal_file = archive_root / "multi_symbol_feature_regime_analysis.md"
    model_file.parent.mkdir(parents=True)
    model_file.write_bytes(b"model")
    normal_file.write_text("# ok", encoding="utf-8")

    assert should_include_report_file(model_file, archive_root=archive_root) is False
    assert should_include_report_file(normal_file, archive_root=archive_root) is True


def test_strict_compact_archive_prunes_runtime_stream_files(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    stdout_file = archive_root / "raw_outputs" / "SOLUSDT-run.stdout.json"
    pipeline_log = archive_root / "per_symbol" / "pipeline_runs" / "run1" / "training_pipeline.log"
    pipeline_events = archive_root / "per_symbol" / "pipeline_runs" / "run1" / "training_pipeline_events.jsonl"
    keep_report = archive_root / "multi_symbol_feature_regime_analysis.md"

    stdout_file.parent.mkdir(parents=True, exist_ok=True)
    pipeline_log.parent.mkdir(parents=True, exist_ok=True)
    keep_report.parent.mkdir(parents=True, exist_ok=True)

    stdout_file.write_text("{}", encoding="utf-8")
    pipeline_log.write_text("large log", encoding="utf-8")
    pipeline_events.write_text("{}\n", encoding="utf-8")
    keep_report.write_text("# keep", encoding="utf-8")

    assert should_include_report_file(
        stdout_file,
        archive_root=archive_root,
        report_profile=COMPACT_REPORT_PROFILE,
    ) is False
    assert report_file_exclusion_reason(
        stdout_file,
        archive_root=archive_root,
        report_profile=COMPACT_REPORT_PROFILE,
    ) == STRICT_COMPACT_EXCLUSION_REASON
    assert should_include_report_file(
        pipeline_log,
        archive_root=archive_root,
        report_profile=COMPACT_REPORT_PROFILE,
    ) is False
    assert should_include_report_file(
        pipeline_events,
        archive_root=archive_root,
        report_profile=COMPACT_REPORT_PROFILE,
    ) is False
    assert should_include_report_file(
        keep_report,
        archive_root=archive_root,
        report_profile=COMPACT_REPORT_PROFILE,
    ) is True


def test_debug_profile_keeps_runtime_stream_files_but_not_model_artifacts(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    stdout_file = archive_root / "raw_outputs" / "SOLUSDT-run.stdout.json"
    model_file = archive_root / "artifacts" / "models" / "candidate" / "model.pt"
    stdout_file.parent.mkdir(parents=True)
    model_file.parent.mkdir(parents=True)
    stdout_file.write_text("{}", encoding="utf-8")
    model_file.write_bytes(b"model")

    assert should_include_report_file(
        stdout_file,
        archive_root=archive_root,
        report_profile=DEBUG_REPORT_PROFILE,
    ) is True
    assert should_include_report_file(
        model_file,
        archive_root=archive_root,
        report_profile=DEBUG_REPORT_PROFILE,
    ) is False
