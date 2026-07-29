from __future__ import annotations

from dataclasses import replace

import pytest

from app.engine_execution.paper_idempotency import order_transition_event_id
from app.engine_execution.paper_state_machine import (
    ORDER_TRANSITION_EVENT_TYPES,
    fill_order,
    transition_order,
)
from app.engine_safety.paper_domain import (
    PaperDomainError,
    PaperEventType,
    PaperOrderState,
    PaperReasonCode,
)
from tests.paper_domain.conftest import NOW, make_created_order, make_fill, make_order


EXPECTED = {
    (PaperOrderState.CREATED, PaperOrderState.VALIDATED):
        PaperEventType.PAPER_ORDER_VALIDATED,
    (PaperOrderState.CREATED, PaperOrderState.REJECTED):
        PaperEventType.PAPER_COMMAND_REJECTED,
    (PaperOrderState.CREATED, PaperOrderState.FAILED):
        PaperEventType.PAPER_EXECUTION_FAILED,
    (PaperOrderState.VALIDATED, PaperOrderState.OPEN):
        PaperEventType.PAPER_ORDER_OPENED,
    (PaperOrderState.VALIDATED, PaperOrderState.REJECTED):
        PaperEventType.PAPER_COMMAND_REJECTED,
    (PaperOrderState.VALIDATED, PaperOrderState.FAILED):
        PaperEventType.PAPER_EXECUTION_FAILED,
    (PaperOrderState.OPEN, PaperOrderState.FILLED):
        PaperEventType.PAPER_ORDER_FILLED,
    (PaperOrderState.OPEN, PaperOrderState.FAILED):
        PaperEventType.PAPER_EXECUTION_FAILED,
}


def test_transition_event_mapping_is_complete_and_exact():
    assert ORDER_TRANSITION_EVENT_TYPES == EXPECTED
    assert len(ORDER_TRANSITION_EVENT_TYPES) == 8


@pytest.mark.parametrize(
    ("source", "target", "event_type"),
    [
        (source, target, event_type)
        for (source, target), event_type in EXPECTED.items()
        if target is not PaperOrderState.FILLED
    ],
)
def test_every_nonfill_approved_transition_emits_exact_event(source, target, event_type):
    order = make_order(source)
    change = transition_order(
        order,
        target,
        expected_version=order.version,
        occurred_at=NOW,
    )
    assert len(change.events) == 1
    assert change.events[0].event_type is event_type
    assert change.events[0].aggregate_version == order.version + 1
    assert change.events[0].causation_id == order.order_id


def test_open_to_filled_emits_distinct_filled_event():
    order = make_order(PaperOrderState.OPEN)
    change = fill_order(
        order,
        make_fill(order_id=order.order_id),
        expected_version=order.version,
        event_id="event:filled:matrix",
    )
    assert change.events[0].event_type is PaperEventType.PAPER_ORDER_FILLED


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (source, target)
        for source in PaperOrderState
        for target in PaperOrderState
        if source not in {
            PaperOrderState.FILLED,
            PaperOrderState.REJECTED,
            PaperOrderState.FAILED,
        }
        and (source, target) not in EXPECTED
    ],
)
def test_every_unapproved_nonterminal_transition_is_rejected(source, target):
    order = make_order(source)
    with pytest.raises(PaperDomainError):
        transition_order(
            order,
            target,
            expected_version=order.version,
            occurred_at=NOW,
        )


@pytest.mark.parametrize(
    "source",
    [PaperOrderState.FILLED, PaperOrderState.REJECTED, PaperOrderState.FAILED],
)
@pytest.mark.parametrize("target", list(PaperOrderState))
def test_terminal_states_reject_every_followup_transition(source, target):
    order = make_order(source)
    with pytest.raises(PaperDomainError):
        transition_order(
            order,
            target,
            expected_version=order.version,
            occurred_at=NOW,
        )


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (PaperOrderState.CREATED, PaperOrderState.VALIDATED),
        (PaperOrderState.VALIDATED, PaperOrderState.OPEN),
        (PaperOrderState.CREATED, PaperOrderState.REJECTED),
        (PaperOrderState.CREATED, PaperOrderState.FAILED),
        (PaperOrderState.VALIDATED, PaperOrderState.REJECTED),
        (PaperOrderState.VALIDATED, PaperOrderState.FAILED),
        (PaperOrderState.OPEN, PaperOrderState.FAILED),
    ],
)
def test_default_transition_event_identity_is_deterministic(source, target):
    order = make_order(source)
    first = transition_order(
        order, target, expected_version=order.version, occurred_at=NOW
    )
    second = transition_order(
        order, target, expected_version=order.version, occurred_at=NOW
    )
    expected_id = order_transition_event_id(
        order_id=order.order_id,
        from_state=source,
        to_state=target,
        aggregate_version=order.version + 1,
    )
    assert first.events == second.events
    assert first.events[0].event_id == expected_id


def test_validated_and_opened_events_are_distinct_from_created():
    assert PaperEventType.PAPER_ORDER_VALIDATED is not PaperEventType.PAPER_ORDER_CREATED
    assert PaperEventType.PAPER_ORDER_OPENED is not PaperEventType.PAPER_ORDER_CREATED
    assert PaperEventType.PAPER_ORDER_VALIDATED is not PaperEventType.PAPER_ORDER_OPENED


def test_event_reason_codes_are_stable_and_distinct():
    created = make_created_order()
    validated = transition_order(
        created,
        PaperOrderState.VALIDATED,
        expected_version=0,
        occurred_at=NOW,
    )
    opened = transition_order(
        validated.order,
        PaperOrderState.OPEN,
        expected_version=1,
        occurred_at=NOW,
    )
    assert validated.events[0].reason_code is PaperReasonCode.PAPER_ORDER_VALIDATED
    assert opened.events[0].reason_code is PaperReasonCode.PAPER_ORDER_OPENED
