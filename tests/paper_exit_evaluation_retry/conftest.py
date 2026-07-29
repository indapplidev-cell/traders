from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.engine_paper.exit_evaluation_service import PaperExitEvaluationRequest
from app.engine_paper.exit_evaluator import PaperSafetyExitDirective
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_safety import ExecutionMode
from app.db.paper_mappings import (
    paper_command_to_orm_values,
    paper_exit_cursor_to_orm_values,
    paper_fill_to_orm_values,
    paper_order_to_orm_values,
    paper_position_to_orm_values,
)
from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitEvaluationCursorRecord,
    PaperFillRecord,
    PaperOrderRecord,
    PaperPositionRecord,
    PaperSimulationPolicyRecord,
)
from tests.paper_close_causal_cursor_remediation.conftest import (
    Q,
    T1,
    causal_graph,
    make_candle,
    make_cursor,
)
from tests.paper_repository.conftest import (
    paper_session_factory,
    repository_postgres_engine,
)


T2 = T1 + 60_000
OPERATION_AT = datetime.fromtimestamp(T2 / 1000, tz=timezone.utc)


def seed_exit_graph(factory, graph):
    cursor = make_cursor(graph)
    policy = graph["policy"]
    command = graph["command"]
    with factory() as session:
        if session.get(
            PaperSimulationPolicyRecord,
            (policy.simulation_policy_id, 1),
        ) is None:
            session.add(PaperSimulationPolicyRecord(
                policy_id=policy.simulation_policy_id,
                policy_version=1,
                status="ACTIVE",
                price_source=policy.price_source.value,
                timeframe=policy.timeframe,
                latency_candles=policy.latency_candles,
                slippage_bps=policy.slippage_bps,
                fee_bps=policy.fee_bps,
                partial_fill_enabled=policy.partial_fill_enabled,
                future_data_allowed=policy.future_data_allowed,
                intrabar_conflict_policy=policy.intrabar_conflict_policy.value,
                configuration_fingerprint=command.configuration_fingerprint,
                created_at=command.created_at,
                retired_at=None,
            ))
        session.add(
            PaperExecutionCommandRecord(**paper_command_to_orm_values(command))
        )
        session.flush()
        session.add(
            PaperOrderRecord(
                **paper_order_to_orm_values(
                    graph["filled_entry_order"], order_role="ENTRY"
                )
            )
        )
        session.flush()
        session.add(
            PaperFillRecord(
                **paper_fill_to_orm_values(
                    graph["entry_fill"], fill_role="ENTRY"
                )
            )
        )
        session.flush()
        session.add(
            PaperPositionRecord(
                **paper_position_to_orm_values(graph["position"])
            )
        )
        session.flush()
        session.add(
            PaperExitEvaluationCursorRecord(
                **paper_exit_cursor_to_orm_values(cursor)
            )
        )
        session.commit()
    return cursor


def make_request(graph, cursor, *, trigger=None, safety=None, **changes):
    candle = make_candle(
        T1,
        low_price=Decimal("90") if trigger == "STOP" else Decimal("95"),
        high_price=Decimal("110") if trigger == "TARGET" else Decimal("105"),
        observed_closed_until_ms=T2,
    )
    values = {
        "position_id": graph["position"].position_id,
        "expected_position_version": graph["position"].version,
        "cursor_id": cursor.cursor_id,
        "expected_cursor_version": cursor.version,
        "expected_cursor_from_closed_until_ms": (
            cursor.last_evaluated_closed_until_ms
        ),
        "source_command_id": graph["command"].command_id,
        "entry_order_id": graph["position"].entry_order_id,
        "entry_fill_id": graph["position"].entry_fill_id,
        "candles": (candle,),
        "market_snapshot_closed_until_ms": T2,
        "safety_directive": safety,
        "evaluation_policy_id": cursor.evaluation_policy_id,
        "execution_mode": ExecutionMode.PAPER,
        "explicit_paper_authorization": True,
        "exit_decision_id": "exit:evaluation:1",
        "close_order_id": "order:evaluation:close:1",
        "exit_event_id": "event:evaluation:exit:1",
        "close_order_created_event_id": "event:evaluation:close:created:1",
        "close_order_validated_event_id": "event:evaluation:close:validated:1",
        "close_order_opened_event_id": "event:evaluation:close:opened:1",
        "journal_entry_ids": (
            "event:evaluation:close:created:1",
            "event:evaluation:close:validated:1",
            "event:evaluation:close:opened:1",
            "event:evaluation:exit:1",
        ),
        "close_execution_fill_id": "fill:evaluation:close:1",
        "close_execution_order_event_id": "event:evaluation:fill-order:1",
        "close_execution_position_event_id": "event:evaluation:position-closed:1",
        "close_execution_journal_entry_ids": (
            "journal:evaluation:fill-order:1",
            "journal:evaluation:position-closed:1",
        ),
        "price_quantum": Q,
        "fee_quantum": Q,
        "quote_asset": "USDT",
        "created_at": OPERATION_AT,
        "correlation_id": "correlation:evaluation:1",
        "causation_id": "causation:evaluation:1",
    }
    values.update(changes)
    return PaperExitEvaluationRequest(**values)


def make_safety(graph, boundary=T2, **changes):
    values = {
        "directive_id": "safety:evaluation:1",
        "version": 1,
        "position_id": graph["position"].position_id,
        "symbol": graph["position"].symbol,
        "side": graph["position"].side,
        "effective_closed_until_ms": boundary,
        "issued_at": datetime.fromtimestamp(T1 / 1000, tz=timezone.utc),
        "valid_until_ms": T2 + 600_000,
        "final_safety_authorization": True,
        "reason": "operator-risk-stop",
        "correlation_id": "correlation:safety:evaluation:1",
        "causation_id": "causation:safety:evaluation:1",
        "mode": ExecutionMode.PAPER,
    }
    values.update(changes)
    return PaperSafetyExitDirective(**values)


@pytest.fixture
def exit_service_factory(paper_session_factory):
    return lambda: PaperUnitOfWork(paper_session_factory)
