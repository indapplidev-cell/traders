from tests.test_engine_orchestrator_01_daemon_once_mode import Detector, Gate, Runner
from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon
from tests.engine_orchestrator_01_helpers import config


class NoWriteStore:
    def reserve(self, *args, **kwargs): raise AssertionError("dry-run wrote")
    def finish(self, *args, **kwargs): raise AssertionError("dry-run wrote")


def test_dry_run_does_not_reserve_or_run(tmp_path):
    daemon = OrchestratorDaemon(config(health_report_path=tmp_path / "health.json"), Detector(), Gate(), Runner(), NoWriteStore())
    assert daemon.run(continuous=False, dry_run=True)[0]["dry_run"] is True
