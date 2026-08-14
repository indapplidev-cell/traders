from __future__ import annotations

import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.engine_paper.production_preparation import (
    ALL_PREPARATION_ACTIONS, READONLY_BASELINE_GRANTS, READONLY_GRANTS,
)
from app.engine_paper.production_preparation_backend import compose_production_preparation


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def isolated_pg16():
    raw = os.environ.get("PAPER_BACKEND_TEST_PG_URL")
    if not raw:
        pytest.fail("PAPER_BACKEND_TEST_PG_URL is required")
    assert "127.0.0.1" in raw and "/paper_backend_remediation" in raw
    engine = create_engine(raw, hide_parameters=True)
    with engine.connect() as connection:
        assert str(connection.execute(text("SHOW server_version_num")).scalar_one()).startswith("16")
    import app.config.settings as settings
    original = settings.get_settings
    settings.get_settings = lambda: type("Settings", (), {"database_url": raw})()
    try:
        config = Config("alembic.ini")
        with engine.connect() as connection:
            relation = connection.execute(text("SELECT to_regclass('public.alembic_version')")).scalar_one()
        if relation:
            command.downgrade(config, "0008_engine_orchestrator_freshness_retry")
        else:
            command.upgrade(config, "0008_engine_orchestrator_freshness_retry")
        with engine.begin() as connection:
            connection.exec_driver_sql('DROP ROLE IF EXISTS "traders_paper_runtime"')
            connection.exec_driver_sql('DROP ROLE IF EXISTS "traders_readonly_api"')
            connection.exec_driver_sql(
                'CREATE ROLE "traders_readonly_api" NOLOGIN NOSUPERUSER NOCREATEDB '
                'NOCREATEROLE NOREPLICATION NOBYPASSRLS')
            for grant in READONLY_BASELINE_GRANTS:
                connection.exec_driver_sql(
                    f'GRANT SELECT ON TABLE "{grant.table}" TO "traders_readonly_api"'
                )
        yield engine, raw
    finally:
        with engine.begin() as connection:
            for role in ("traders_paper_runtime", "traders_readonly_api"):
                connection.exec_driver_sql(f'DROP OWNED BY "{role}"')
                connection.exec_driver_sql(f'DROP ROLE IF EXISTS "{role}"')
        engine.dispose()
        settings.get_settings = original


def _files(tmp_path: Path, raw: str):
    admin = make_url(raw)
    identity = tmp_path / "paper-identity.json"
    identity.write_text(json.dumps({
        "PAPER_PRODUCTION_ACCOUNT_ID": "PAPER-ISOLATED-PRIMARY",
        "PAPER_PRODUCTION_ACCOUNTING_SESSION_ID": "PAPER-ISOLATED-LIFECYCLE-01",
        "PAPER_PRODUCTION_CURRENCY": "USDT",
    }), encoding="utf-8")
    binding = tmp_path / ".env.isolated.local"
    binding.write_text(f"TRADERS_ML_POSTGRES_PASSWORD={admin.password}\n"
                       "TRADERS_READONLY_API_DATABASE_URL=\nTRADERS_READONLY_API_HOST=127.0.0.1\n"
                       "TRADERS_READONLY_API_PORT=8765\n", encoding="utf-8")
    state = tmp_path / "state"
    config = tmp_path / "composition.json"
    config.write_text(json.dumps({
        "deployment_driver": "ISOLATED_FILESYSTEM", "identity_config": str(identity),
        "protected_binding": str(binding), "state_root": str(state),
        "target_id": "isolated-production-target",
        "admin_host": admin.host, "admin_port": admin.port,
        "admin_database": admin.database, "admin_user": admin.username,
    }), encoding="utf-8")
    return config, binding, state


