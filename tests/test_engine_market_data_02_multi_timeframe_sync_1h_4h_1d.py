import pytest
from app.engine_market_data.boundary_scheduler import BoundaryEvent
from app.engine_market_data.db_sync_config import DBSyncConfig
from app.engine_market_data.multi_timeframe_sync import MultiTimeframeSync
from engine_market_data_02_helpers import MemoryRepository, Rest, candle


@pytest.mark.parametrize("timeframe,duration", [("1h", 3_600_000), ("4h", 14_400_000), ("1d", 86_400_000)])
def test_slow_boundary_recovers_one(timeframe, duration):
    repo, rest = MemoryRepository(), Rest([candle(timeframe, 0)])
    report = MultiTimeframeSync(repo, rest, None, DBSyncConfig(["BTCUSDT"])).sync_boundary("BTCUSDT", BoundaryEvent(timeframe, 0, duration - 1, duration + 2_000))
    assert report.expected_candles == report.downloaded_candles == 1 and report.status == "SUCCESS"
