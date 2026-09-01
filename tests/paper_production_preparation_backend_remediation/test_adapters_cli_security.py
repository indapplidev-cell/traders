from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from app.engine_paper.production_preparation import PaperProductionIdentityError
from app.engine_paper.production_preparation_backend import (
    PRODUCTION_ADMIN_PASSWORD_KEY,
    PRODUCTION_PROTECTED_SOURCE,
    PRODUCTION_TARGET_ID,
    RUNTIME_DATABASE_KEY,
    READONLY_EXPECTED_GET_ROUTES,
    READONLY_LEGACY_ROUTES,
    READONLY_STATIC_PAPER_HTTP_PATHS,
    PaperPreparationAdapterError,
    PaperPreparationDeploymentAdapter,
    ReadonlyRuntimeAcceptance,
    PaperProductionPreparationTargetBinding,
    PaperProductionIdentityConfigurationAdapter,
    ProtectedPaperRuntimeBindingAdapter,
    compose_production_preparation,
)
from app.engine_paper.production_preparation_cli import build_parser


ROOT = Path(__file__).resolve().parents[2]
SECRET = "-".join(("isolated", "only", "secret", "value", "that", "must", "never", "escape"))


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
    binding.write_text("TRADERS_ML_POSTGRES_PASSWORD=synthetic-admin\n"
                       "TRADERS_READONLY_API_DATABASE_URL=\nTRADERS_READONLY_API_HOST=127.0.0.1\n"
                       "TRADERS_READONLY_API_PORT=8765\n", encoding="utf-8")
    monkeypatch.setattr("app.engine_paper.production_preparation_backend.secrets.token_urlsafe",
                        lambda _: SECRET)
    adapter = ProtectedPaperRuntimeBindingAdapter(
        binding, "postgresql+psycopg" + "://admin:isolated-admin@127.0.0.1:55432/isolated")
    security_before = windows_sddl(binding)
    installed = []
    result = adapter.ensure(installed.append)
    assert result.changed and installed == [SECRET]
    validation = adapter.metadata()
    rendered = repr(validation) + str(validation.safe_dict()) + repr(result)
    assert validation.binding_valid and SECRET not in rendered and "://" not in rendered
    assert not adapter.ensure(installed.append).changed and installed == [SECRET]
    assert windows_sddl(binding) == security_before
    assert f"{PRODUCTION_ADMIN_PASSWORD_KEY}=synthetic-admin" in binding.read_text()
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
        binding, "postgresql+psycopg" + "://admin:isolated-admin@127.0.0.1:55432/isolated")
    with pytest.raises(PaperPreparationAdapterError) as caught:
        adapter.ensure(lambda _: (_ for _ in ()).throw(RuntimeError("uncertain secret " + SECRET)))
    assert str(caught.value) == "PROTECTED_BINDING_INSTALL_FAILED"
    replayed = []
    assert adapter.ensure(replayed.append).changed
    assert generated == [SECRET] and replayed == [SECRET]
    assert SECRET not in repr(caught.value)


def test_cli_plan_missing_protected_binding_fails_closed_without_mutation(tmp_path):
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
    assert completed.returncode == 5 and completed.stdout == ""
    payload = json.loads(completed.stderr)
    assert payload["reason"] == "PRODUCTION_TARGET_BINDING_UNAVAILABLE"
    assert not state.exists() and SECRET not in completed.stderr


def test_cli_failure_stdout_stderr_and_diagnostics_never_expose_protected_secret(tmp_path):
    identity = tmp_path / "identity.json"
    write_identity(identity)
    binding = tmp_path / ".env.isolated.local"
    binding.write_text(f"{PRODUCTION_ADMIN_PASSWORD_KEY}={SECRET}\n"
                       "TRADERS_READONLY_API_DATABASE_URL=\nTRADERS_READONLY_API_HOST=127.0.0.1\n"
                       "TRADERS_READONLY_API_PORT=8765\n", encoding="utf-8")
    config = tmp_path / "composition.json"
    config.write_text(json.dumps({
        "deployment_driver": "ISOLATED_FILESYSTEM", "identity_config": str(identity),
        "protected_binding": str(binding), "state_root": str(tmp_path / "state"),
        "target_id": "declared-target",
    }), encoding="utf-8")
    completed = subprocess.run([
        sys.executable, "-m", "app.engine_paper.production_preparation_cli",
        "--config", str(config), "status"], cwd=ROOT,
        capture_output=True, text=True, check=False)
    assert completed.returncode == 3
    rendered = completed.stdout + completed.stderr
    assert SECRET not in rendered and "://" not in rendered and "admin" not in rendered


def test_cli_has_no_default_or_secret_arguments_and_no_trading_modes():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--config", "x.json"])
    help_text = parser.format_help().lower()
    forbidden = ("--password", "--secret", "--token", "database-url", " arm", " start", " trade", " live")
    assert not any(item in help_text for item in forbidden)


def test_readonly_acceptance_includes_funnel_export_and_retries_timeout(monkeypatch):
    assert "/api/v1/trading/funnel/export" in READONLY_EXPECTED_GET_ROUTES
    calls = 0

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self, _limit): return b'{"ok":true}'

    def urlopen(_request, *, timeout):
        nonlocal calls
        calls += 1
        assert timeout == 15
        if calls == 1:
            raise TimeoutError
        return Response()

    monkeypatch.setattr(
        "app.engine_paper.production_preparation_backend.urllib.request.urlopen", urlopen,
    )
    assert PaperPreparationDeploymentAdapter._http_json("/api/v1/health") == (200, {"ok": True})
    assert calls == 2


