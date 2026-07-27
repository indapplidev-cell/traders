import json
from datetime import datetime, timezone

from app.engine_market_data.continuous_sync_state import (
    ALLOWED_SYNC_STATUSES,
    ContinuousSyncStatus,
)
from app.engine_market_data.freshness_monitor import FreshnessMonitor
from app.engine_market_data.operational.prod_smoke import (
    ProdSmokeRunner,
    health_payload_operational,
)
from app.engine_observation.observation_runner import _read_health
from tests.engine_market_data_04_helpers import FakeRepository, candle


UTC = timezone.utc


def report_payload(now_ms: int, *, stored_open_ms: int):
    repository = FakeRepository([candle("BTCUSDT", "1m", stored_open_ms)])
    snapshot = FreshnessMonitor(repository).snapshot(
        "BTCUSDT", "1m", now_ms, heartbeat_progressing=True,
        last_success_at="2026-07-27T00:00:00Z",
    )
    return FreshnessMonitor.report(
        [snapshot],
        "consumer-test",
        generated_at=datetime.fromtimestamp(now_ms / 1000, UTC),
    ).to_dict()


def test_public_persisted_enum_is_unchanged():
    assert ALLOWED_SYNC_STATUSES == (
        "OK", "STALE", "GAP_DETECTED", "RECOVERING", "DEGRADED",
        "DISCONNECTED", "ERROR", "NOT_CONFIGURED",
    )
    assert ContinuousSyncStatus("OK") is ContinuousSyncStatus.OK


def test_prod_smoke_accepts_within_grace_and_blocks_expired_deadline():
    boundary = 600_000
    stored_prior = boundary - 120_000
    within = report_payload(boundary + 1, stored_open_ms=stored_prior)
    expired = report_payload(boundary + 10_001, stored_open_ms=stored_prior)

    assert within["overall_status"] == "OK"
    assert within["reason_code"] == "BOUNDARY_WITHIN_GRACE"
    assert health_payload_operational(within) is True
    assert ProdSmokeRunner._strict_health_errors(within) == []

    assert expired["overall_status"] == "RECOVERING"
    assert expired["reason_code"] == "RECOVERY_AFTER_DEADLINE"
    assert health_payload_operational(expired) is False
    assert ProdSmokeRunner._strict_health_errors(expired)


def test_observation_reader_preserves_boundary_operational_fields(tmp_path):
    boundary = 600_000
    payload = report_payload(boundary + 1, stored_open_ms=boundary - 120_000)
    path = tmp_path / "latest_health.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    observed = _read_health(
        path, datetime.fromtimestamp((boundary + 1) / 1000, UTC),
    )
    assert observed["current"] is True
    assert observed["overall_status"] == "OK"
    assert observed["operational"] is observed["ready"] is True
    assert observed["acceptance_blocking"] is False
    assert observed["reason_code"] == "BOUNDARY_WITHIN_GRACE"
    assert observed["within_grace_count"] == 1


def test_unknown_new_state_fails_closed_for_new_and_old_readers():
    assert health_payload_operational({
        "overall_status": "OK",
        "operational": False,
        "ready": False,
        "reason_code": "UNKNOWN_HEALTH_STATE",
    }) is False
    assert health_payload_operational({
        "overall_status": "UNKNOWN_NEW_STATE",
    }) is False
