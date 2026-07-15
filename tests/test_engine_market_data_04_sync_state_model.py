from app.engine_market_data.continuous_sync_state import ALLOWED_SYNC_STATUSES, SyncStateUpdate


def test_allowed_statuses_and_values():
    assert "RECOVERING" in ALLOWED_SYNC_STATUSES
    assert SyncStateUpdate("BTCUSDT", "1m", "test", status="OK").values()["status"] == "OK"
