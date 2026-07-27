from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
from pydantic import ValidationError

from app.config.settings import Settings, get_settings
from scripts.market_data_image_contract import scan_tree


ROOT = Path(__file__).resolve().parents[1]


def _runtime_secret() -> str:
    password = os.urandom(18).hex()
    return "postgresql+psycopg" + ":" + "//runtime:" + password + "@db.invalid/runtime"


def test_production_requires_external_database_url() -> None:
    with pytest.raises(ValidationError) as error:
        Settings(app_env="production")
    assert "DATABASE_URL is required in production" in str(error.value)


def test_injected_database_url_is_not_rendered_or_serialized() -> None:
    secret = _runtime_secret()
    settings = Settings(app_env="production", database_url=secret)
    assert settings.require_database_url() == secret
    assert secret not in repr(settings)
    assert secret not in str(settings)
    assert secret not in settings.model_dump_json()
    assert "database_url" not in settings.model_dump()


def test_missing_secret_error_does_not_contain_injected_value() -> None:
    secret = _runtime_secret()
    with pytest.raises(ValidationError) as error:
        Settings(app_env="production", database_url=None, service_name=secret)
    assert secret not in str(error.value)


def test_get_settings_has_no_database_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        assert get_settings().database_url is None
    finally:
        get_settings.cache_clear()


def test_tracked_source_has_no_credential_bearing_literals() -> None:
    findings = scan_tree(ROOT)
    assert findings == []


def test_dockerignore_excludes_credentials_and_virtual_environments() -> None:
    patterns = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert {
        ".env",
        ".env.*",
        "*.pem",
        "*.key",
        "secrets/",
        "credentials/",
        ".venv/",
        "venv/",
        "env/",
        ".git/",
    }.issubset(patterns)


def test_git_tracked_context_has_no_credential_files_or_venvs() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8").split("\0")
    credential_names = {".env", "id_rsa", "id_ed25519"}
    assert not [
        path
        for path in tracked
        if path
        and (
            Path(path).name in credential_names
            or Path(path).suffix.lower() in {".key", ".pem"}
        )
    ]
    assert not [
        path
        for path in tracked
        if any(part in {".venv", "venv", "env", ".virtualenv"} for part in Path(path).parts)
    ]
