from __future__ import annotations

import json
from pathlib import Path

from scripts.production_db_credential_rotation import AFFECTED, ClientResult


ROOT = Path(__file__).resolve().parents[1]


def _compose_text() -> str:
    return (ROOT / "docker-compose.yml").read_text(encoding="utf-8")


def test_shared_clients_use_one_protected_password_file_not_config_env() -> None:
    compose = _compose_text()
    assert "DATABASE_URL: ${" not in compose
    for service, _, _ in AFFECTED:
        assert f"  {service}:" in compose
    assert compose.count("      - traders_shared_db_password") == 4
    assert compose.count("/run/secrets/traders_shared_db_password") == 4


def test_postgres_uses_password_file_contract() -> None:
    compose = _compose_text()
    assert "POSTGRES_PASSWORD:" not in compose
    assert "POSTGRES_PASSWORD_FILE: /run/secrets/traders_shared_db_password" in compose


def test_secret_source_is_ignored_host_local_path() -> None:
    compose = _compose_text()
    assert "file: ./.secrets.production.local/shared-db-password" in compose
    assert "/.secrets.production.local/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".secrets.production.local" in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()


def test_safe_client_result_contains_no_credential_field() -> None:
    item = ClientResult(
        service="example",
        container="example-1",
        principal="traders_ml",
        binding_path="protected/path",
        new_binding_loaded=True,
        reconnect=True,
        db_query=True,
        health=True,
        old_credential_rejected=True,
        image_unchanged=True,
        restart_count_before=0,
        restart_count_after=0,
    )
    rendered = json.dumps(item.__dict__, sort_keys=True)
    assert "password" not in rendered.casefold()
    assert "database_url" not in rendered.casefold()


def test_rotation_controller_never_renders_exception_values() -> None:
    source = (ROOT / "scripts" / "production_db_credential_rotation.py").read_text(encoding="utf-8")
    assert "str(error)" not in source
    assert "print(error)" not in source
    assert "SECRET_DERIVED_HASH_CREATED=NO" in source


def test_rotation_controller_uses_probe_connected_state() -> None:
    source = (ROOT / "scripts" / "production_db_credential_rotation.py").read_text(encoding="utf-8")
    assert '"CONNECTED"' in source
    assert '"ACCEPTED"' not in source
