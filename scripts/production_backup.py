"""Bounded no-secret production backup/PITR operator commands."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_safety.production_backup import (
    BackupManifest,
    POLICY,
    PRODUCTION_SCHEMA_HEAD,
    atomic_json_write,
    catalog_health,
    evaluate_health,
    file_sha256,
    iso_utc,
    load_catalog,
    publish_manifest,
    retention_plan,
    safe_artifact_id,
    tree_sha256,
    utc_now,
    parse_utc,
)
from scripts.security_retry_controls import inspect_postgres_archive_health

CONTAINER = "traders-ml-postgres-1"
DB_USER = "traders_ml"
DB_NAME = "traders_ml"
CONTAINER_RECOVERY_ROOT = "/var/lib/postgresql/recovery"
SAFE_ROOT = Path(r"D:\traders_ml_recovery\postgres")


class OperationFailure(RuntimeError):
    pass


def run(command: list[str], *, timeout: int = 3600) -> subprocess.CompletedProcess[str]:
    rendered = " ".join(command)
    if "://" in rendered:
        raise OperationFailure("PROTECTED_BINDING_OR_URI_IN_COMMAND")
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise OperationFailure("COMMAND_EXECUTION_FAILED") from error
    if result.returncode:
        raise OperationFailure("COMMAND_NONZERO")
    return result


def validate_root(root: Path) -> None:
    resolved = root.resolve()
    forbidden = (ROOT.resolve(), ROOT.parent / "traders-client", ROOT.parent / "evidence_inbox")
    if any(resolved == item.resolve() or item.resolve() in resolved.parents for item in forbidden):
        raise OperationFailure("UNSAFE_STORAGE_ROOT")
    if resolved != SAFE_ROOT.resolve():
        raise OperationFailure("UNAPPROVED_STORAGE_ROOT")
    for name in ("logical", "base", "wal_archive", "catalog", "catalog/manifests", "rehearsal"):
        (resolved / name).mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(resolved).free < 2 * 1024**3:
        raise OperationFailure("INSUFFICIENT_FREE_SPACE")


def create_logical(root: Path) -> dict[str, object]:
    validate_root(root)
    now = utc_now()
    artifact_id = safe_artifact_id("logical", now, secrets.token_hex(4))
    container_temp = f"/tmp/{artifact_id}.dump"
    staged = root / "logical" / f"{artifact_id}.dump.in_progress"
    published = root / "logical" / f"{artifact_id}.dump"
    started = time.monotonic()
    try:
        run(["docker", "exec", "--user", "postgres", CONTAINER, "pg_dump", "-U", DB_USER, "-d", DB_NAME, "-Fc", "-f", container_temp])
        run(["docker", "exec", "--user", "postgres", CONTAINER, "pg_restore", "-l", container_temp])
        run(["docker", "cp", f"{CONTAINER}:{container_temp}", str(staged)])
        if not staged.is_file() or staged.stat().st_size <= 0:
            raise OperationFailure("BACKUP_SIZE_INVALID")
        checksum = file_sha256(staged)
        if file_sha256(staged) != checksum:
            raise OperationFailure("BACKUP_CHECKSUM_UNSTABLE")
        os.replace(staged, published)
        version = run(["docker", "exec", CONTAINER, "pg_dump", "--version"]).stdout.strip()
        manifest = BackupManifest(
            artifact_id, "LOGICAL", iso_utc(now), 16, "PRODUCTION",
            PRODUCTION_SCHEMA_HEAD, "PG_DUMP_CUSTOM", published.stat().st_size,
            checksum, version, "PUBLISHED", "PAPER_FIRST_MILESTONE_24H_MINIMUM",
            published.relative_to(root).as_posix(), True, False,
        )
        publish_manifest(root, manifest)
        return {"artifact_id": artifact_id, "bytes": manifest.size_bytes, "sha256": checksum,
                "duration_seconds": round(time.monotonic() - started, 3), "published": True}
    finally:
        subprocess.run(["docker", "exec", "--user", "postgres", CONTAINER, "rm", "-f", container_temp], check=False, capture_output=True)
        if staged.exists():
            staged.unlink()


def create_base(root: Path) -> dict[str, object]:
    validate_root(root)
    now = utc_now()
    artifact_id = safe_artifact_id("base", now, secrets.token_hex(4))
    relative_published = f"base/{artifact_id}"
    container_staged = f"/tmp/{artifact_id}.in_progress"
    host_staged = root / "base" / f"{artifact_id}.in_progress"
    published = root / relative_published
    started = time.monotonic()
    try:
        run(["docker", "exec", "--user", "postgres", CONTAINER, "pg_basebackup", "-U", DB_USER, "-D", container_staged, "-Fp", "-X", "stream", "-c", "fast"], timeout=3600)
        run(["docker", "exec", "--user", "postgres", CONTAINER, "pg_verifybackup", container_staged], timeout=1800)
        run(["docker", "cp", f"{CONTAINER}:{container_staged}", str(host_staged)], timeout=1800)
        if published.exists():
            raise OperationFailure("BASE_BACKUP_TARGET_EXISTS")
        os.replace(host_staged, published)
        checksum, size = tree_sha256(published)
        version = run(["docker", "exec", CONTAINER, "pg_basebackup", "--version"]).stdout.strip()
        manifest = BackupManifest(
            artifact_id, "BASE", iso_utc(now), 16, "PRODUCTION",
            PRODUCTION_SCHEMA_HEAD, "PG_BASEBACKUP_PLAIN", size, checksum,
            version, "PUBLISHED", "PAPER_FIRST_MILESTONE_24H_MINIMUM",
            relative_published, False, True,
        )
        publish_manifest(root, manifest)
        return {"artifact_id": artifact_id, "bytes": size, "sha256": checksum,
                "duration_seconds": round(time.monotonic() - started, 3), "published": True}
    finally:
        subprocess.run(["docker", "exec", "--user", "postgres", CONTAINER, "rm", "-rf", container_staged], check=False, capture_output=True)


def sync_wal(root: Path) -> dict[str, object]:
    validate_root(root)
    listing = run([
        "docker", "exec", "--user", "postgres", CONTAINER, "sh", "-c",
        "for f in /var/lib/postgresql/wal_export/*; do [ -f \"$f\" ] && basename \"$f\"; done 2>/dev/null || true",
    ]).stdout.splitlines()
    allowed_name = re.compile(
        r"^(?:[0-9A-F]{24}|[0-9A-F]{24}\.[0-9A-F]{8}\.backup|[0-9A-F]{8}\.history)$"
    )
    segments = sorted({name for name in listing if allowed_name.fullmatch(name)})[:8]
    published: list[str] = []
    for name in segments:
        staged = root / "wal_archive" / f"{name}.in_progress"
        target = root / "wal_archive" / name
        run(["docker", "cp", f"{CONTAINER}:/var/lib/postgresql/wal_export/{name}", str(staged)])
        staged_hash = file_sha256(staged)
        if target.exists():
            if file_sha256(target) != staged_hash:
                staged.unlink()
                raise OperationFailure("WAL_ARCHIVE_CONFLICT")
            staged.unlink()
        else:
            os.replace(staged, target)
            if file_sha256(target) != staged_hash:
                raise OperationFailure("WAL_ARCHIVE_CHECKSUM_MISMATCH")
        run(["docker", "exec", "--user", "postgres", CONTAINER, "touch", f"/var/lib/postgresql/wal_export/{name}.ack"])
        published.append(name)
    last = run([
        "docker", "exec", "--user", "postgres", CONTAINER, "psql", "-U", DB_USER,
        "-d", DB_NAME, "-AtX", "-c", "SELECT COALESCE(last_archived_wal, '') FROM pg_stat_archiver",
    ]).stdout.strip()
    cleaned = 0
    if allowed_name.fullmatch(last):
        for name in segments:
            target = root / "wal_archive" / name
            if name <= last and target.is_file():
                run(["docker", "exec", "--user", "postgres", CONTAINER, "rm", "-f",
                     f"/var/lib/postgresql/wal_export/{name}",
                     f"/var/lib/postgresql/wal_export/{name}.ack"])
                cleaned += 1
    return {"published_segment_count": len(published), "cleaned_staging_count": cleaned,
            "segments": published}


def verify(root: Path) -> dict[str, object]:
    validate_root(root)
    health = catalog_health(root)
    return {"healthy": health.healthy, "verified_entries": health.verified_entries,
            "logical": health.valid_logical_backups, "base": health.valid_base_backups,
            "error_code": health.error_code}


def refresh_monitoring(root: Path, *, record_rehearsals: bool) -> dict[str, object]:
    validate_root(root)
    path = root / "catalog" / "runtime_state.json"
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    now = utc_now()
    archive = inspect_postgres_archive_health(CONTAINER)
    if archive.error_class != "NONE":
        raise OperationFailure("ARCHIVE_HEALTH_UNAVAILABLE")
    entries = load_catalog(root)
    bases = [item for item in entries if item.artifact_type == "BASE"]
    pitr_window = 0 if not bases else max(
        0, int((now - max(parse_utc(item.created_at) for item in bases)).total_seconds())
    )
    payload = {
        "schema": "TRADERS_ML_BACKUP_RUNTIME_STATE_V1",
        "updated_at": iso_utc(now),
        "wal_archive_progressing": bool(archive.archived_segment_observed and not archive.unresolved_failure),
        "wal_archive_failure_count": int(archive.unresolved_failure is True),
        "wal_archive_historical_failure_count": archive.failed_count,
        "wal_archive_last_success_age_seconds": archive.last_success_age_seconds,
        "pitr_window_seconds": pitr_window,
        "last_restore_rehearsal": iso_utc(now) if record_rehearsals else previous.get("last_restore_rehearsal"),
        "last_pitr_rehearsal": iso_utc(now) if record_rehearsals else previous.get("last_pitr_rehearsal"),
    }
    atomic_json_write(path, payload)
    return payload


def _wait_postgres(container: str, user: str, database: str, *, attempts: int = 180) -> None:
    for _ in range(attempts):
        try:
            run(["docker", "exec", "--user", "postgres", container,
                 "pg_isready", "-U", user, "-d", database], timeout=10)
            return
        except OperationFailure:
            time.sleep(2)
    raise OperationFailure("ISOLATED_POSTGRES_NOT_READY")


def restore_logical(root: Path) -> dict[str, object]:
    validate_root(root)
    logical = [item for item in load_catalog(root) if item.artifact_type == "LOGICAL"]
    if not logical:
        raise OperationFailure("LOGICAL_BACKUP_MISSING")
    item = max(logical, key=lambda value: value.created_at)
    name = f"traders-ml-logical-restore-{secrets.token_hex(4)}"
    artifact = root / item.relative_path
    mount = f"type=bind,source={artifact},target=/backup.dump,readonly"
    started = time.monotonic()
    try:
        run(["docker", "run", "-d", "--name", name, "--network", "none",
             "--mount", mount, "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "postgres:16-alpine"])
        _wait_postgres(name, "postgres", "postgres")
        run(["docker", "exec", "--user", "postgres", name, "createdb", "-U", "postgres", "restore_target"])
        run(["docker", "exec", "--user", "postgres", name, "pg_restore", "-U", "postgres",
             "-d", "restore_target", "--no-owner", "--no-acl", "--exit-on-error", "/backup.dump"], timeout=3600)
        head = run(["docker", "exec", "--user", "postgres", name, "psql", "-U", "postgres",
                    "-d", "restore_target", "-AtX", "-c", "SELECT version_num FROM alembic_version"]).stdout.strip()
        if head != PRODUCTION_SCHEMA_HEAD:
            raise OperationFailure("RESTORED_SCHEMA_MISMATCH")
        return {"restored": True, "schema_head": head,
                "duration_seconds": round(time.monotonic() - started, 3), "cleanup_required": False}
    finally:
        subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True)


def rehearse_pitr(root: Path, target_name: str) -> dict[str, object]:
    validate_root(root)
    if not re.fullmatch(r"[a-z0-9_]{1,63}", target_name):
        raise OperationFailure("INVALID_RECOVERY_TARGET_NAME")
    bases = [item for item in load_catalog(root) if item.artifact_type == "BASE"]
    if not bases:
        raise OperationFailure("BASE_BACKUP_MISSING")
    item = max(bases, key=lambda value: value.created_at)
    nonce = secrets.token_hex(4)
    volume = f"traders_ml_pitr_rehearsal_{nonce}_data"
    container = f"traders-ml-pitr-rehearsal-{nonce}"
    base_mount = f"type=bind,source={root / item.relative_path},target=/source,readonly"
    wal_mount = f"type=bind,source={root / 'wal_archive'},target=/wal,readonly"
    started = time.monotonic()
    try:
        run(["docker", "volume", "create", volume])
        run(["docker", "run", "--rm", "--mount", base_mount, "-v", f"{volume}:/target",
             "postgres:16-alpine", "sh", "-c",
             "cp -a /source/. /target/ && touch /target/recovery.signal && chown -R postgres:postgres /target && chmod 700 /target"], timeout=1800)
        run(["docker", "run", "-d", "--name", container, "--network", "none",
             "-v", f"{volume}:/var/lib/postgresql/data", "--mount", wal_mount,
             "postgres:16-alpine", "postgres", "-c", "restore_command=cp /wal/%f %p",
             "-c", f"recovery_target_name={target_name}", "-c", "recovery_target_action=pause"])
        _wait_postgres(container, DB_USER, DB_NAME)
        paused = False
        for _ in range(180):
            result = run(["docker", "exec", "--user", "postgres", container, "psql", "-U", DB_USER,
                          "-d", DB_NAME, "-AtX", "-c", "SELECT pg_is_in_recovery() AND pg_is_wal_replay_paused()"])
            if result.stdout.strip() == "t":
                paused = True
                break
            time.sleep(2)
        head = run(["docker", "exec", "--user", "postgres", container, "psql", "-U", DB_USER,
                    "-d", DB_NAME, "-AtX", "-c", "SELECT version_num FROM alembic_version"]).stdout.strip()
        if not paused or head != PRODUCTION_SCHEMA_HEAD:
            raise OperationFailure("PITR_TARGET_VALIDATION_FAILED")
        return {"recovered": True, "target_accuracy": "PASS", "schema_head": head,
                "duration_seconds": round(time.monotonic() - started, 3), "cleanup_required": False}
    finally:
        subprocess.run(["docker", "rm", "-f", container], check=False, capture_output=True)
        subprocess.run(["docker", "volume", "rm", volume], check=False, capture_output=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("preflight", "create-logical", "restore-logical", "create-base", "sync-wal", "rehearse-pitr", "verify", "catalog", "retention-dry-run", "record-rehearsals", "refresh-monitoring", "health"))
    parser.add_argument("--root", type=Path, default=SAFE_ROOT)
    parser.add_argument("--recovery-target-name", default="traders_ml_backup_pitr_controlled_01")
    args = parser.parse_args(argv)
    try:
        validate_root(args.root)
        if args.operation == "preflight":
            result: object = {"ready": True, "free_space_class": "PASS_AT_LEAST_2_GIB", "policy": POLICY.__dict__ if hasattr(POLICY, "__dict__") else "APPROVED_TECHNICAL_POLICY"}
        elif args.operation == "create-logical":
            result = create_logical(args.root)
        elif args.operation == "restore-logical":
            result = restore_logical(args.root)
        elif args.operation == "create-base":
            result = create_base(args.root)
        elif args.operation == "sync-wal":
            result = sync_wal(args.root)
        elif args.operation == "rehearse-pitr":
            result = rehearse_pitr(args.root, args.recovery_target_name)
        elif args.operation == "verify":
            result = verify(args.root)
        elif args.operation == "catalog":
            result = [item.to_json() for item in load_catalog(args.root)]
        elif args.operation == "retention-dry-run":
            result = retention_plan(load_catalog(args.root), now=utc_now()).__dict__ if hasattr(retention_plan(load_catalog(args.root), now=utc_now()), "__dict__") else {"candidates": retention_plan(load_catalog(args.root), now=utc_now()).candidates, "dry_run": True}
        elif args.operation in {"record-rehearsals", "refresh-monitoring"}:
            result = refresh_monitoring(args.root, record_rehearsals=args.operation == "record-rehearsals")
        else:
            state = args.root / "catalog" / "runtime_state.json"
            runtime = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
            result = evaluate_health(
                root=args.root, now=utc_now(),
                wal_archive_progressing=bool(runtime.get("wal_archive_progressing")),
                wal_archive_failure_count=int(runtime.get("wal_archive_failure_count", 0)),
                pitr_window=timedelta(seconds=int(runtime.get("pitr_window_seconds", 0))),
                last_restore_rehearsal=(parse_utc(runtime["last_restore_rehearsal"]) if runtime.get("last_restore_rehearsal") else None),
                last_pitr_rehearsal=(parse_utc(runtime["last_pitr_rehearsal"]) if runtime.get("last_pitr_rehearsal") else None),
            )
            result = {name: getattr(result, name) for name in result.__dataclass_fields__}
        print(json.dumps(result, sort_keys=True, default=list))
        return 0
    except (OSError, ValueError, OperationFailure, json.JSONDecodeError) as error:
        print(json.dumps({"status": "FAILED", "error_class": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
