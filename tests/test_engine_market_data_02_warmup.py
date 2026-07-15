from app.engine_market_data.db_sync_config import DBSyncConfig
from app.engine_market_data.multi_timeframe_sync import MultiTimeframeSync
from engine_market_data_02_helpers import MemoryRepository, Rest, candle


def test_warmup_downloads_only_missing_latest_closed_window():
    existing = candle("1m", 120_000, source="websocket")
    rest = Rest([candle("1m", 0), candle("1m", 60_000)], now_ms=180_002)
    config = DBSyncConfig(["BTCUSDT"], enabled_timeframes=["1m"], warmup_limits={"1m": 3})
    report = MultiTimeframeSync(MemoryRepository([existing]), rest, None, config).warmup_symbol("BTCUSDT")
    assert report.existing_candles == 1 and report.downloaded_candles == 2
    assert len(rest.calls) == 1 and rest.calls[0]["end_time_ms"] == 119_999
