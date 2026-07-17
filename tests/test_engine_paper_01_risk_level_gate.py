import pytest

from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


@pytest.mark.parametrize("level", ["HIGH", "BLOCKED", "UNKNOWN"])
def test_unsupported_risk_levels_do_not_create_ready_plan(level):
    source = risk_decision()
    object.__setattr__(source, "risk_level", level)
    assert PaperRunner().process_risk_decision(source).paper_status == "REJECT"
