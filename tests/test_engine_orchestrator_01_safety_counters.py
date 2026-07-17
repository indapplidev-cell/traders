from types import SimpleNamespace

from app.engine_orchestrator.pipeline_runner import PipelineRunner
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo, component, config


def test_forbidden_counter_fails_run():
    analysis = SimpleNamespace(status="ANALYZED", action="NO_ACTION", future_bars_used=True, reason_codes=[])
    dummy = SimpleNamespace(status="NO_SETUP", reason_codes=[])
    result = PipelineRunner(config(), CandleRepo(), analysis_runner=component(analysis),
                            setup_runner=component(dummy), strategy_runner=component(SimpleNamespace(decision_status="NO_DECISION")),
                            risk_runner=component(SimpleNamespace(risk_status="NO_DECISION")),
                            paper_runner=component(SimpleNamespace(paper_status="NO_PLAN"))).run("BTCUSDT", BOUNDARY)
    assert result.status == "ERROR"
    assert result.error_code == "SAFETY_VIOLATION"
