from app.engine_orchestrator.pipeline_runner import PipelineRunner
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo, component, config, outputs


def test_typed_no_action_chain_finishes_without_fabrication():
    values = outputs()
    result = PipelineRunner(config(), CandleRepo(), analysis_runner=component(values[0]),
                            setup_runner=component(values[1]), strategy_runner=component(values[2]),
                            risk_runner=component(values[3]), paper_runner=component(values[4])).run("BTCUSDT", BOUNDARY)
    assert result.final_result == "NO_PLAN"
    assert result.safety_counters.has_violation is False
