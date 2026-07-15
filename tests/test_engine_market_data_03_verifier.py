from app.engine_market_data.historical_backfill_planner import HistoricalBackfillPlanner
from app.engine_market_data.historical_backfill_verifier import HistoricalBackfillVerifier
from engine_market_data_03_helpers import MemoryRepository, candle


def test_verifier_reports_exact_gap_and_no_future_bars():
    task = HistoricalBackfillPlanner().build_task("BTCUSDT", "1m", 600_001, 3)
    result = HistoricalBackfillVerifier(MemoryRepository([candle(420_000), candle(540_000)])).verify_task(task)
    assert result.actual_count == 2 and result.missing_open_times == [480_000]
    assert result.has_gaps and not result.future_bars_used and result.closed_candle_only
    assert result.status == "INCOMPLETE"

