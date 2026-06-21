from pathlib import Path

from app.reporting.compact_report import (
    COMPACT_REPORT_PROFILE,
    CompactReportBuilder,
    build_archive_manifest,
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


def test_archive_manifest_detects_model_artifact_and_largest_files(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    model_dir = archive_root / "artifacts" / "models" / "candidate"
    model_dir.mkdir(parents=True)
    (model_dir / "model.pt").write_bytes(b"x" * 128)
    (archive_root / "summary.json").write_text("{}", encoding="utf-8")

    manifest = build_archive_manifest(archive_root, report_profile=COMPACT_REPORT_PROFILE)

    assert manifest["file_count"] == 2
    assert manifest["model_artifacts_included"] is True
    assert manifest["largest_files"][0]["path"].endswith("model.pt")


def test_should_include_report_file_excludes_model_binaries(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    model_file = archive_root / "artifacts" / "models" / "candidate" / "model.pt"
    normal_file = archive_root / "multi_symbol_feature_regime_analysis.md"
    model_file.parent.mkdir(parents=True)
    model_file.write_bytes(b"model")
    normal_file.write_text("# ok", encoding="utf-8")

    assert should_include_report_file(model_file, archive_root=archive_root) is False
    assert should_include_report_file(normal_file, archive_root=archive_root) is True
