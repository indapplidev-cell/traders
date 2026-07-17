import pytest

from app.engine_paper.paper_config import PaperConfig
from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


@pytest.mark.parametrize("context", [
    {}, {"reference_close": 100},
    {"reference_close": 100, "causal_support_level": 95},
])
def test_missing_causal_primitive_yields_no_plan(context):
    assert PaperRunner().process_risk_decision(
        risk_decision(risk_context=context)).paper_status == "NO_PLAN"


def test_fallbacks_are_disabled_by_default():
    config = PaperConfig()
    assert not config.allow_fallback_stop and not config.allow_fallback_target
