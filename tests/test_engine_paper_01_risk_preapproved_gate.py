from app.engine_paper.paper_runner import PaperRunner
from tests.engine_paper_01_helpers import risk_decision


def test_missing_preapproval_yields_no_plan():
    source = risk_decision()
    object.__setattr__(source, "risk_pre_approved", False)
    assert PaperRunner().process_risk_decision(source).paper_status == "NO_PLAN"