def test_readonly_ready_rejects_stale_marker_even_when_stale_runtime_is_healthy(tmp_path):
    current = "sha256:" + "a" * 64
    acceptance = lambda identity: ReadonlyRuntimeAcceptance(
        identity, True, READONLY_EXPECTED_GET_ROUTES, 0,
        (200,) * len(READONLY_LEGACY_ROUTES),
        (200,) * len(READONLY_STATIC_PAPER_HTTP_PATHS),
    )
    adapter = PaperPreparationDeploymentAdapter(
        tmp_path, source_identity_provider=lambda: current, runtime_probe=acceptance,
    )
    marker = {
        "deployment": "NARROW", "service": "readonly-api", "schema": 2,
        "source_identity": "sha256:" + "b" * 64, "runtime_health": "PASS",
        "get_routes": len(READONLY_EXPECTED_GET_ROUTES), "write_routes": 0,
        "legacy_endpoints": len(READONLY_LEGACY_ROUTES),
        "paper_endpoints": len(tuple(
            path for path in READONLY_EXPECTED_GET_ROUTES if "/paper/" in path
        )),
    }
    (tmp_path / "readonly-api.narrow.json").write_text(json.dumps(marker), encoding="utf-8")
    assert not adapter.readonly_api_narrow_ready()
    marker["source_identity"] = current
    (tmp_path / "readonly-api.narrow.json").write_text(json.dumps(marker), encoding="utf-8")
    assert adapter.readonly_api_narrow_ready()


def test_target_binding_is_safe_and_never_returns_protected_value(tmp_path):
    captured = []

    class Engine:
        pass

    def engine_factory(url, **options):
        captured.append((url, options))
        return Engine()

    binding = PaperProductionPreparationTargetBinding(
        tmp_path / "protected", "isolated-production-target",
        protected_value_provider=lambda _: SECRET,
        engine_factory=engine_factory,
    )
    engine = binding.build_engine()
    rendered = repr(binding) + str(binding) + repr(engine)
    assert SECRET not in rendered and "://" not in rendered
    assert len(captured) == 1 and captured[0][0].password == SECRET
    assert captured[0][1] == {"hide_parameters": True, "pool_pre_ping": True}

    failing = PaperProductionPreparationTargetBinding(
        tmp_path / "protected", "isolated-production-target",
        protected_value_provider=lambda _: SECRET,
        engine_factory=lambda url, **_: (_ for _ in ()).throw(RuntimeError(str(url))),
    )
    with pytest.raises(PaperPreparationAdapterError) as caught:
        failing.build_engine()
    assert str(caught.value) == "PRODUCTION_TARGET_BINDING_INVALID"
    assert SECRET not in repr(caught.value) + str(caught.value)


def test_target_binding_missing_invalid_and_logging_are_secret_free(tmp_path, caplog):
    missing = PaperProductionPreparationTargetBinding(tmp_path / "missing", "isolated-target")
    with pytest.raises(PaperPreparationAdapterError, match="PRODUCTION_TARGET_BINDING_UNAVAILABLE"):
        missing.build_engine()
    invalid_path = tmp_path / "invalid"
    invalid_path.write_text(f"{PRODUCTION_ADMIN_PASSWORD_KEY}=\n", encoding="utf-8")
    invalid = PaperProductionPreparationTargetBinding(invalid_path, "isolated-target")
    with pytest.raises(PaperPreparationAdapterError) as caught:
        invalid.build_engine()
    with caplog.at_level(logging.DEBUG):
        logging.getLogger("binding-test").debug("%r %s", invalid, invalid)
    rendered = str(caught.value) + caplog.text
    assert SECRET not in rendered and "://" not in rendered


@pytest.mark.parametrize("target", ["test-target", "isolated-production-target"])
def test_production_mode_rejects_non_production_target_before_secret_load(target):
    config = {
        "deployment_driver": "DOCKER_COMPOSE_NARROW",
        "identity_config": str(ROOT / "ops/production/paper-identity.json"),
        "protected_binding": str(PRODUCTION_PROTECTED_SOURCE),
        "state_root": str(ROOT / "artifacts/paper-production-preparation"),
        "target_id": target,
        "compose_file": str(ROOT / "ops/production/readonly-api/compose.yaml"),
    }
    called = []
    with pytest.raises(PaperPreparationAdapterError, match="PRODUCTION_TARGET_MISMATCH"):
        compose_production_preparation(
            config, production_mode=True,
            protected_value_provider=lambda _: called.append(True) or SECRET,
        )
    assert called == []


def test_production_binding_access_is_single_trusted_source_path():
    sources = "\n".join(path.read_text(encoding="utf-8") for path in (
        ROOT / "app/engine_paper/production_preparation.py",
        ROOT / "app/engine_paper/production_preparation_backend.py",
        ROOT / "app/engine_paper/production_preparation_cli.py",
    ))
    assert "os.environ" not in (ROOT / "app/engine_paper/production_preparation_cli.py").read_text(encoding="utf-8")
    assert "printenv" not in sources and "environ.items" not in sources
    assert sources.count(' / ".env.production.local"') == 1
    assert "TRADERS_PAPER_PREPARATION_ADMIN_DATABASE_URL" not in sources
