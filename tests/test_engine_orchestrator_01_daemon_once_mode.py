from types import SimpleNamespace

from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon
from app.engine_orchestrator.pipeline_result import PipelineResult
from tests.engine_orchestrator_01_helpers import BOUNDARY, config


class Detector:
    def get_unprocessed_closed_windows(self, symbol): return [SimpleNamespace(timeframe="15m", closed_until_ms=BOUNDARY)]
class Gate:
    def check(self, symbol, boundary): return SimpleNamespace(allowed=True, status="OK", reasons=(), timeframe_statuses={})
class Runner:
    def run(self, symbol, boundary): return PipelineResult(symbol, "15m", boundary)
class Store:
    def reserve(self, *args, **kwargs): return "run"
    def finish(self, *args, **kwargs): pass


def test_once_exits_after_one_cycle(tmp_path):
    daemon = OrchestratorDaemon(config(health_report_path=tmp_path / "health.json"), Detector(), Gate(), Runner(), Store())
    assert len(daemon.run(continuous=False)) == 1
    assert daemon.state.cycles == 1
