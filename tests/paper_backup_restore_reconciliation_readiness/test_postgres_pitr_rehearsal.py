from __future__ import annotations

import os
import subprocess
import time

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.config.settings import get_settings
from app.engine_paper.reconciliation import (
    EXPECTED_SCHEMA_HEAD,
    PaperReadOnlyReconciliationService,
    PaperReconciliationOutcome,
    PaperReconciliationRequest,
    PaperReconciliationScope,
    SqlAlchemyPaperReconciliationReader,
)


pytestmark = pytest.mark.postgres
SOURCE = "traders-ml-paper-pitr-source-01"
RESTORE = "traders-ml-paper-pitr-restore-01"
SOURCE_VOLUME = "traders_ml_paper_pitr_source_01"
BASE_VOLUME = "traders_ml_paper_pitr_base_01"
ARCHIVE_VOLUME = "traders_ml_paper_pitr_archive_01"
RESTORE_VOLUME = "traders_ml_paper_pitr_restore_01"
PORT = "55440"
USER = "paper_pitr_task"
DATABASE = "paper_test_pitr_01"


def _run(*arguments: str, timeout=120, allow_failure=False):
    completed = subprocess.run(
        ["docker", *arguments], capture_output=True, text=True, timeout=timeout
    )
    if completed.returncode and not allow_failure:
        pytest.fail(f"isolated PITR docker operation failed: {arguments[0]}")
    return completed


def _wait_ready(container: str):
    consecutive = 0
    for _ in range(60):
        if _run("exec", container, "pg_isready", "-U", USER, "-d", DATABASE, allow_failure=True).returncode == 0:
            consecutive += 1
            if consecutive == 3:
                return
        else:
            consecutive = 0
        time.sleep(0.25)
    pytest.fail("isolated PITR PostgreSQL did not become ready")


def _url():
    return f"postgresql+psycopg://{USER}@127.0.0.1:{PORT}/{DATABASE}"


def _migrate(revision: str):
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = _url()
    get_settings.cache_clear()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", _url().replace("%", "%%"))
    try:
        command.upgrade(config, revision)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def _reconcile():
    engine = create_engine(_url(), hide_parameters=True)
    factory = sessionmaker(bind=engine)
    result = PaperReadOnlyReconciliationService(
        lambda _request: SqlAlchemyPaperReconciliationReader(factory())
    ).reconcile(
        PaperReconciliationRequest(
            request_id="pitr-rehearsal-request",
            correlation_id="pitr-rehearsal-correlation",
            target_class="ISOLATED_POSTGRESQL_0012",
            target_identity="task-pitr-restore",
            expected_schema_head=EXPECTED_SCHEMA_HEAD,
            scope=PaperReconciliationScope(full_isolated_fixture=True),
        )
    )
    engine.dispose()
    return result


def _cleanup():
    for container in (SOURCE, RESTORE):
        _run("rm", "-f", container, allow_failure=True)
    for volume in (SOURCE_VOLUME, BASE_VOLUME, ARCHIVE_VOLUME, RESTORE_VOLUME):
        _run("volume", "rm", "-f", volume, allow_failure=True)


