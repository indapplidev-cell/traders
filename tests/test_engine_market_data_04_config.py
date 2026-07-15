import pytest
from app.engine_market_data.continuous_sync_config import ContinuousSyncConfig


def test_defaults_and_validation():
    config = ContinuousSyncConfig()
    assert config.warmup_depths["1m"] == 1440
    with pytest.raises(ValueError):
        ContinuousSyncConfig(timeframes=["30m"])