def _run(config: Path, mode: str = "execute"):
    env = dict(os.environ)
    env.pop("TRADERS_PAPER_PREPARATION_ADMIN_DATABASE_URL", None)
    env.pop("TRADERS_PAPER_PREPARATION_TARGET_ID", None)
    command_line = [
        sys.executable, "-m", "app.engine_paper.production_preparation_cli",
        "--config", str(config), mode,
    ]
    if mode == "execute":
        command_line.extend([
            "--ack", "I_ACKNOWLEDGE_PRODUCTION_PREPARATION_MUTATIONS",
            "--actions", ",".join(item.value for item in ALL_PREPARATION_ACTIONS),
            "--orchestrate-schema-and-baseline", "--initial-balance-usdt", "100.00",
        ])
    return subprocess.run(command_line, cwd=ROOT, env=env,
                          capture_output=True, text=True, check=False)


def test_real_cli_execute_replay_roles_grants_baseline_and_zero_trade(isolated_pg16, tmp_path):
    engine, raw = isolated_pg16
    config, binding, state = _files(tmp_path, raw)
    with engine.connect() as connection:
        before_revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        before_roles = connection.execute(text(
            "SELECT count(*) FROM pg_roles WHERE rolname IN ('traders_paper_runtime','traders_readonly_api')"
        )).scalar_one()
    for mode in ("status", "plan"):
        safe = _run(config, mode)
        assert safe.returncode == 0, safe.stderr
        payload = json.loads(safe.stdout)
        assert payload["result"] == "PASS" and payload["target_verified"] is True
        assert str(make_url(raw).password) not in safe.stdout + safe.stderr
        assert "://" not in safe.stdout + safe.stderr
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == before_revision
        assert connection.execute(text(
            "SELECT count(*) FROM pg_roles WHERE rolname IN ('traders_paper_runtime','traders_readonly_api')"
        )).scalar_one() == before_roles
    assert not state.exists()
    first = _run(config)
    assert first.returncode == 0, first.stderr
    first_output = json.loads(first.stdout)
    assert first_output["result"] == "PASS" and first_output["binding_ready"] is True
    protected_content = binding.read_text(encoding="utf-8")
    runtime_binding_line = next(line for line in protected_content.splitlines()
                                if line.startswith("TRADERS_PAPER_RUNTIME_DATABASE_URL="))
    assert runtime_binding_line
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0014_paper_canary_selection_policy"
        attrs = connection.execute(text(
            "SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls "
            "FROM pg_roles WHERE rolname='traders_paper_runtime'")).one()
        assert tuple(attrs) == (True, False, False, False, False, False)
        readonly_attrs = connection.execute(text(
            "SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls "
            "FROM pg_roles WHERE rolname='traders_readonly_api'")).one()
        assert not any(readonly_attrs)
        assert connection.execute(text("SELECT count(*) FROM paper_account_baselines")).scalar_one() == 1
        baseline = connection.execute(text(
            "SELECT account_id,accounting_session_id,currency,initial_balance FROM paper_account_baselines")).one()
        assert tuple(baseline[:3]) == ("PAPER-ISOLATED-PRIMARY", "PAPER-ISOLATED-LIFECYCLE-01", "USDT")
        assert baseline[3] == Decimal("100.00")
        for table in ("paper_execution_commands", "paper_orders", "paper_fills", "paper_positions",
                      "paper_exit_decisions", "paper_first_canary_sessions"):
            assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
        assert not connection.execute(text(
            "SELECT has_table_privilege('traders_paper_runtime','paper_account_baselines','INSERT,UPDATE,DELETE')")).scalar_one()
        assert not connection.execute(text(
            "SELECT has_table_privilege('traders_readonly_api','paper_orders','INSERT,UPDATE,DELETE')")).scalar_one()
    assert json.loads((state / "paper-runtime.disabled.json").read_text())["state"] == "DEPLOYED_DISABLED"
    assert json.loads((state / "readonly-api.narrow.json").read_text())["write_routes"] == 0

    second = _run(config)
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["mutations"] == 0
    assert binding.read_text(encoding="utf-8") == protected_content
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM paper_account_baselines")).scalar_one() == 1


