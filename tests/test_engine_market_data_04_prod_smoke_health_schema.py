from app.engine_market_data.prod_smoke import ProdSmokeRunner, validate_health_payload


def test_health_schema_requires_operational_snapshot_and_outcome_context():
    payload = {
        "generated_at": "2026-07-15T00:00:00Z", "daemon_instance_id": "smoke-1",
        "overall_status": "OK", "snapshots": [{
            "symbol": "BTCUSDT", "timeframe": "15m", "expected_open_time_ms": 1000,
            "stored_open_time_ms": 1000, "freshness_lag_candles": 0, "status": "OK",
            "missing_count": 0, "last_success_at": "2026-07-15T00:00:00Z", "last_error": None,
        }],
    }
    assert validate_health_payload(payload) == []


def test_health_schema_rejects_empty_snapshots():
    errors = validate_health_payload({"generated_at": "x", "daemon_instance_id": "x",
                                      "overall_status": "OK", "snapshots": []})
    assert "snapshots must be a non-empty list" in errors


def test_strict_smoke_health_rejects_ok_snapshot_with_hidden_last_error():
    payload = {
        "generated_at": "2026-07-15T00:00:00Z", "daemon_instance_id": "smoke-1",
        "overall_status": "OK", "snapshots": [{
            "symbol": "BTCUSDT", "timeframe": "15m", "expected_open_time_ms": 1000,
            "stored_open_time_ms": 1000, "freshness_lag_candles": 0, "status": "OK",
            "missing_count": 0, "last_success_at": "2026-07-15T00:00:00Z",
            "last_error": "number of parameters must be between 0 and 65535",
        }],
    }
    errors = ProdSmokeRunner._strict_health_errors(payload)
    assert any("reports last_error despite status=OK" in error for error in errors)
