from app.engine_observation.pipeline_funnel_analyzer import analyze_funnel
from tests.engine_observation_01_helpers import run


def test_funnel_distributions_include_required_outcomes():
    value = analyze_funnel([run()], 1)
    assert value["funnel"]["paper_result"] == 1
    assert value["distributions"]["final_result"]["PAPER_PLAN_READY"] == 0
    assert value["distributions"]["final_result"]["NO_PLAN"] == 1