def test_privilege_drift_fails_closed_before_mutation(isolated_pg16, tmp_path):
    engine, raw = isolated_pg16
    config, binding, state = _files(tmp_path, raw)
    if not binding.exists():
        pytest.fail("isolated binding fixture missing")
    with engine.begin() as connection:
        connection.exec_driver_sql('ALTER ROLE "traders_paper_runtime" CREATEDB')
    before = state.joinpath("paper-runtime.disabled.json").read_bytes() if state.exists() else b""
    result = _run(config)
    assert result.returncode == 4
    assert "CREATEDB" not in result.stdout + result.stderr
    after = state.joinpath("paper-runtime.disabled.json").read_bytes() if state.exists() else b""
    assert after == before
    with engine.begin() as connection:
        connection.exec_driver_sql('ALTER ROLE "traders_paper_runtime" NOCREATEDB')


def test_real_pg16_partial_0013_legitimate_baseline_grants_resume_and_replay(
    isolated_pg16, tmp_path,
):
    engine, raw = isolated_pg16
    config, binding, state_root = _files(tmp_path, raw)
    command.upgrade(Config("alembic.ini"), "0014_paper_canary_selection_policy")
    with engine.begin() as connection:
        connection.exec_driver_sql('DROP OWNED BY "traders_paper_runtime"')
        connection.exec_driver_sql('DROP ROLE "traders_paper_runtime"')
        connection.exec_driver_sql(
            'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM "traders_readonly_api"'
        )
        connection.execute(text("DELETE FROM paper_account_baselines"))
        for grant in READONLY_BASELINE_GRANTS:
            connection.exec_driver_sql(
                f'GRANT SELECT ON TABLE "{grant.table}" TO "traders_readonly_api"'
            )

    composition_config = json.loads(config.read_text(encoding="utf-8"))
    composition = compose_production_preparation(composition_config)
    # This is the exact old PAPER-only comparison that rejected production.
    assert composition.backend._extra_privileges("traders_readonly_api", READONLY_GRANTS)
    assert not composition.backend.inspect_privilege_drift()

    status = _run(config, "status")
    assert status.returncode == 0, status.stderr
    status_payload = json.loads(status.stdout)
    assert status_payload["alembic_revision"] == "0014_paper_canary_selection_policy"
    assert status_payload["preparation_phase"] == "PARTIAL_RESUMABLE"
    assert status_payload["baseline_ready"] is False
    assert status_payload["runtime_binding_ready"] is False
    assert status_payload["privilege_drift"] is False
    assert status_payload["schema_head_count"] == 1
    assert status_payload["baseline_count"] == 0
    assert all(status_payload[key] == 0 for key in (
        "paper_commands", "paper_orders", "paper_fills", "paper_positions", "paper_canaries",
    ))

    plan = _run(config, "plan")
    assert plan.returncode == 0, plan.stderr
    plan_payload = json.loads(plan.stdout)
    assert plan_payload["preparation_phase"] == "PARTIAL_RESUMABLE"
    assert plan_payload["migration_action_required"] is False
    assert plan_payload["migration_already_satisfied"] is True
    assert plan_payload["planned_actions"] == [item.value for item in ALL_PREPARATION_ACTIONS]

    first = _run(config)
    assert first.returncode == 0, first.stderr
    first_payload = json.loads(first.stdout)
    assert first_payload["result"] == "PASS"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0014_paper_canary_selection_policy"
        )
        assert connection.execute(text("SELECT count(*) FROM paper_account_baselines")).scalar_one() == 1
        for table in ("paper_execution_commands", "paper_orders", "paper_fills", "paper_positions",
                      "paper_first_canary_sessions"):
            assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0

    replay = _run(config)
    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay.stdout)["mutations"] == 0
    completed = _run(config, "status")
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["preparation_phase"] == "COMPLETED"
