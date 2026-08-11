from __future__ import annotations

import os
import subprocess
import time

import pytest


pytestmark = pytest.mark.postgres
SOURCE = "traders-ml-wal-remediation-source-01"
RESTORE = "traders-ml-wal-remediation-restore-01"
BROKEN = "traders-ml-wal-remediation-broken-01"
DATA = "traders_ml_wal_remediation_source_01"
BASE = "traders_ml_wal_remediation_base_01"
ARCHIVE = "traders_ml_wal_remediation_archive_01"
RESTORE_DATA = "traders_ml_wal_remediation_restore_01"
BROKEN_DATA = "traders_ml_wal_remediation_broken_01"


def run(*args: str, timeout: int = 120, allowed_failure: bool = False):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode and not allowed_failure:
        pytest.fail("isolated PostgreSQL 16 command failed")
    return result


def wait_ready(container: str, *, expected: bool = True) -> bool:
    if not expected:
        for _ in range(50):
            if run("exec", container, "pg_isready", "-U", "postgres", allowed_failure=True).returncode == 0:
                return False
            time.sleep(0.1)
        return True
    for _ in range(100):
        ready = run("exec", container, "pg_isready", "-U", "postgres", allowed_failure=True).returncode == 0
        if ready:
            return True
        time.sleep(0.1)
    return False


def cleanup() -> None:
    for container in (SOURCE, RESTORE, BROKEN):
        run("rm", "-f", container, allowed_failure=True)
    for volume in (DATA, BASE, ARCHIVE, RESTORE_DATA, BROKEN_DATA):
        run("volume", "rm", "-f", volume, allowed_failure=True)


def prepare_restore(target_volume: str) -> None:
    command = (
        "cp -a /base/backup/. /target/ && touch /target/recovery.signal && "
        "printf '%s\\n' \"restore_command = 'cp /archive/%f %p'\" "
        "\"recovery_target_name = 'wal_retry_target'\" "
        "\"recovery_target_action = 'promote'\" >> /target/postgresql.auto.conf && "
        "chown -R postgres:postgres /target"
    )
    run("run", "--rm", "-u", "root", "-v", f"{BASE}:/base:ro", "-v", f"{ARCHIVE}:/archive:ro",
        "-v", f"{target_volume}:/target", "postgres:16", "sh", "-c", command)


def test_transient_failure_retry_continuous_restore_and_missing_wal_detection() -> None:
    if os.environ.get("PAPER_WAL_REMEDIATION_REHEARSAL") != "1":
        pytest.skip("explicit isolated WAL remediation rehearsal authorization required")
    cleanup()
    try:
        for volume in (DATA, BASE, ARCHIVE, RESTORE_DATA, BROKEN_DATA):
            run("volume", "create", volume)
        archive_command = (
            "if [ ! -f /archive/.failed_once ]; then touch /archive/.failed_once; exit 1; fi; "
            "if [ -f /archive/%f ]; then cmp -s %p /archive/%f; else cp %p /archive/%f; fi"
        )
        run("run", "-d", "--name", SOURCE, "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
            "-v", f"{DATA}:/var/lib/postgresql/data", "-v", f"{BASE}:/base",
            "-v", f"{ARCHIVE}:/archive", "postgres:16", "postgres", "-c", "archive_mode=on",
            "-c", "wal_level=replica", "-c", f"archive_command={archive_command}")
        assert wait_ready(SOURCE)
        run("exec", SOURCE, "psql", "-U", "postgres", "-d", "postgres", "-c",
            "CREATE TABLE wal_retry_markers(marker text PRIMARY KEY); INSERT INTO wal_retry_markers VALUES ('A');")
        run("exec", "-u", "root", SOURCE, "sh", "-c", "mkdir -p /base/backup && chown -R postgres:postgres /base /archive")
        run("exec", SOURCE, "pg_basebackup", "-U", "postgres", "-D", "/base/backup", "-Fp", "-Xs", "-c", "fast")
        run("exec", SOURCE, "psql", "-U", "postgres", "-d", "postgres", "-AtX", "-c", "SELECT pg_create_restore_point('wal_retry_target')")
        run("exec", SOURCE, "psql", "-U", "postgres", "-d", "postgres", "-c", "INSERT INTO wal_retry_markers VALUES ('B')")
        run("exec", SOURCE, "psql", "-U", "postgres", "-d", "postgres", "-AtX", "-c", "SELECT pg_switch_wal()")
        last_archived = ""
        for _ in range(120):
            record = run("exec", SOURCE, "psql", "-U", "postgres", "-d", "postgres", "-AtX", "-F", "|", "-c",
                         "SELECT archived_count,failed_count,COALESCE(last_archived_wal,'') FROM pg_stat_archiver").stdout.strip()
            fields = record.split("|")
            if len(fields) == 3 and int(fields[0]) >= 1 and int(fields[1]) >= 1 and len(fields[2]) == 24:
                last_archived = fields[2]
                break
            time.sleep(0.25)
        assert last_archived
        run("rm", "-f", SOURCE)
        run("volume", "rm", "-f", DATA)

        prepare_restore(RESTORE_DATA)
        run("run", "-d", "--name", RESTORE, "-v", f"{RESTORE_DATA}:/var/lib/postgresql/data",
            "-v", f"{ARCHIVE}:/archive:ro", "postgres:16")
        assert wait_ready(RESTORE)
        markers = run("exec", RESTORE, "psql", "-U", "postgres", "-d", "postgres", "-AtX", "-c",
                      "SELECT string_agg(marker,',' ORDER BY marker) FROM wal_retry_markers").stdout.strip()
        assert markers == "A"
        run("rm", "-f", RESTORE)

        run("run", "--rm", "-u", "root", "-v", f"{ARCHIVE}:/archive", "postgres:16",
            "sh", "-c", "rm -f /archive/\"$1\"", "remove-one-required-segment", last_archived)
        prepare_restore(BROKEN_DATA)
        run("run", "-d", "--name", BROKEN, "-v", f"{BROKEN_DATA}:/var/lib/postgresql/data",
            "-v", f"{ARCHIVE}:/archive:ro", "postgres:16")
        assert wait_ready(BROKEN, expected=False)
    finally:
        cleanup()
