from types import SimpleNamespace

from app.engine_orchestrator.pipeline_runner import PipelineRunner
from tests.engine_orchestrator_01_helpers import BOUNDARY, config


class UnsafeRepo:
    def get_candles(self, symbol, timeframe, **kwargs):
        last_open = kwargs["end_time_ms"]
        return [SimpleNamespace(
            open_time_ms=last_open, close_time_ms=last_open + 1,
            is_closed=False, source="postgres",
        )]


def forbidden(_):
    raise AssertionError("downstream started before snapshot contract passed")


def test_unclosed_snapshot_is_terminal_before_any_downstream_call():
    runner = PipelineRunner(
        config(required_timeframes=("15m",), minimum_windows={"15m": 1}), UnsafeRepo(),
        analysis_runner=forbidden, setup_runner=forbidden, strategy_runner=forbidden,
        risk_runner=forbidden, paper_runner=forbidden,
    )
    result = runner.run("BTCUSDT", BOUNDARY)
    assert result.status == "SKIPPED_FRESHNESS_NOT_OK"
    assert result.error_code == "SNAPSHOT_CONTRACT_VIOLATION"
