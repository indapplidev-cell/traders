from sqlalchemy import select

from app.db.paper_models import PaperExitDecisionRecord, PaperPositionRecord
from app.engine_paper.exit_evaluation_service import (
    PaperExitEvaluationService,
    PaperExitServiceOutcome,
)
from app.engine_safety import PaperExitCause

from .conftest import make_request, make_safety, seed_exit_graph


def test_net_pnl_directive_persists_typed_irreversible_closing_decision(
    paper_session_factory, causal_graph, exit_service_factory
):
    cursor = seed_exit_graph(paper_session_factory, causal_graph)
    request = make_request(
        causal_graph,
        cursor,
        safety=make_safety(causal_graph, reason="NET_PNL_PROTECTION"),
    )
    result = PaperExitEvaluationService(
        exit_service_factory, paper_session_factory
    ).evaluate(request)

    assert result.outcome is PaperExitServiceOutcome.EXIT_PREPARED
    assert result.trigger.cause is PaperExitCause.NET_PNL_PROTECTION
    assert result.position_state.value == "CLOSING"
    assert result.close_execution_request is not None
    with paper_session_factory() as session:
        decision = session.scalar(select(PaperExitDecisionRecord))
        position = session.get(PaperPositionRecord, request.position_id)
        assert decision.cause == "NET_PNL_PROTECTION"
        assert decision.reason_code == "PAPER_EXIT_NET_PNL_PROTECTION_TRIGGERED"
        assert position.state == "CLOSING"
        assert position.exit_fill_id is None
