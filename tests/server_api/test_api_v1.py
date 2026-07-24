from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.server_api import create_app
from tests.server_api.fakes import FakeReadRepository, NOW


def client_and_fake(*, raise_server_exceptions: bool = True):
    fake = FakeReadRepository()
    app = create_app(repositories=fake.api_repositories(), clock=lambda: NOW)
    return TestClient(app, raise_server_exceptions=raise_server_exceptions), fake


def assert_success(response) -> dict:
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"api_version", "generated_at", "data"}
    assert payload["api_version"] == "v1"
    assert re.fullmatch(r".*Z", payload["generated_at"])
    return payload["data"]


def assert_error(response, status: int, code: str) -> dict:
    assert response.status_code == status
    payload = response.json()
    assert payload["api_version"] == "v1"
    assert payload["error"]["code"] == code
    assert isinstance(payload["error"]["details"], dict)
    assert re.fullmatch(r"req-[0-9a-f]{32}", payload["request_id"])
    return payload


def test_health_endpoint_and_success_envelope():
    client, _ = client_and_fake()
    data = assert_success(client.get("/api/v1/health"))
    assert data["status"] == "OK"
    assert [item["name"] for item in data["services"]] == ["market-data", "online-orchestrator"]


def test_dashboard_endpoint():
    client, _ = client_and_fake()
    data = assert_success(client.get("/api/v1/dashboard"))
    assert data["active_incident_count"] == 1
    assert data["recent_runs"][0]["result_count"] == 1
    assert [item["symbol"] for item in data["markets"]] == ["BTCUSDT", "ETHUSDT"]


def test_markets_list_is_deterministic_and_unknown_safe():
    client, _ = client_and_fake()
    first = assert_success(client.get("/api/v1/markets"))
    second = assert_success(client.get("/api/v1/markets"))
    assert first == second
    assert [item["symbol"] for item in first["items"]] == ["BTCUSDT", "ETHUSDT"]
    assert first["items"][1]["status"] == "UNKNOWN"
    assert first["items"][1]["setup_status"] == "UNKNOWN"


def test_market_detail_decimal_timestamp_nullable_and_no_internal_fields():
    client, _ = client_and_fake()
    data = assert_success(client.get("/api/v1/markets/BTCUSDT"))
    assert data["close"] == "60123.45"
    assert isinstance(data["close"], str)
    assert data["summary"]["closed_until"].endswith("Z")
    assert data["future_bars_used"] is False
    assert "context" not in data
    nullable = assert_success(client.get("/api/v1/markets/ETHUSDT"))
    assert nullable["close"] is None
    assert nullable["summary"]["closed_until"] is None


def test_analysis_endpoint():
    client, _ = client_and_fake()
    data = assert_success(client.get("/api/v1/analysis/BTCUSDT"))
    assert data["analysis_id"].startswith("analysis:")
    assert data["confidence"] == 0.75
    assert data["direction"] == "BULLISH"


def test_setups_list_filters_and_detail_is_non_executable():
    client, _ = client_and_fake()
    page = assert_success(client.get("/api/v1/setups?status=SETUP_CANDIDATE"))
    assert len(page["items"]) == 2
    setup_id = page["items"][0]["setup_id"]
    detail = assert_success(client.get(f"/api/v1/setups/{setup_id}"))
    assert detail["executable"] is False
    assert detail["hypothetical_entry"] == "60100.25"
    assert detail["planned_rr"] == "2"


def test_incidents_list_filters_and_detail_is_redacted():
    client, _ = client_and_fake()
    page = assert_success(client.get("/api/v1/incidents?severity=ERROR"))
    assert len(page["items"]) == 1
    detail = assert_success(client.get("/api/v1/incidents/incident:001"))
    assert detail["reason_code"] == "MODULE_ERROR"
    assert "sql" not in detail["safe_description"].lower()


def test_resource_not_found_and_invalid_identifiers():
    client, _ = client_and_fake()
    assert_error(client.get("/api/v1/markets/SOLUSDT"), 404, "RESOURCE_NOT_FOUND")
    assert_error(client.get("/api/v1/markets/btcusdt"), 422, "INVALID_REQUEST")
    assert_error(client.get("/api/v1/setups/bad!id"), 422, "INVALID_REQUEST")


def test_invalid_timestamp_range_and_limit_are_rejected_before_repository():
    client, fake = client_and_fake()
    assert_error(client.get("/api/v1/setups?from=2026-07-24T00:00:00"), 422, "INVALID_REQUEST")
    assert "list_setups" not in fake.calls
    assert_error(
        client.get("/api/v1/setups?from=2026-07-25T00:00:00Z&to=2026-07-24T00:00:00Z"),
        422,
        "INVALID_REQUEST",
    )
    assert "list_setups" not in fake.calls
    assert_error(client.get("/api/v1/setups?limit=101"), 422, "INVALID_REQUEST")
    assert "list_setups" not in fake.calls


def test_invalid_cursor_is_contract_error_before_repository():
    client, fake = client_and_fake()
    assert_error(client.get("/api/v1/setups?cursor=not-a-cursor"), 422, "INVALID_CURSOR")
    assert "list_setups" not in fake.calls


def test_cursor_pagination_first_next_and_final_page():
    client, _ = client_and_fake()
    first = assert_success(client.get("/api/v1/setups?limit=2"))
    assert len(first["items"]) == 2
    assert first["page"]["next_cursor"]
    second = assert_success(client.get("/api/v1/setups", params={"limit": 2, "cursor": first["page"]["next_cursor"]}))
    assert len(second["items"]) == 1
    assert second["page"]["next_cursor"] is None
    assert {item["setup_id"] for item in first["items"]}.isdisjoint(
        {item["setup_id"] for item in second["items"]}
    )


def test_unconfigured_app_fails_closed_without_discovery():
    client = TestClient(create_app(clock=lambda: NOW))
    payload = assert_error(client.get("/api/v1/health"), 503, "SERVICE_NOT_CONFIGURED")
    assert payload["error"]["details"] == {}


def test_exception_is_sanitized():
    fake = FakeReadRepository()

    def fail():
        raise RuntimeError(r"postgresql://user:secret@host/db C:\private\file.sql")

    fake.get_health = fail
    app = create_app(repositories=fake.api_repositories(), clock=lambda: NOW)
    client = TestClient(app, raise_server_exceptions=False)
    payload = assert_error(client.get("/api/v1/health"), 500, "INTERNAL_ERROR")
    text = str(payload).lower()
    assert "secret" not in text
    assert "postgresql" not in text
    assert "private" not in text
