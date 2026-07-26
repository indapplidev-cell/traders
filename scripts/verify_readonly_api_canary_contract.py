"""Fail-closed static verifier for the disabled Readonly API canary contract."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANARY_DIR = ROOT / "ops" / "canary" / "readonly-api"
COMPOSE = CANARY_DIR / "compose.yaml"
ENV_EXAMPLE = CANARY_DIR / "readonly-api.env.example"
RUNBOOK = CANARY_DIR / "CANARY_RUNBOOK.md"
ROLLBACK = CANARY_DIR / "ROLLBACK_PLAN.md"
SERVICE = "readonly-api-canary"
PROFILE = "readonly-api-canary"
IMAGE = "traders-readonly-api:880264b1-canary-preparation"
ALLOWED_ENVIRONMENT = {
    "TRADERS_READONLY_API_DATABASE_URL",
    "TRADERS_READONLY_API_HOST",
    "TRADERS_READONLY_API_PORT",
    "TRADERS_READONLY_API_LOG_LEVEL",
    "TRADERS_READONLY_API_STATEMENT_TIMEOUT_MS",
    "TRADERS_READONLY_API_POOL_SIZE",
    "TRADERS_READONLY_API_POOL_TIMEOUT_SECONDS",
}
STOP_CRITERIA = (
    "healthcheck failure",
    "any unexpected HTTP 5xx",
    "route count differs from 9",
    "any write route appears",
    "DB row count changes",
    "DB content hash changes",
    "Alembic version changes",
    "schema object changes",
    "readonly privilege probe unexpectedly succeeds",
    "container restart",
    "memory limit breach/OOM",
    "CPU saturation beyond",
    "connection pool exhaustion",
    "statement timeout violation",
    "credential/config leakage in logs",
    "market-data/orchestrator degradation after future real start",
)
RUNBOOK_SECTIONS = tuple(f"## {number}." for number in range(1, 17))
ROLLBACK_STEPS = tuple(f"{number}." for number in range(1, 11))
CREDENTIAL_PATTERNS = (
    re.compile(r"postgres(?:ql)?(?:\+psycopg)?://[^<\s:]+:[^<\s@]+@", re.I),
    re.compile(r"(?i)(?:password|secret|api[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9+/=_-]{8,}"),
)


class ContractError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _compose_json(*, profile: bool) -> dict:
    command = ["docker", "compose", "-f", str(COMPOSE)]
    if profile:
        command += ["--profile", PROFILE]
    command += ["config", "--format", "json"]
    environment = {
        **os.environ,
        "TRADERS_READONLY_API_DATABASE_URL": "postgresql+psycopg://<READONLY_ROLE>:<READONLY_PASSWORD>@<DATABASE_HOST>:5432/<DATABASE_NAME>",
    }
    completed = subprocess.run(
        command, cwd=ROOT, env=environment, capture_output=True, text=True, check=False
    )
    _require(completed.returncode == 0, f"docker compose config failed: {completed.stderr.strip()}")
    return json.loads(completed.stdout)


def verify() -> list[str]:
    checks: list[str] = []
    for path in (COMPOSE, ENV_EXAMPLE, RUNBOOK, ROLLBACK):
        _require(path.is_file(), f"required file missing: {path.relative_to(ROOT)}")
    source = COMPOSE.read_text(encoding="utf-8")
    env_source = ENV_EXAMPLE.read_text(encoding="utf-8")
    runbook = RUNBOOK.read_text(encoding="utf-8")
    rollback = ROLLBACK.read_text(encoding="utf-8")

    default = _compose_json(profile=False)
    _require(not default.get("services"), "canary service must be absent without explicit profile")
    configured = _compose_json(profile=True)
    _require(set(configured.get("services", {})) == {SERVICE}, "service name must be exact")
    service = configured["services"][SERVICE]
    _require(service.get("profiles") == [PROFILE], "exact canary profile is required")
    _require(service.get("image") == IMAGE and ":latest" not in IMAGE, "image must be immutable and non-latest")
    build = service.get("build", {})
    _require(build.get("target") == "readonly-api", "readonly-api build target is required")
    _require(build.get("labels", {}).get("org.opencontainers.image.revision") == "880264b1d0a881c01f8fe67dc151c0b69dd4c649", "root revision build label is required")
    _require(service.get("read_only") is True, "read-only root filesystem is required")
    _require(any(str(item).startswith("/tmp") for item in service.get("tmpfs", [])), "/tmp tmpfs is required")
    _require(str(service.get("user")) == "10001:10001", "non-root UID/GID is required")
    _require(service.get("cap_drop") == ["ALL"], "cap_drop ALL is required")
    _require("no-new-privileges:true" in service.get("security_opt", []), "no-new-privileges is required")
    _require(service.get("restart") == "no", "restart policy must be no")
    _require(service.get("deploy", {}).get("replicas") == 1, "single replica is required")
    _require(float(service.get("cpus", 99)) <= 1.0, "CPU limit must be at most 1.0")
    _require(int(service.get("mem_limit", 2**60)) <= 512 * 1024 * 1024, "memory limit must be at most 512 MiB")
    _require(int(service.get("pids_limit", 9999)) <= 128, "PIDs limit must be at most 128")
    _require(bool(service.get("healthcheck", {}).get("test")), "healthcheck is required")
    ports = service.get("ports", [])
    _require(len(ports) == 1, "exactly one published port is required")
    port = ports[0]
    _require(port.get("host_ip") == "127.0.0.1" and int(port.get("target")) == 8080, "port must bind localhost only to internal 8080")
    _require(set(service.get("environment", {})) == ALLOWED_ENVIRONMENT, "environment allowlist mismatch")
    _require("/var/run/docker.sock" not in source and "/var/run/docker.sock" not in json.dumps(service), "Docker socket is forbidden")
    _require("env_file" not in service, "unfiltered env_file injection is forbidden")
    _require("DO NOT USE DATABASE OWNER/ADMIN CREDENTIALS" in env_source, "owner/admin warning is required")
    _require("<READONLY_ROLE>" in env_source and "<READONLY_PASSWORD>" in env_source, "placeholder-only DSN is required")
    for pattern in CREDENTIAL_PATTERNS:
        _require(not pattern.search(source), "credential-shaped literal found in Compose")
        _require(not pattern.search(env_source), "credential-shaped literal found in env example")
    _require(all(section in runbook for section in RUNBOOK_SECTIONS), "runbook sections 1..16 are required")
    _require("This runbook does not authorize deployment by itself." in runbook, "authorization boundary missing")
    _require(all(item.lower() in runbook.lower() for item in STOP_CRITERIA), "stop criteria incomplete")
    _require(all(step in rollback for step in ROLLBACK_STEPS), "rollback steps 1..10 are required")
    checks.extend(
        [
            "compose",
            "disabled-default",
            "profile",
            "image-build",
            "security",
            "resources",
            "healthcheck",
            "environment",
            "credentials",
            "runbook",
            "rollback",
            "stop-criteria",
        ]
    )
    return checks


def main() -> int:
    try:
        checks = verify()
    except (ContractError, json.JSONDecodeError, OSError) as exc:
        print(f"CANARY_CONTRACT=FAIL reason={exc}", file=sys.stderr)
        return 1
    print(f"CANARY_CONTRACT=PASS checks={len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
