from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.experiments.compact_archive_pruner import (
    COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY,
    COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY_VERSION,
    CompactArchivePrunerError,
    compact_staged_symbol_output,
)
from app.reporting.compact_report import should_include_report_file


def _sidecar_dir(root: Path) -> Path:
    path = root / "label_grid_runtime" / "run1" / "prediction_payloads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_sidecar(
    root: Path,
    *,
    body: bytes | None = None,
    summary_overrides: dict | None = None,
    write_summary: bool = True,
    write_schema: bool = True,
) -> Path:
    sidecar_dir = _sidecar_dir(root)
    stream = sidecar_dir / "full_dataset_prediction_stream.jsonl"
    payload = body if body is not None else b'{"row":1}\n{"row":2}\n'
    stream.write_bytes(payload)
    if write_summary:
        summary = {
            "sha256": sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "row_count": 2,
            "sidecar_schema_version": "ml38.10.69",
            "schema_version": "ml38.10.69",
            "prediction_field_contract_version": "ml38.10.69",
            "line_ending_contract": "LF",
            "hash_contract": "EXACT_BYTES_AFTER_WRITE",
            "byte_size_contract": "EXACT_BYTES_AFTER_WRITE",
            "validation_status": "PREDICTION_SIDECAR_VALID",
        }
        summary.update(summary_overrides or {})
        (sidecar_dir / "full_dataset_prediction_stream_summary.json").write_text(
            json.dumps(summary),
            encoding="utf-8",
        )
    if write_schema:
        (sidecar_dir / "prediction_payload_schema.json").write_text(
            json.dumps({"schema_version": "ml38.10.69"}),
            encoding="utf-8",
        )
    return stream


def test_compact_archive_helper_imports_and_policy_version() -> None:
    assert COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY == (
        "COMPACT_ARCHIVE_MANIFEST_ONLY_LARGE_SIDECAR_STREAMS"
    )
    assert COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY_VERSION == "ml38.10.72"


def test_large_sidecar_switches_to_manifest_only_under_cap(tmp_path: Path) -> None:
    stream = _write_sidecar(tmp_path, body=(b'{"row":1}\n' * 5000))
    cap = 10_000

    result = compact_staged_symbol_output(
        tmp_path,
        max_archive_stage_bytes=cap,
        archive_root=tmp_path,
    )

    manifest_path = stream.with_name("prediction_sidecar_stream_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert result.sidecar_streams_seen == 1
    assert result.sidecar_streams_manifest_only == 1
    assert result.final_archive_size_bytes < cap
    assert manifest["policy_name"] == COMPACT_ARCHIVE_MANIFEST_ONLY_SIDECAR_POLICY
    assert manifest["omission_policy_version"] == "ml38.10.72"
    assert manifest["original_stream_relative_path"].endswith(
        "prediction_payloads/full_dataset_prediction_stream.jsonl"
    )
    assert manifest["stream_filename"] == "full_dataset_prediction_stream.jsonl"
    assert manifest["sha256"] == sha256(stream.read_bytes()).hexdigest()
    assert manifest["size_bytes"] == stream.stat().st_size
    assert manifest["row_count"] == 2
    assert manifest["sidecar_schema_version"] == "ml38.10.69"
    assert manifest["prediction_field_contract_version"] == "ml38.10.69"
    assert "size budget" in manifest["omission_reason"]
    assert manifest["full_stream_in_compact_archive"] is False
    assert manifest["full_stream_available_in_output_dir"] is True
    assert manifest["lf_only"] is True
    assert manifest["summary_hash_verified"] is True
    assert manifest["summary_size_verified"] is True
    assert stream.exists()
    assert stream.with_name("full_dataset_prediction_stream_summary.json").exists()
    assert stream.with_name("prediction_payload_schema.json").exists()
    assert not should_include_report_file(
        stream,
        archive_root=tmp_path,
        report_profile="compact",
    )
    zip_path = tmp_path / "compact.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in tmp_path.rglob("*"):
            if path.is_file() and path != zip_path and should_include_report_file(
                path,
                archive_root=tmp_path,
                report_profile="compact",
            ):
                archive.write(path, path.relative_to(tmp_path).as_posix())
    with ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        assert not any(name.endswith("full_dataset_prediction_stream.jsonl") for name in names)
        assert any(name.endswith("full_dataset_prediction_stream_summary.json") for name in names)
        assert any(name.endswith("prediction_payload_schema.json") for name in names)
        assert any(name.endswith("prediction_sidecar_stream_manifest.json") for name in names)


def test_small_sidecar_under_budget_is_included_normally(tmp_path: Path) -> None:
    stream = _write_sidecar(tmp_path)

    result = compact_staged_symbol_output(
        tmp_path,
        max_archive_stage_bytes=1024 * 1024,
        archive_root=tmp_path,
    )

    assert result.sidecar_streams_seen == 1
    assert result.sidecar_streams_manifest_only == 0
    assert not stream.with_name("prediction_sidecar_stream_manifest.json").exists()
    assert should_include_report_file(stream, archive_root=tmp_path, report_profile="compact")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"write_summary": False}, "SUMMARY_MISSING"),
        ({"summary_overrides": {"sha256": "bad"}}, "HASH_MISMATCH"),
        ({"summary_overrides": {"size_bytes": 1}}, "SIZE_MISMATCH"),
        ({"write_schema": False}, "SCHEMA_MISSING"),
        ({"body": b'{"row":1}\r\n'}, "LF_ONLY_MISMATCH"),
    ],
)
def test_manifest_only_fails_closed_for_invalid_sidecar_contract(
    tmp_path: Path,
    kwargs: dict,
    message: str,
) -> None:
    stream = _write_sidecar(tmp_path, **kwargs)

    with pytest.raises(CompactArchivePrunerError, match=message):
        compact_staged_symbol_output(
            tmp_path,
            max_archive_stage_bytes=max(1, stream.stat().st_size - 1),
            archive_root=tmp_path,
        )
    assert stream.exists()


def test_final_stage_size_still_above_cap_fails_with_largest_files(tmp_path: Path) -> None:
    stream = _write_sidecar(tmp_path)
    (tmp_path / "large_report.md").write_text("x" * 1000, encoding="utf-8")

    with pytest.raises(CompactArchivePrunerError, match="STAGE_SIZE_CAP_EXCEEDED"):
        compact_staged_symbol_output(
            tmp_path,
            max_archive_stage_bytes=10,
            archive_root=tmp_path,
        )
    assert stream.exists()


def test_no_silent_drop_duplicate_manifest_fails_closed(tmp_path: Path) -> None:
    stream = _write_sidecar(tmp_path, body=(b'{"row":1}\n' * 20))
    stream.with_name("prediction_sidecar_stream_manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(CompactArchivePrunerError, match="MANIFEST_DUPLICATE"):
        compact_staged_symbol_output(
            tmp_path,
            max_archive_stage_bytes=stream.stat().st_size - 1,
            archive_root=tmp_path,
        )


def test_manifest_cannot_claim_available_stream_when_stream_missing(tmp_path: Path) -> None:
    stream = _write_sidecar(tmp_path, body=(b'{"row":1}\n' * 20))
    stream.unlink()

    with pytest.raises(CompactArchivePrunerError, match="STREAM_MISSING"):
        compact_staged_symbol_output(
            tmp_path,
            max_archive_stage_bytes=1,
            archive_root=tmp_path,
        )
    assert not stream.with_name("prediction_sidecar_stream_manifest.json").exists()
