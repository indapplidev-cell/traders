from app.engine_market_data.boundary_scheduler import BoundaryEvent
from app.engine_market_data.db_sync_config import DBSyncConfig
from app.engine_market_data.multi_timeframe_sync import MultiTimeframeSync
from engine_market_data_02_helpers import MemoryRepository, Rest, candle


def test_15m_missing_only_and_noop():
    available = [candle("15m", 0)] + [candle("5m", v) for v in range(0, 900_000, 300_000)] + [candle("1m", v) for v in range(0, 900_000, 60_000)]
    repo, rest = MemoryRepository(), Rest(available)
    sync = MultiTimeframeSync(repo, rest, None, DBSyncConfig(["BTCUSDT"]))
    event = BoundaryEvent("15m", 0, 899_999, 902_000)
    report = sync.sync_boundary("BTCUSDT", event)
    assert report.status == "SUCCESS" and report.expected_candles == 19 and report.missing_after == 0
    calls = len(rest.calls)
    report = sync.sync_boundary("BTCUSDT", event)
    assert report.status == "NOOP_ALREADY_SYNCED" and len(rest.calls) == calls
