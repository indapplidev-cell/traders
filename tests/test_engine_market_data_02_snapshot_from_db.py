from app.engine_market_data.market_data_snapshot import build_market_data_snapshot_from_db
from engine_market_data_02_helpers import MemoryRepository, candle


def test_db_snapshot_is_closed_only_causal_and_gap_aware():
    repo = MemoryRepository([candle("1m", 0), candle("1m", 120_000), candle("1m", 180_000, closed=False)])
    snapshot = build_market_data_snapshot_from_db(repo, "BTCUSDT", "1m", 3)
    assert [c.open_time_ms for c in snapshot.candles] == [0, 120_000]
    assert snapshot.has_gaps and not snapshot.future_bars_used and not snapshot.enough_data
