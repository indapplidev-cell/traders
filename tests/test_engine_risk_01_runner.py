import asyncio

import pytest

from app.engine_risk.risk_runner import RiskRunner
from tests.engine_risk_01_helpers import strategy_decision


def test_runner_accepts_only_strategy_decision():
    with pytest.raises(TypeError):
        RiskRunner().process_strategy_decision({})


def test_async_runner_yields_decisions():
    async def collect():
        return [row async for row in RiskRunner().run_on_strategy_decisions([strategy_decision()])]
    assert len(asyncio.run(collect())) == 1
