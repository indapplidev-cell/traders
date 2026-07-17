from app.engine_orchestrator.pipeline_runner import PipelineRunner
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo, component, config, outputs


def test_pipeline_preserves_all_module_outputs():
    analysis, setup, strategy, risk, paper = outputs(paper_status="PAPER_PLAN_READY")
    runner = PipelineRunner(config(), CandleRepo(), analysis_runner=component(analysis),
                            setup_runner=component(setup), strategy_runner=component(strategy),
                            risk_runner=component(risk), paper_runner=component(paper))
    result = runner.run("BTCUSDT", BOUNDARY)
    assert result.status == "COMPLETED"
    assert result.final_result == "PAPER_PLAN_READY"
    assert result.paper_payload["paper_status"] == "PAPER_PLAN_READY"
    assert all(call[2]["end_time_ms"] < BOUNDARY for call in runner.candle_repository.calls)
