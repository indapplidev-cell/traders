from app.engine_orchestrator.pipeline_runner import PipelineRunner
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo, component, config, outputs


def test_reject_path_is_preserved_by_supported_contracts():
    values = outputs(strategy_status="REJECT", risk_status="REJECT", paper_status="REJECT")
    result = PipelineRunner(config(), CandleRepo(), analysis_runner=component(values[0]),
                            setup_runner=component(values[1]), strategy_runner=component(values[2]),
                            risk_runner=component(values[3]), paper_runner=component(values[4])).run("BTCUSDT", BOUNDARY)
    assert (result.strategy_status, result.risk_status, result.paper_status) == ("REJECT", "REJECT", "REJECT")
    assert result.final_result == "REJECT"
