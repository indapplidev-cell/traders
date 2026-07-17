import asyncio

from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


def test_runner_accepts_only_risk_decisions_and_supports_async_iteration():
    runner = PaperRunner()
    try:
        runner.process_risk_decision({})  # type: ignore[arg-type]
        assert False
    except TypeError:
        pass

    async def collect():
        return [plan async for plan in runner.run_on_risk_decisions([risk_decision()])]
    assert asyncio.run(collect())[0].paper_status == "PAPER_PLAN_READY"
