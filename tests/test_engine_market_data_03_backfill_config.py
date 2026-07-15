import pytest

from app.engine_market_data.historical_backfill_config import DEFAULT_BACKFILL_LIMITS, HistoricalBackfillConfig


def test_default_limits_and_safety_policies():
    assert DEFAULT_BACKFILL_LIMITS == {"1m": 10_000, "5m": 10_000, "15m": 10_000,
                                       "1h": 5_000, "4h": 3_000, "1d": 1_500}
    config = HistoricalBackfillConfig()
    assert config.backfill_limits == DEFAULT_BACKFILL_LIMITS
    assert config.utc_only and config.store_only_closed_candles
    with pytest.raises(ValueError):
        HistoricalBackfillConfig(utc_only=False)

