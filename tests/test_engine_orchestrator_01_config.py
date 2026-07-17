import pytest

from app.engine_orchestrator.orchestrator_config import OrchestratorConfig


def test_defaults_and_validation():
    config = OrchestratorConfig()
    assert config.primary_timeframe == "15m"
    assert config.max_catchup_windows == 4
    with pytest.raises(ValueError):
        OrchestratorConfig(primary_timeframe="1m")