def test_physical_base_backup_wal_target_recovery_and_reconciliation():
    if os.environ.get("PAPER_PITR_REHEARSAL") != "1":
        pytest.skip("explicit task-owned PITR rehearsal authorization required")
    _cleanup()
    try:
        for volume in (SOURCE_VOLUME, BASE_VOLUME, ARCHIVE_VOLUME, RESTORE_VOLUME):
            _run("volume", "create", volume)
        _run(
            "run", "-d", "--name", SOURCE,
            "-e", "POSTGRES_HOST_AUTH_METHOD=trust", "-e", f"POSTGRES_USER={USER}",
            "-e", f"POSTGRES_DB={DATABASE}",
            "-p", f"127.0.0.1:{PORT}:5432",
            "-v", f"{SOURCE_VOLUME}:/var/lib/postgresql/data",
            "-v", f"{BASE_VOLUME}:/base", "-v", f"{ARCHIVE_VOLUME}:/archive",
            "postgres:16", "postgres", "-c", "archive_mode=on", "-c", "wal_level=replica",
            "-c", "archive_command=test ! -f /archive/%f && cp %p /archive/%f",
        )
        _wait_ready(SOURCE)
        _migrate("0008_engine_orchestrator_freshness_retry")
        schema_gate = _reconcile()
        assert schema_gate.outcome is PaperReconciliationOutcome.PAPER_SCHEMA_NOT_DEPLOYED
        assert schema_gate.paper_table_queries == 0
        assert schema_gate.business_mutations == schema_gate.schema_mutations == 0
        _migrate(EXPECTED_SCHEMA_HEAD)
        engine = create_engine(_url(), hide_parameters=True)
        with engine.begin() as connection:
            assert connection.execute(text("SHOW server_version_num")).scalar_one().startswith("16")
            assert connection.execute(text("SHOW archive_mode")).scalar_one() == "on"
            connection.execute(text("CREATE TABLE task_pitr_markers (marker text PRIMARY KEY)"))
            connection.execute(text("INSERT INTO task_pitr_markers(marker) VALUES ('A')"))
        engine.dispose()

        _run("exec", "-u", "root", SOURCE, "bash", "-c", "mkdir -p /base/backup && chown -R postgres:postgres /base /archive")
        _run("exec", SOURCE, "pg_basebackup", "-U", USER, "-D", "/base/backup", "-Fp", "-Xs", "-c", "fast")
        _run("exec", SOURCE, "psql", "-U", USER, "-d", DATABASE, "-c", "SELECT pg_create_restore_point('paper_recovery_target_01')")
        _run("exec", SOURCE, "psql", "-U", USER, "-d", DATABASE, "-c", "INSERT INTO task_pitr_markers(marker) VALUES ('B')")
        _run("exec", SOURCE, "psql", "-U", USER, "-d", DATABASE, "-c", "SELECT pg_switch_wal()")
        for _ in range(40):
            archived = _run("exec", SOURCE, "bash", "-c", "test $(find /archive -type f | wc -l) -gt 0", allow_failure=True)
            if archived.returncode == 0:
                break
            time.sleep(0.25)
        else:
            pytest.fail("task-owned WAL archive remained empty")

        metrics_engine = create_engine(_url(), hide_parameters=True)
        with metrics_engine.connect() as connection:
            connections = connection.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid()" )).scalar_one()
            idle = connection.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND state = 'idle in transaction'" )).scalar_one()
            waits = connection.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'" )).scalar_one()
        metrics_engine.dispose()
        assert (connections, idle, waits) == (0, 0, 0)
        _run("rm", "-f", SOURCE)
        _run("volume", "rm", "-f", SOURCE_VOLUME)

        configuration = (
            "cp -a /base/backup/. /restore/ && "
            "touch /restore/recovery.signal && "
            "printf '%s\\n' \"restore_command = 'cp /archive/%f %p'\" "
            "\"recovery_target_name = 'paper_recovery_target_01'\" "
            "\"recovery_target_action = 'promote'\" >> /restore/postgresql.auto.conf && "
            "chown -R postgres:postgres /restore"
        )
        _run(
            "run", "--rm", "-u", "root",
            "-v", f"{BASE_VOLUME}:/base:ro", "-v", f"{RESTORE_VOLUME}:/restore",
            "-v", f"{ARCHIVE_VOLUME}:/archive:ro", "postgres:16", "bash", "-c", configuration,
        )
        _run(
            "run", "-d", "--name", RESTORE, "-p", f"127.0.0.1:{PORT}:5432",
            "-v", f"{RESTORE_VOLUME}:/var/lib/postgresql/data",
            "-v", f"{ARCHIVE_VOLUME}:/archive:ro", "postgres:16",
        )
        _wait_ready(RESTORE)
        engine = create_engine(_url(), hide_parameters=True)
        with engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            markers = tuple(connection.execute(text("SELECT marker FROM task_pitr_markers ORDER BY marker")).scalars())
            recovering = connection.execute(text("SELECT pg_is_in_recovery()" )).scalar_one()
        engine.dispose()
        assert revision == EXPECTED_SCHEMA_HEAD
        assert markers == ("A",)
        assert recovering is False
        reconciliation = _reconcile()
        assert reconciliation.outcome is PaperReconciliationOutcome.HEALTHY
        assert reconciliation.paper_table_queries == 8
        print(
            "PITR_PROVEN_ISOLATED target_accurate=YES pre_target_A=YES "
            "post_target_B_absent=YES schema_head=0011 reconciliation=HEALTHY"
        )
    finally:
        _cleanup()
