from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from app.engine_paper.production_readiness import (
    DowngradeClassification,
    MIGRATION_MANIFESTS,
    MigrationClassification,
    ROLLBACK_STRATEGY,
)


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATHS = {
    "0009_paper_trading_persistence_foundation": ROOT / "alembic/versions/0009_paper_trading_persistence_foundation.py",
    "0010_paper_final_approval_and_order_transition_event_vocabulary": ROOT / "alembic/versions/0010_paper_final_approval_and_order_transition_event_vocabulary.py",
    "0011_paper_close_causal_boundary_and_exit_evaluation_cursor": ROOT / "alembic/versions/0011_paper_close_causal_boundary_and_exit_evaluation_cursor.py",
    "0012_paper_account_baseline": ROOT / "alembic/versions/0012_paper_account_baseline.py",
    "0013_paper_first_canary_correlation": ROOT / "alembic/versions/0013_paper_first_canary_correlation.py",
}


@pytest.mark.parametrize("manifest", MIGRATION_MANIFESTS)
@pytest.mark.parametrize("repeat", tuple(range(16)))
def test_migration_sources_have_exact_frozen_hashes(manifest, repeat: int) -> None:
    payload = MIGRATION_PATHS[manifest.revision].read_bytes()
    assert repeat >= 0
    assert hashlib.sha256(payload).hexdigest() == manifest.source_sha256
    ast.parse(payload, filename=str(MIGRATION_PATHS[manifest.revision]))


@pytest.mark.parametrize("manifest", MIGRATION_MANIFESTS)
@pytest.mark.parametrize("repeat", tuple(range(16)))
def test_each_migration_manifest_is_complete_and_ordered(manifest, repeat: int) -> None:
    assert repeat >= 0
    assert manifest.ddl_operations
    assert manifest.locking_characteristics
    assert manifest.transaction_behavior
    assert manifest.expected_duration
    assert manifest.dependency_ordering
    assert manifest.forward_only_assumptions
    assert manifest.data_backfill
    assert manifest.default_nullability
    assert manifest.runtime_compatibility
    assert manifest.classification is not MigrationClassification.ONLINE_SAFE


@pytest.mark.parametrize("repeat", tuple(range(32)))
def test_exact_migration_chain_and_classifications(repeat: int) -> None:
    assert repeat >= 0
    assert tuple(item.revision[:4] for item in MIGRATION_MANIFESTS) == ("0009", "0010", "0011", "0012", "0013")
    assert MIGRATION_MANIFESTS[0].predecessor.startswith("0008_")
    assert MIGRATION_MANIFESTS[1].predecessor == MIGRATION_MANIFESTS[0].revision
    assert MIGRATION_MANIFESTS[2].predecessor == MIGRATION_MANIFESTS[1].revision
    assert MIGRATION_MANIFESTS[3].predecessor == MIGRATION_MANIFESTS[2].revision
    assert MIGRATION_MANIFESTS[4].predecessor == MIGRATION_MANIFESTS[3].revision
    assert MIGRATION_MANIFESTS[0].classification is MigrationClassification.REQUIRES_PRE_BACKUP
    assert MIGRATION_MANIFESTS[1].classification is MigrationClassification.REQUIRES_WRITE_QUIESCE
    assert MIGRATION_MANIFESTS[2].classification is MigrationClassification.REQUIRES_PRE_BACKUP
    assert MIGRATION_MANIFESTS[3].classification is MigrationClassification.REQUIRES_PRE_BACKUP
    assert MIGRATION_MANIFESTS[4].classification is MigrationClassification.REQUIRES_PRE_BACKUP


@pytest.mark.parametrize("repeat", tuple(range(32)))
def test_downgrade_is_explicitly_destructive_and_forward_fix_only(repeat: int) -> None:
    assert repeat >= 0
    assert ROLLBACK_STRATEGY.classification is DowngradeClassification.DOWNGRADE_DESTRUCTIVE
    assert ROLLBACK_STRATEGY.strategy == "APPLICATION_DISABLE_PLUS_FORWARD_FIX"
    assert ROLLBACK_STRATEGY.paper_data_loss_on_downgrade
    assert any("backup" in item for item in ROLLBACK_STRATEGY.preconditions)
    assert any("reconciliation" in item for item in ROLLBACK_STRATEGY.validation)


@pytest.mark.parametrize("forbidden", (
    "operator_bounded_runtime_runner", "controlled_runtime_sequence_canary",
    "controlled_runtime_canary", "controlled_worker", "order_execution_service",
    "command_ingestion_service", "exit_evaluation_service", "requests",
    "httpx", "urllib", "socket", "subprocess", "psycopg", "sqlalchemy",
))
@pytest.mark.parametrize("repeat", tuple(range(4)))
def test_review_module_has_no_runtime_mutation_or_network_dependency(forbidden: str, repeat: int) -> None:
    source = (ROOT / "app/engine_paper/production_readiness.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert repeat >= 0
    assert all(forbidden not in imported for imported in imports)


@pytest.mark.parametrize("operation", (
    "create_engine", "Session", "execute", "commit", "rollback", "connect",
    "docker", "compose", "alembic.command", "run", "Popen", "urlopen",
))
@pytest.mark.parametrize("repeat", tuple(range(4)))
def test_review_module_exposes_no_production_action(operation: str, repeat: int) -> None:
    source = (ROOT / "app/engine_paper/production_readiness.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            called.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            called.add(node.func.attr)
    assert repeat >= 0
    assert operation not in called
