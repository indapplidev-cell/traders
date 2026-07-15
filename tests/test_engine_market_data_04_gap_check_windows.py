from app.engine_market_data.continuous_sync_config import DEFAULT_GAP_CHECK_WINDOWS


def test_gap_windows_match_contract():
    assert DEFAULT_GAP_CHECK_WINDOWS == {"1m": 360, "5m": 288, "15m": 192, "1h": 168, "4h": 180, "1d": 365}
