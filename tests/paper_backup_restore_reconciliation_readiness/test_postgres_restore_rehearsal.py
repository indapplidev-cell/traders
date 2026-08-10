from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.engine_paper.reconciliation import (
    EXPECTED_SCHEMA_HEAD,
    PAPER_TABLES,
    PaperReadOnlyReconciliationService,
    PaperReconciliationOutcome,
    PaperReconciliationRequest,
    PaperReconciliationScope,
    SqlAlchemyPaperReconciliationReader,
)
from app.engine_paper.recovery_readiness import (
    PaperProductionBackupArtifactManifest,
    PaperProductionBackupArtifactType,
    PaperProductionBackupClass,
    PaperProductionIntegrityResult,
)
from app.engine_paper.controlled_worker import SqlAlchemyPaperLifecycleGraphLoader
from app.engine_paper.unit_of_work import PaperUnitOfWork


pytestmark = pytest.mark.postgres


def _configuration():
    raw = os.environ.get("PAPER_TEST_DATABASE_URL")
    container = os.environ.get("PAPER_RECOVERY_CONTAINER")
    if not raw or not container:
        pytest.skip("task-owned recovery PostgreSQL is not configured")
    url = make_url(raw)
    if url.host not in {"127.0.0.1", "localhost", "::1"} or not (url.database or "").startswith("paper_test_"):
        pytest.fail("isolated loopback paper_test_ target required")
    if not container.startswith("traders-ml-paper-recovery-"):
        pytest.fail("task-owned recovery container identity required")
    return raw, container


def _docker(*arguments: str) -> None:
    completed = subprocess.run(
        ["docker", *arguments], check=False, capture_output=True, text=True, timeout=120
    )
    if completed.returncode:
        pytest.fail(f"isolated docker operation failed: {arguments[0]}")


def _request(identity: str):
    return PaperReconciliationRequest(
        request_id="restore-rehearsal-request",
        correlation_id="restore-rehearsal-correlation",
        target_class="ISOLATED_POSTGRESQL_0011",
        target_identity=identity,
        expected_schema_head=EXPECTED_SCHEMA_HEAD,
        scope=PaperReconciliationScope(full_isolated_fixture=True),
    )


def _reconcile(url: str, identity: str):
    engine = create_engine(url, hide_parameters=True)
    factory = sessionmaker(bind=engine)
    service = PaperReadOnlyReconciliationService(
        lambda _request: SqlAlchemyPaperReconciliationReader(factory())
    )
    result = service.reconcile(_request(identity))
    engine.dispose()
    return result


def _normalized(value):
    if isinstance(value, (datetime, Decimal)):
        return str(value)
    return value


def _material_manifest(url: str):
    engine = create_engine(url, hide_parameters=True)
    result = {}
    with engine.connect() as connection:
        for table in PAPER_TABLES:
            primary = {
                "paper_execution_commands": "command_id", "paper_orders": "order_id",
                "paper_fills": "fill_id", "paper_positions": "position_id",
                "paper_exit_evaluation_cursors": "cursor_id",
                "paper_exit_decisions": "exit_decision_id",
                "paper_order_events": "order_event_id",
                "paper_journal_entries": "journal_entry_id",
            }[table]
            rows = connection.execute(text(f"SELECT * FROM {table} ORDER BY {primary}"))
            result[table] = [
                {key: _normalized(value) for key, value in row.items()}
                for row in rows.mappings()
            ]
    engine.dispose()
    return result


def _structural_manifest(url: str):
    engine = create_engine(url, hide_parameters=True)
    inspector = inspect(engine)
    result = {
        table: tuple((column["name"], str(column["type"]), column["nullable"]) for column in inspector.get_columns(table))
        for table in PAPER_TABLES
    }
    engine.dispose()
    return result


