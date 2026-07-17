import pytest

from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import routed


@pytest.mark.parametrize(("source", "expected"), [
    ("NO_DECISION", "NO_PLAN"), ("WAIT", "WAIT"), ("REJECT", "NO_PLAN"), ("ERROR", "ERROR")])
def test_source_status_routing(source, expected):
    assert PaperRunner().process_risk_decision(routed(source)).paper_status == expected
