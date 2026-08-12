from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from app.engine_paper.production_preparation import PaperProductionIdentityError
from app.engine_paper.production_preparation_backend import (
    RUNTIME_DATABASE_KEY,
    PaperPreparationAdapterError,
    PaperProductionIdentityConfigurationAdapter,
    ProtectedPaperRuntimeBindingAdapter,
)
from app.engine_paper.production_preparation_cli import build_parser


ROOT = Path(__file__).resolve().parents[2]
SECRET = "isolated-only-secret-value-that-must-never-escape"


def windows_sddl(path: Path) -> str | None:
    if os.name != "nt":
        return None
    completed = subprocess.run([
        "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
        "(Get-Acl -LiteralPath $env:ACL_TEST_PATH).Sddl",
    ], env={"SystemRoot": os.environ["SystemRoot"], "ACL_TEST_PATH": str(path)},
        capture_output=True, text=True, check=True)
    return completed.stdout.strip()


def write_identity(path: Path) -> None:
    path.write_text(json.dumps({
        "PAPER_PRODUCTION_ACCOUNT_ID": "PAPER-ISOLATED-PRIMARY",
        "PAPER_PRODUCTION_ACCOUNTING_SESSION_ID": "PAPER-ISOLATED-LIFECYCLE-01",
        "PAPER_PRODUCTION_CURRENCY": "USDT",
    }), encoding="utf-8")


def test_identity_adapter_is_persistent_restart_stable_and_exact(tmp_path):
    path = tmp_path / "identity.json"
    write_identity(path)
    first = PaperProductionIdentityConfigurationAdapter(path).load()
    second = PaperProductionIdentityConfigurationAdapter(path).load()
    assert first == second
    for content in ("{}", '{"PAPER_PRODUCTION_ACCOUNT_ID":""}',
                    '{"PAPER_PRODUCTION_ACCOUNT_ID":"A","PAPER_PRODUCTION_ACCOUNT_ID":"B"}',
                    json.dumps({"PAPER_PRODUCTION_ACCOUNT_ID": "TEST-FIXTURE",
                                "PAPER_PRODUCTION_ACCOUNTING_SESSION_ID": "VALID-SESSION",
                                "PAPER_PRODUCTION_CURRENCY": "USDT"})):
        path.write_text(content, encoding="utf-8")
        with pytest.raises(PaperProductionIdentityError):
            PaperProductionIdentityConfigurationAdapter(path).load()


def test_protected_adapter_atomic_binding_safe_repr_and_idempotency(tmp_path, monkeypatch):
    binding = tmp_path / ".env.isolated.local"
    binding.write_text("TRADERS_READONLY_API_DATABASE_URL=\nTRADERS_READONLY_API_HOST=127.0.0.1\n"
                       "TRADERS_READONLY_API_PORT=8765\n", encoding="utf-8")
    monkeypatch.setattr("app.engine_paper.production_preparation_backend.secrets.token_urlsafe",
                        lambda _: SECRET)
    adapter = ProtectedPaperRuntimeBindingAdapter(
        binding, "postgresql+psycopg://admin:isolated-admin@127.0.0.1:55432/isolated")
    security_before = windows_sddl(binding)
    installed = []
    result = adapter.ensure(installed.append)
    assert result.changed and installed == [SECRET]
    validation = adapter.metadata()
    rendered = repr(validation) + str(validation.safe_dict()) + repr(result)
    assert validation.binding_valid and SECRET not in rendered and "://" not in rendered
    assert not adapter.ensure(installed.append).changed and installed == [SECRET]
    assert windows_sddl(binding) == security_before
    assert make_url(dict(line.split("=", 1) for line in binding.read_text().splitlines())[
        RUNTIME_DATABASE_KEY]).username == "traders_paper_runtime"