def test_logical_backup_destructive_loss_restore_and_reconciliation():
    source_url, container = _configuration()
    source = make_url(source_url)
    source_db = source.database
    restore_db = f"{source_db}_restore"
    fixture_engine = create_engine(source_url, hide_parameters=True)
    now_ms = (int(time.time() * 1000) // 60_000) * 60_000
    with fixture_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE paper_exit_evaluation_cursors "
                "SET position_opened_closed_until_ms = :opened, "
                "last_evaluated_closed_until_ms = :evaluated, "
                "last_advance_from_closed_until_ms = :opened, "
                "last_advance_to_closed_until_ms = :evaluated"
            ),
            {"opened": now_ms - 120_000, "evaluated": now_ms - 60_000},
        )
    fixture_engine.dispose()
    healthy_before = _reconcile(source_url, "task-source")
    assert healthy_before.outcome is PaperReconciliationOutcome.HEALTHY, [
        finding.code for finding in healthy_before.findings
    ]
    material_before = _material_manifest(source_url)
    structure_before = _structural_manifest(source_url)
    assert tuple(len(material_before[table]) for table in PAPER_TABLES) == (1, 2, 2, 1, 1, 1, 8, 12)

    with tempfile.TemporaryDirectory(prefix="paper-recovery-rehearsal-") as workspace:
        artifact = Path(workspace) / "logical-backup.dump"
        started = time.perf_counter_ns()
        _docker("exec", container, "pg_dump", "-U", source.username, "-d", source_db, "-Fc", "-f", "/tmp/paper-logical-backup.dump")
        _docker("cp", f"{container}:/tmp/paper-logical-backup.dump", str(artifact))
        backup_ms = (time.perf_counter_ns() - started) // 1_000_000
        payload = artifact.read_bytes()
        manifest = PaperProductionBackupArtifactManifest(
            artifact_type=PaperProductionBackupArtifactType.LOGICAL_CUSTOM,
            created_at=datetime.now(timezone.utc), source_schema_head=EXPECTED_SCHEMA_HEAD,
            postgresql_major=16, backup_class=PaperProductionBackupClass.LOGICAL,
            size_bytes=len(payload), checksum_sha256=hashlib.sha256(payload).hexdigest(),
            integrity_result=PaperProductionIntegrityResult.VERIFIED,
            tool_version="pg_dump-16", rehearsal_id="logical-restore-1",
            retention_class="task-ephemeral",
        )
        assert manifest.verify_bytes(payload) == "VERIFIED"

        admin_url = source.set(database="postgres")
        admin = create_engine(admin_url, isolation_level="AUTOCOMMIT", hide_parameters=True)
        with admin.connect() as connection:
            connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": source_db})
            connection.execute(text(f'DROP DATABASE "{source_db}"'))
            connection.execute(text(f'CREATE DATABASE "{restore_db}"'))
        admin.dispose()
        started = time.perf_counter_ns()
        _docker("exec", container, "pg_restore", "-U", source.username, "-d", restore_db, "--exit-on-error", "/tmp/paper-logical-backup.dump")
        restore_ms = (time.perf_counter_ns() - started) // 1_000_000
        restored_url = source.set(database=restore_db).render_as_string(
            hide_password=False
        )

        restored_engine = create_engine(restored_url, hide_parameters=True)
        with restored_engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == EXPECTED_SCHEMA_HEAD
        restored_engine.dispose()
        assert _structural_manifest(restored_url) == structure_before
        assert _material_manifest(restored_url) == material_before
        restored_result = _reconcile(restored_url, "task-restore")
        assert restored_result.outcome is PaperReconciliationOutcome.HEALTHY

        repository_engine = create_engine(restored_url, hide_parameters=True)
        factory = sessionmaker(bind=repository_engine)
        with repository_engine.connect() as connection:
            command_id = connection.execute(text("SELECT command_id FROM paper_execution_commands")).scalar_one()
        graph = SqlAlchemyPaperLifecycleGraphLoader(lambda: PaperUnitOfWork(factory)).load(command_id)
        assert graph.positions[0].state.value == "CLOSED"
        repository_engine.dispose()

        mutation_engine = create_engine(restored_url, hide_parameters=True)
        with mutation_engine.begin() as connection:
            terminal_id = connection.execute(
                text(
                    "SELECT journal_entry_id FROM paper_journal_entries "
                    "WHERE event_type = 'PAPER_POSITION_CLOSED'"
                )
            ).scalar_one()
            connection.execute(
                text(
                    "UPDATE paper_journal_entries "
                    "SET event_type = 'PAPER_EXIT_TRIGGERED' "
                    "WHERE journal_entry_id = :terminal_id"
                ),
                {"terminal_id": terminal_id},
            )
        assert _reconcile(restored_url, "task-restore-inconsistent").outcome is PaperReconciliationOutcome.INCONSISTENT
        with mutation_engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE paper_journal_entries "
                    "SET event_type = 'PAPER_POSITION_CLOSED' "
                    "WHERE journal_entry_id = :terminal_id"
                ),
                {"terminal_id": terminal_id},
            )
        mutation_engine.dispose()
        assert _reconcile(restored_url, "task-restore-repaired-fixture").outcome is PaperReconciliationOutcome.HEALTHY
        _docker("exec", container, "rm", "-f", "/tmp/paper-logical-backup.dump")
        assert not artifact.exists() or artifact.stat().st_size > 0
        print(json.dumps({
            "logical_backup_duration_ms": backup_ms,
            "logical_restore_duration_ms": restore_ms,
            "logical_backup_bytes": len(payload),
            "logical_backup_sha256": manifest.checksum_sha256,
            "restored_counts": [len(material_before[table]) for table in PAPER_TABLES],
            "restored_reconciliation": "HEALTHY",
            "material_graph_exact": True,
        }, sort_keys=True))
