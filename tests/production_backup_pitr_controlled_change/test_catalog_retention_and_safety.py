from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.engine_safety import production_backup as backup


NOW = datetime(2026, 8, 11, tzinfo=timezone.utc)


def manifest(tmp_path: Path, artifact_id: str, kind: str, age_days: int = 0) -> backup.BackupManifest:
    directory = "logical" if kind == "LOGICAL" else "base"
    suffix = ".dump" if kind == "LOGICAL" else ""
    path = tmp_path / directory / f"{artifact_id}{suffix}"
    if kind == "LOGICAL":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(artifact_id.encode())
        checksum, size = backup.file_sha256(path), path.stat().st_size
    else:
        path.mkdir(parents=True, exist_ok=True)
        (path / "backup_manifest").write_text(artifact_id, encoding="utf-8")
        checksum, size = backup.tree_sha256(path)
    return backup.BackupManifest(
        artifact_id, kind, backup.iso_utc(NOW - timedelta(days=age_days)), 16,
        "PRODUCTION", backup.PRODUCTION_SCHEMA_HEAD,
        "PG_DUMP_CUSTOM" if kind == "LOGICAL" else "PG_BASEBACKUP_PLAIN",
        size, checksum, "PostgreSQL 16", "PUBLISHED",
        "PAPER_FIRST_MILESTONE_24H_MINIMUM", path.relative_to(tmp_path).as_posix(),
        kind == "LOGICAL", kind == "BASE",
    )


def test_atomic_catalog_publication_and_integrity(tmp_path) -> None:
    item = manifest(tmp_path, "logical-20260811T000000Z-00000001", "LOGICAL")
    backup.publish_manifest(tmp_path, item)
    assert backup.load_catalog(tmp_path) == (item,)
    health = backup.catalog_health(tmp_path)
    assert health.healthy and health.valid_logical_backups == 1
    assert not list((tmp_path / "catalog").glob("*.in_progress"))


def test_catalog_detects_missing_corrupt_orphan_and_unmanifested(tmp_path) -> None:
    item = manifest(tmp_path, "logical-20260811T000000Z-00000001", "LOGICAL")
    backup.publish_manifest(tmp_path, item)
    (tmp_path / item.relative_path).write_bytes(b"corrupt")
    (tmp_path / "logical" / "unmanifested.dump").write_bytes(b"x")
    (tmp_path / "catalog" / "manifests" / "logical-20260811T000001Z-00000002.json").write_text("{}", encoding="utf-8")
    health = backup.catalog_health(tmp_path)
    assert not health.healthy
    assert item.artifact_id in health.checksum_mismatches
    assert "unmanifested.dump" in health.unmanifested_artifacts
    assert health.orphan_manifests


def test_catalog_detects_missing_artifact(tmp_path) -> None:
    item = manifest(tmp_path, "logical-20260811T000000Z-00000001", "LOGICAL")
    backup.publish_manifest(tmp_path, item)
    (tmp_path / item.relative_path).unlink()
    assert item.artifact_id in backup.catalog_health(tmp_path).missing_artifacts


def test_retention_never_deletes_two_logical_or_last_base_and_is_bounded(tmp_path) -> None:
    items = []
    for index in range(12):
        items.append(manifest(tmp_path, f"logical-202607{index + 1:02d}T000000Z-{index:08x}", "LOGICAL", 40 - index))
    items.append(manifest(tmp_path, "base-20260701T000000Z-00000020", "BASE", 41))
    items.append(manifest(tmp_path, "base-20260810T000000Z-00000021", "BASE", 1))
    decision = backup.retention_plan(items, now=NOW)
    assert decision.dry_run_required and decision.bounded
    assert len(decision.candidates) <= backup.RETENTION_DELETE_BATCH
    assert {items[10].artifact_id, items[11].artifact_id, items[-1].artifact_id} <= set(decision.protected)


def test_retention_apply_requires_prior_dry_run_ack(tmp_path) -> None:
    decision = backup.RetentionDecision((), (), True, True)
    with pytest.raises(ValueError, match="RETENTION_DRY_RUN_ACK_REQUIRED"):
        backup.apply_retention(tmp_path, decision, dry_run_ack=False)


@pytest.mark.parametrize("bad", ("../x", "/absolute", "C:/absolute"))
def test_manifest_rejects_unsafe_artifact_paths(bad: str) -> None:
    with pytest.raises(ValueError, match="UNSAFE_RELATIVE_PATH"):
        backup.BackupManifest(
            "logical-20260811T000000Z-00000001", "LOGICAL",
            "2026-08-11T00:00:00Z", 16, "PRODUCTION",
            backup.PRODUCTION_SCHEMA_HEAD, "PG_DUMP_CUSTOM", 1, "0" * 64,
            "PostgreSQL 16", "PUBLISHED", "PAPER_FIRST_MILESTONE_24H_MINIMUM",
            bad, True, False,
        )


def test_catalog_rejects_duplicate_ids(tmp_path) -> None:
    item = manifest(tmp_path, "logical-20260811T000000Z-00000001", "LOGICAL")
    backup.publish_manifest(tmp_path, item)
    with pytest.raises(ValueError, match="DUPLICATE_ARTIFACT_ID"):
        backup.publish_manifest(tmp_path, item)
