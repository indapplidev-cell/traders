from app.engine_market_data.historical_backfill_config import HistoricalBackfillConfig
from app.engine_market_data.historical_backfill_planner import HistoricalBackfillPlanner
from app.engine_market_data.historical_backfill_runner import HistoricalBackfillRunner
from app.engine_market_data.historical_backfill_verifier import HistoricalBackfillVerifier
from engine_market_data_03_helpers import MemoryRepository, RestClient, candle


def runner(repository, rest, *, limit=3):
    config = HistoricalBackfillConfig(symbols=["BTCUSDT"], timeframes=["1m"],
                                      backfill_limits={"1m": limit})
    return HistoricalBackfillRunner(repository, rest, HistoricalBackfillPlanner(),
                                    HistoricalBackfillVerifier(repository), config,
                                    now_ms=rest.now_ms)


def test_partial_database_downloads_only_missing_and_rerun_is_noop():
    rows = [candle(420_000), candle(480_000), candle(540_000)]
    repository = MemoryRepository([rows[0]])
    rest = RestClient(rows, now_ms=600_001)
    service = runner(repository, rest)
    first = service.backfill_symbol_timeframe("BTCUSDT", "1m")
    assert first.status == "SUCCESS" and first.missing_before == 2
    assert first.accepted_candles == 2 and len(rest.kline_calls) == 1
    assert rest.kline_calls[0]["start_time_ms"] == 480_000
    second = service.backfill_symbol_timeframe("BTCUSDT", "1m")
    assert second.status == "NOOP_ALREADY_FILLED"
    assert len(rest.kline_calls) == 1


def test_disjoint_missing_ranges_make_disjoint_calls():
    rows = [candle(value) for value in (360_000, 420_000, 480_000, 540_000)]
    repository = MemoryRepository([rows[1], rows[3]])
    rest = RestClient(rows, now_ms=600_001)
    report = runner(repository, rest, limit=4).backfill_symbol_timeframe("BTCUSDT", "1m")
    assert report.rest_ranges == 2 and report.rest_calls == 2
    assert [call["start_time_ms"] for call in rest.kline_calls] == [360_000, 480_000]

