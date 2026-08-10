from __future__ import annotations

import subprocess

import pytest

from scripts.security_retry_controls import (
    ArchiveTimeoutClass,
    DataPersistenceClass,
    WalLevelClass,
    command_is_forbidden,
    inspect_postgres_recovery_metadata,
    parse_safe_postgres_recovery_metadata,
)


@pytest.mark.parametrize("persistence,expected", (
    ("volume", DataPersistenceClass.PERSISTENT_EXTERNAL_VOLUME),
    ("bind", DataPersistenceClass.PERSISTENT_HOST_BIND),
    ("tmpfs", DataPersistenceClass.EPHEMERAL_CONTAINER_STORAGE),
    ("none", DataPersistenceClass.EPHEMERAL_CONTAINER_STORAGE),
))
def test_safe_metadata_parser_classifies_storage(persistence, expected) -> None:
    result = parse_safe_postgres_recovery_metadata(
        "16|off|replica|0|0|0", persistence, "present"
    )
    assert result is not None
    assert result.postgres_major == 16
    assert result.data_persistence_class is expected
    assert result.wal_level_class is WalLevelClass.REPLICA_OR_HIGHER
    assert result.archive_timeout_class is ArchiveTimeoutClass.DISABLED


@pytest.mark.parametrize("fake_secret", (
    "-".join(("fake", "password", "one")),
    "".join(("postgresql", "://", "fake", ":", "value", "@example/db")),
    "=".join(("DATABASE_URL", "fake-value")),
    "=".join(("TRADERS_ML_POSTGRES_PASSWORD", "fake-value")),
))
def test_inspector_never_renders_fake_secret_from_stderr(fake_secret: str) -> None:
    calls = []

    def runner(command, **_kwargs):
        calls.append(tuple(command))
        if "psql" in command:
            return subprocess.CompletedProcess(command, 0, "16|off|replica|0|0|0", fake_secret)
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "postgres (PostgreSQL) 16.10", fake_secret)
        if "inspect" in command:
            return subprocess.CompletedProcess(command, 0, "volume", fake_secret)
        return subprocess.CompletedProcess(command, 0, "present", fake_secret)

    result = inspect_postgres_recovery_metadata("safe-container", runner=runner)
    rendered = result.render()
    assert fake_secret not in rendered
    assert "archive_command_configured_boolean=NO" in rendered
    assert all(not command_is_forbidden(command) for command in calls)
    assert all(".Config.Env" not in command and ".ContainerConfig.Env" not in command for command in calls)


@pytest.mark.parametrize("record", (
    "", "16|off|replica|0|0", "16|off|unsafe|0|0|0",
    "16|off|replica|2|0|0", "16|off|replica|0|0|0|fake-secret",
))
def test_safe_metadata_parser_rejects_unexpected_shape(record: str) -> None:
    assert parse_safe_postgres_recovery_metadata(record, "volume", "present") is None


def test_inspector_setting_failure_keeps_safe_proven_metadata_only() -> None:
    def runner(command, **_kwargs):
        if "psql" in command:
            return subprocess.CompletedProcess(command, 2, "", "fake-secret")
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "postgres (PostgreSQL) 16.10", "")
        if "inspect" in command:
            return subprocess.CompletedProcess(command, 0, "volume", "")
        return subprocess.CompletedProcess(command, 0, "present", "")

    result = inspect_postgres_recovery_metadata("safe-container", runner=runner)
    assert result.postgres_major == 16
    assert result.data_persistence_class is DataPersistenceClass.PERSISTENT_EXTERNAL_VOLUME
    assert result.archive_mode_enabled is None
    assert "fake-secret" not in result.render()
