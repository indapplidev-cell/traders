from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "ops" / "canary" / "readonly-api" / "compose.yaml"
RUNBOOK = COMPOSE.with_name("CANARY_RUNBOOK.md")
ROLLBACK = COMPOSE.with_name("ROLLBACK_PLAN.md")
VERIFIER = ROOT / "scripts" / "verify_readonly_api_canary_contract.py"
SERVICE = "readonly-api-canary"
PROFILE = "readonly-api-canary"
ALLOWED_ENVIRONMENT = {
    "TRADERS_READONLY_API_DATABASE_URL",
    "TRADERS_READONLY_API_HOST",
    "TRADERS_READONLY_API_PORT",
    "TRADERS_READONLY_API_LOG_LEVEL",
    "TRADERS_READONLY_API_STATEMENT_TIMEOUT_MS",
    "TRADERS_READONLY_API_POOL_SIZE",
    "TRADERS_READONLY_API_POOL_TIMEOUT_SECONDS",
}


def compose_config(*, profile: bool) -> dict:
    command = ["docker", "compose", "-f", str(COMPOSE)]
    if profile:
        command += ["--profile", PROFILE]
    command += ["config", "--format", "json"]
    environment = {
        **os.environ,
        "TRADERS_READONLY_API_DATABASE_URL": "postgresql+psycopg://<READONLY_ROLE>:<READONLY_PASSWORD>@<DATABASE_HOST>:5432/<DATABASE_NAME>",
    }
    completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def service() -> dict:
    return compose_config(profile=True)["services"][SERVICE]


def test_profile_required_and_default_config_does_not_start_canary():
    assert compose_config(profile=False).get("services") == {}
    assert service()["profiles"] == [PROFILE]


def test_service_name_and_localhost_only_bind():
    configured = compose_config(profile=True)
    assert set(configured["services"]) == {SERVICE}
    assert service()["ports"] == [{
        "mode": "ingress",
        "target": 8080,
        "published": "18080",
        "protocol": "tcp",
        "host_ip": "127.0.0.1",
    }]


def test_read_only_rootfs_and_tmpfs():
    configured = service()
    assert configured["read_only"] is True
    assert any(item.startswith("/tmp") for item in configured["tmpfs"])


def test_non_root_capabilities_and_no_new_privileges():
    configured = service()
    assert configured["user"] == "10001:10001"
    assert configured["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in configured["security_opt"]


def test_bounded_resources_single_replica_and_restart_no():
    configured = service()
    assert float(configured["cpus"]) <= 1.0
    assert int(configured["mem_limit"]) <= 512 * 1024 * 1024
    assert configured["pids_limit"] <= 128
    assert configured["deploy"]["replicas"] == 1
    assert configured["restart"] == "no"


def test_healthcheck():
    configured = service()
    assert configured["healthcheck"]["test"][:2] == ["CMD", "python"]
    assert "/api/v1/health" in configured["healthcheck"]["test"][-1]


def test_environment_allowlist_and_no_unfiltered_env_file():
    configured = service()
    assert set(configured["environment"]) == ALLOWED_ENVIRONMENT
    assert "env_file" not in configured


def test_no_credential_literals_or_docker_socket():
    source = COMPOSE.read_text(encoding="utf-8")
    example = COMPOSE.with_name("readonly-api.env.example").read_text(encoding="utf-8")
    assert "/var/run/docker.sock" not in source
    assert "DO NOT USE DATABASE OWNER/ADMIN CREDENTIALS" in example
    assert "postgresql+psycopg://<READONLY_ROLE>:<READONLY_PASSWORD>@" in example


def test_immutable_image_and_build_contract():
    configured = service()
    assert configured["image"] == "traders-readonly-api:880264b1-canary-preparation"
    assert configured["build"]["target"] == "readonly-api"
    assert configured["build"]["labels"]["org.opencontainers.image.revision"] == "880264b1d0a881c01f8fe67dc151c0b69dd4c649"


def test_runbook_required_sections_and_authorization_boundary():
    text = RUNBOOK.read_text(encoding="utf-8")
    assert all(f"## {number}." in text for number in range(1, 17))
    assert "This runbook does not authorize deployment by itself." in text
    assert "127.0.0.1" in text
    assert "9 GET and 0 write routes" in text


def test_stop_criteria_complete():
    text = RUNBOOK.read_text(encoding="utf-8").lower()
    required = (
        "healthcheck failure", "unexpected http 5xx", "route count differs from 9",
        "any write route appears", "db row count changes", "db content hash changes",
        "alembic version changes", "schema object changes",
        "readonly privilege probe unexpectedly succeeds", "container restart",
        "memory limit breach/oom", "cpu saturation beyond", "connection pool exhaustion",
        "statement timeout violation", "credential/config leakage in logs",
        "market-data/orchestrator degradation after future real start",
    )
    assert all(item in text for item in required)


def test_rollback_required_steps():
    text = ROLLBACK.read_text(encoding="utf-8")
    assert all(f"{number}." in text for number in range(1, 11))
    assert "Do not run Alembic downgrade" in text
    assert "Do not restart unaffected services" in text


def test_verifier_passes_in_process_and_as_cli():
    spec = importlib.util.spec_from_file_location("canary_verifier", VERIFIER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len(module.verify()) == 12
    completed = subprocess.run([sys.executable, str(VERIFIER)], cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert "CANARY_CONTRACT=PASS" in completed.stdout
