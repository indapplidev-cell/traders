import pytest

from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


@pytest.mark.parametrize("direction", ["NEUTRAL", "NONE"])
def test_non_directional_source_is_not_ready(direction):
    assert PaperRunner().process_risk_decision(
        risk_decision(direction_hint=direction)).paper_status == "REJECT"
