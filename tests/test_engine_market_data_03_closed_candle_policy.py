from app.engine_market_data.historical_backfill_config import HistoricalBackfillConfig
from app.engine_market_data.historical_backfill_planner import HistoricalBackfillPlanner
from app.engine_market_data.historical_backfill_runner import HistoricalBackfillRunner
from app.engine_market_data.historical_backfill_verifier import HistoricalBackfillVerifier
from engine_market_data_03_helpers import MemoryRepository, RestClient, candle


def test_unclosed_and_unexpected_rest_candles_are_rejected_without_fillers():
    repository = MemoryRepository()
    class RestWithExtra(RestClient):
        def fetch_klines(self, **kwargs):
            self.kline_calls.append(kwargs)
            return self.rows

    rest = RestWithExtra([candle(540_000, closed=False), candle(600_000)], now_ms=600_001)
    config = HistoricalBackfillConfig(symbols=["BTCUSDT"], timeframes=["1m"],
                                      backfill_limits={"1m": 1})
    service = HistoricalBackfillRunner(repository, rest, HistoricalBackfillPlanner(),
                                       HistoricalBackfillVerifier(repository), config,
                                       now_ms=rest.now_ms)
    report = service.backfill_symbol_timeframe("BTCUSDT", "1m")
    assert report.rejected_unclosed_candles == 1
    assert report.rejected_unexpected_candles == 1
    assert report.accepted_candles == 0 and report.missing_after == 1
    assert repository.rows == {}