def test_uncertain_binding_result_reuses_staged_credential_without_rotation(tmp_path, monkeypatch):
    binding = tmp_path / ".env.isolated.local"
    binding.write_text("TRADERS_READONLY_API_DATABASE_URL=\nTRADERS_READONLY_API_HOST=127.0.0.1\n"
                       "TRADERS_READONLY_API_PORT=8765\n", encoding="utf-8")
    generated = []
    def factory(_):
        generated.append(SECRET)
        return SECRET
    monkeypatch.setattr("app.engine_paper.production_preparation_backend.secrets.token_urlsafe", factory)
    adapter = ProtectedPaperRuntimeBindingAdapter(
        binding, "postgresql+psycopg://admin:isolated-admin@127.0.0.1:55432/isolated")
    with pytest.raises(PaperPreparationAdapterError) as caught:
        adapter.ensure(lambda _: (_ for _ in ()).throw(RuntimeError("uncertain secret " + SECRET)))
    assert str(caught.value) == "PROTECTED_BINDING_INSTALL_FAILED"
    replayed = []
    assert adapter.ensure(replayed.append).changed
    assert generated == [SECRET] and replayed == [SECRET]
    assert SECRET not in repr(caught.value)


def test_cli_plan_is_real_secret_free_zero_mutation(tmp_path):
    identity = tmp_path / "identity.json"
    write_identity(identity)
    config = tmp_path / "composition.json"
    state = tmp_path / "state"
    config.write_text(json.dumps({
        "deployment_driver": "ISOLATED_FILESYSTEM", "identity_config": str(identity),
        "protected_binding": str(tmp_path / ".env.isolated.local"),
        "state_root": str(state), "target_id": "isolated-production-target",
    }), encoding="utf-8")
    env = dict(os.environ)
    env.pop("TRADERS_PAPER_PREPARATION_ADMIN_DATABASE_URL", None)
    env.pop("TRADERS_PAPER_PREPARATION_TARGET_ID", None)
    completed = subprocess.run(
        [sys.executable, "-m", "app.engine_paper.production_preparation_cli",
         "--config", str(config), "plan"], cwd=ROOT, env=env,
        capture_output=True, text=True, check=False)
    assert completed.returncode == 0 and completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload["dry_run"] is True and payload["mutations"] == 0 and payload["result"] == "PASS"
    assert not state.exists() and SECRET not in completed.stdout


def test_cli_failure_stdout_stderr_and_diagnostics_never_expose_environment_secret(tmp_path):
    identity = tmp_path / "identity.json"
    write_identity(identity)
    binding = tmp_path / ".env.isolated.local"
    binding.write_text("TRADERS_READONLY_API_DATABASE_URL=\nTRADERS_READONLY_API_HOST=127.0.0.1\n"
                       "TRADERS_READONLY_API_PORT=8765\n", encoding="utf-8")
    config = tmp_path / "composition.json"
    config.write_text(json.dumps({
        "deployment_driver": "ISOLATED_FILESYSTEM", "identity_config": str(identity),
        "protected_binding": str(binding), "state_root": str(tmp_path / "state"),
        "target_id": "declared-target",
    }), encoding="utf-8")
    env = dict(os.environ)
    env["TRADERS_PAPER_PREPARATION_ADMIN_DATABASE_URL"] = (
        f"postgresql+psycopg://admin:{SECRET}@127.0.0.1:1/isolated")
    env["TRADERS_PAPER_PREPARATION_TARGET_ID"] = "conflicting-target"
    completed = subprocess.run([
        sys.executable, "-m", "app.engine_paper.production_preparation_cli",
        "--config", str(config), "status"], cwd=ROOT, env=env,
        capture_output=True, text=True, check=False)
    assert completed.returncode == 7
    rendered = completed.stdout + completed.stderr
    assert SECRET not in rendered and "://" not in rendered and "admin" not in rendered


def test_cli_has_no_default_or_secret_arguments_and_no_trading_modes():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--config", "x.json"])
    help_text = parser.format_help().lower()
    forbidden = ("--password", "--secret", "--token", "database-url", " arm", " start", " trade", " live")
    assert not any(item in help_text for item in forbidden)


def test_production_binding_direct_access_guard():
    sources = "\n".join(path.read_text(encoding="utf-8") for path in (
        ROOT / "app/engine_paper/production_preparation.py",
        ROOT / "app/engine_paper/production_preparation_backend.py",
        ROOT / "app/engine_paper/production_preparation_cli.py",
    ))
    assert ".env.production.local" not in sources
    assert "os.environ" not in (ROOT / "app/engine_paper/production_preparation_cli.py").read_text(encoding="utf-8")
    assert "printenv" not in sources and "environ.items" not in sources
