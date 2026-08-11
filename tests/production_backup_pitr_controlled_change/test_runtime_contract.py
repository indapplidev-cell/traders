from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import production_backup
from scripts.security_retry_controls import (
    inspect_postgres_capacity_metadata,
    inspect_postgres_recovery_metadata,
)


@pytest.mark.parametrize("fake_secret", (
    "fake-password-value",
    "postgresql:" + "//fake:value@example/db",
    "DATABASE_URL=fake-value",
    "TRADERS_ML_POSTGRES_PASSWORD=fake-value",
))
def test_safe_inspectors_never_echo_fake_secret(fake_secret: str) -> None:
    def runner(command, **_kwargs):
        if "pg_database_size" in " ".join(command):
            return subprocess.CompletedProcess(command, 0, "123456\n", fake_secret)
        if "current_setting" in " ".join(command):
            return subprocess.CompletedProcess(command, 0, "16|on|replica|1|0|900\n", fake_secret)
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, "postgres (PostgreSQL) 16.10\n", fake_secret)
        if "inspect" in command:
            return subprocess.CompletedProcess(command, 0, "volume\n", fake_secret)
        return subprocess.CompletedProcess(command, 0, "present\n", fake_secret)
    capacity = inspect_postgres_capacity_metadata("safe-container", runner=runner).render()
    recovery = inspect_postgres_recovery_metadata("safe-container", runner=runner).render()
    assert fake_secret not in capacity
    assert fake_secret not in recovery


def test_execution_adapter_contains_no_protected_binding_or_uri() -> None:
    source = Path(production_backup.__file__).read_text(encoding="utf-8")
    assert ".env.production.local" not in source
    assert "docker compose config" not in source
    assert "docker inspect" not in source
    assert "printenv" not in source
    assert "docker exec env" not in source
    assert "password" not in source.casefold()
    assert "postgresql://" not in source


def test_compose_pitr_contract_is_no_secret_and_targeted() -> None:
    text = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "archive_mode=on" in text
    assert "wal_level=replica" in text
    assert "archive_timeout=900" in text
    assert "D:/traders_ml_recovery/postgres:/var/lib/postgresql/recovery" in text
    assert "cmp -s" in text
    assert ".ack" in text
    assert "300" in text
    assert "in_progress" in Path(production_backup.__file__).read_text(encoding="utf-8")


def test_production_backup_commands_use_local_socket_identity() -> None:
    source = Path(production_backup.__file__).read_text(encoding="utf-8")
    assert '"-U", DB_USER' in source
    assert '"-d", DB_NAME' in source
    assert "pg_dump" in source and "pg_basebackup" in source and "pg_verifybackup" in source
    assert "DATABASE_URL" not in source


def test_no_foundation_semantic_files_changed() -> None:
    prohibited = (
        "0009_paper_foundation.py", "0010_paper", "0011_paper",
        "controlled_runtime.py", "controlled_worker.py",
    )
    result = subprocess.run(["git", "diff", "--name-only", "3e4ec00ee2a6f7a24dceb93f00f14a8890e0fd34"], capture_output=True, text=True, check=True)
    assert not any(marker in result.stdout for marker in prohibited)
