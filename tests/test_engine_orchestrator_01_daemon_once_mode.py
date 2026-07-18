from types import SimpleNamespace

from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon
from app.engine_orchestrator.pipeline_result import PipelineResult
from tests.engine_orchestrator_01_helpers import BOUNDARY, config


class Detector:
    def get_unprocessed_closed_windows(self, symbol): return [SimpleNamespace(timeframe="15m", closed_until_ms=BOUNDARY)]
class Gate:
    def check(self, symbol, boundary, **kwargs):
        return SimpleNamespace(
            allowed=True, status="READY", classification="READY", reasons=(),
            timeframe_statuses={}, missing_timeframes=(), payload=lambda: {},
        )
class Runner:
    def run(self, symbol, boundary): return PipelineResult(symbol, "15m", boundary)
class Store:
    def claim_due_waiting(self, **kwargs): return []
    def reserve(self, *args, **kwargs): return "run"
    def get_claim(self, run_id):
        from datetime import datetime, timezone
        from app.engine_orchestrator.pipeline_result_store import ClaimedWindow
        return ClaimedWindow(run_id, "BTCUSDT", "15m", BOUNDARY, datetime.now(timezone.utc), 0, False)
    def mark_running(self, *args, **kwargs): return True
    def finish(self, *args, **kwargs): pass


def test_once_exits_after_one_cycle(tmp_path):
    daemon = OrchestratorDaemon(config(health_report_path=tmp_path / "health.json"), Detector(), Gate(), Runner(), Store())
    assert len(daemon.run(continuous=False)) == 1
    assert daemon.state.cycles == 1
