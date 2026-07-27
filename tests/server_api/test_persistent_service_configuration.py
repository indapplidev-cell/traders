from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "ops" / "production" / "readonly-api" / "compose.yaml"
RUNBOOK = ROOT / "docs" / "operations" / "readonly_api_persistent_service.md"


def compose_text() -> str:
    return COMPOSE.read_text(encoding="utf-8")


def test_localhost_only_persistent_boundary_and_runtime_secret_file() -> None:
    text = compose_text()
    assert '"127.0.0.1:8765:8765"' in text
    assert "../../../.env.production.local" in text
    assert 'TRADERS_READONLY_API_HOST: "0.0.0.0"' in text
    assert 'TRADERS_READONLY_API_PORT: "8765"' in text
    assert "TRADERS_READONLY_API_DATABASE_URL:" not in text


def test_service_is_hardened_bounded_and_independently_managed() -> None:
    text = compose_text()
    for required in (
        "target: readonly-api",
        'user: "10001:10001"',
        "read_only: true",
        "- ALL",
        "- no-new-privileges:true",
        "restart: unless-stopped",
        'cpus: "0.50"',
        "mem_limit: 256m",
        "pids_limit: 64",
        "- production",
    ):
        assert required in text


def test_healthcheck_proves_http_and_database_readiness() -> None:
    text = compose_text()
    assert "- CMD" in text
    assert "- python" in text
    assert "127.0.0.1:8765/api/v1/health" in text
    assert "interval: 10s" in text
    assert "retries: 5" in text


def test_runbook_forbids_stack_down_and_limits_rollback() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "Do not run `docker compose down`" in text
    assert "stop readonly-api" in text
    assert "rm -f readonly-api" in text
    assert "PostgreSQL, market-data, or the" in text
    assert "online orchestrator" in text
