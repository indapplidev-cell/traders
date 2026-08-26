from __future__ import annotations

import json
import subprocess

import pytest

from scripts.safe_docker_inspection import (
    SafeDockerInspectionError,
    redact_diagnostic,
    redact_uri,
    safe_inspect_container,
)


SENTINEL = "SENTINEL_FAKE_SECRET_DO_NOT_LEAK"


def _runner(document: dict, *, stderr: str = ""):
    def run(command, **_kwargs):
        return subprocess.CompletedProcess(command, 0, json.dumps([document]), stderr)

    return run


def _document() -> dict:
    return {
        "Id": "container-id",
        "Image": "sha256:image-id",
        "RestartCount": 2,
        "State": {"Status": "running", "Running": True, "Health": {"Status": "healthy"}},
        "Config": {
            "Env": [
                "PATH=/usr/bin",
                f"DATABASE_URL=postgresql://traders_ml:{SENTINEL}@postgres:5432/traders_ml",
                f"API_TOKEN={SENTINEL}",
            ],
            "Entrypoint": ["/usr/bin/python"],
            "Cmd": ["python", "-m", "app", SENTINEL],
            "Labels": {"org.opencontainers.image.revision": "abcdef123456"},
        },
        "Mounts": [
            {
                "Type": "bind",
                "Source": f"C:/protected/{SENTINEL}/shared-db-password",
                "Destination": "/run/secrets/traders_shared_db_password",
            }
        ],
    }


def test_extended_inspector_emits_allowlisted_metadata_and_no_values() -> None:
    result = safe_inspect_container("traders-ml-online-orchestrator-1", runner=_runner(_document()))
    rendered = result.render()
    assert SENTINEL not in rendered
    assert "postgresql://" not in rendered
    assert "PATH=/usr/bin" not in rendered
    assert "API_TOKEN=" not in rendered
    assert "env_keys_only=API_TOKEN,DATABASE_URL,PATH" in rendered
    assert "db_principals=traders_ml" in rendered
    assert "runtime-secret:traders_shared_db_password" in rendered
    assert "command_identity=python" in rendered


@pytest.mark.parametrize(
    "payload",
    (
        {"password": SENTINEL},
        {"nested": [{"authorization": SENTINEL}]},
        {"message": f"postgresql://role:{SENTINEL}@db/app"},
        {"message": f"password={SENTINEL}"},
        [f"dsn=postgresql://role:{SENTINEL}@db/app"],
    ),
)
def test_structured_redaction_never_leaks_sentinel(payload: object) -> None:
    rendered = json.dumps(redact_diagnostic(payload), sort_keys=True)
    assert SENTINEL not in rendered


def test_uri_redaction_preserves_non_secret_diagnostics() -> None:
    rendered = redact_uri(f"postgresql://role:{SENTINEL}@db.example/app?sslmode=require")
    assert rendered == "postgresql://role:***@db.example/app?sslmode=require"


def test_invalid_json_and_stderr_are_normalized_without_leak() -> None:
    def runner(command, **_kwargs):
        return subprocess.CompletedProcess(command, 0, "not-json", SENTINEL)

    with pytest.raises(SafeDockerInspectionError) as raised:
        safe_inspect_container("container", runner=runner)
    assert SENTINEL not in str(raised.value)


def test_nonzero_exception_does_not_emit_raw_output() -> None:
    def runner(command, **_kwargs):
        return subprocess.CompletedProcess(command, 1, SENTINEL, SENTINEL)

    with pytest.raises(SafeDockerInspectionError) as raised:
        safe_inspect_container("container", runner=runner)
    assert SENTINEL not in str(raised.value)


def test_raw_command_and_environment_values_remain_private_to_module() -> None:
    result = safe_inspect_container("container", runner=_runner(_document()))
    assert not hasattr(result, "environment")
    assert not hasattr(result, "raw_document")
    assert not hasattr(result, "command")


def test_rotation_operational_paths_use_only_safe_docker_reducer() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for relative in (
        "scripts/production_db_credential_rotation.py",
        "scripts/production_db_security_remediation.py",
    ):
        source = (root / relative).read_text(encoding="utf-8")
        assert '["docker", "inspect"' not in source
        assert '["docker", "container", "inspect"' not in source
        assert "safe_inspect_container" in source


def test_multi_principal_report_contract_has_no_secret_fields() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "production_db_security_remediation.py"
    ).read_text(encoding="utf-8")
    assert '"old_passwords"' not in source
    assert '"new_passwords"' not in source
    assert '"credential_hash"' not in source
    assert "SECRET_VALUE_OUTPUT=NO" in source
    assert "SECRET_DERIVED_HASH_CREATED=NO" in source


def test_all_principal_scanner_has_count_only_contract() -> None:
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "scan_all_production_db_secret_exposure.py"
    ).read_text(encoding="utf-8")
    assert "print(secret" not in source
    assert "print(password" not in source
    assert "SECRET_VALUE_OUTPUT=NO" in source
    assert "SECRET_DERIVED_HASH_CREATED=NO" in source
