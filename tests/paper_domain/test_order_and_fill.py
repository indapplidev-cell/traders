from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import inspect

import pytest

from app.engine_execution.paper_models import PaperFill, PaperOrder
from app.engine_execution.paper_state_machine import (
    create_paper_order,
    fill_order,
    transition_order,
)
from app.engine_safety import (
    PaperDomainError,
    PaperEventType,
    PaperOrderState,
    PaperReasonCode,
    PaperSide,
)
from tests.paper_domain.conftest import NOW, make_created_order, make_fill


ALLOWED_NON_FILL = [
    (PaperOrderState.CREATED, PaperOrderState.VALIDATED),
    (PaperOrderState.CREATED, PaperOrderState.REJECTED),
    (PaperOrderState.CREATED, PaperOrderState.FAILED),
    (PaperOrderState.VALIDATED, PaperOrderState.OPEN),
    (PaperOrderState.VALIDATED, PaperOrderState.REJECTED),
    (PaperOrderState.VALIDATED, PaperOrderState.FAILED),
    (PaperOrderState.OPEN, PaperOrderState.FAILED),
]
ALLOWED_GRAPH = set(ALLOWED_NON_FILL) | {(PaperOrderState.OPEN, PaperOrderState.FILLED)}
INVALID_GRAPH = [
    (source, target)
    for source in PaperOrderState
    for target in PaperOrderState
    if (source, target) not in ALLOWED_GRAPH
]


def test_order_creation_emits_typed_event(command_factory):
    result = create_paper_order(
        command_factory(),
        order_id="order:1",
        idempotency_key="paper:order:v1:key",
        occurred_at=NOW,
        event_id="event:create",
    )
    assert result.applied is True
    assert result.previous_order is None
    assert result.order.state is PaperOrderState.CREATED
    assert result.order.version == 0
    assert result.events[0].event_type is PaperEventType.PAPER_ORDER_CREATED


@pytest.mark.parametrize(("source", "target"), ALLOWED_NON_FILL)
def test_all_allowed_non_fill_transitions(order_factory, source, target):
    order = order_factory(source)
    result = transition_order(
        order,
        target,
        expected_version=order.version,
        occurred_at=NOW,
        event_id=f"event:{source.value.lower()}-{target.value.lower()}",
    )
    assert result.applied is True
    assert result.order.state is target
    assert result.order.version == order.version + 1
    assert result.previous_order is order


@pytest.mark.parametrize(("source", "target"), INVALID_GRAPH)
def test_all_invalid_transitions_fail_closed(order_factory, source, target):
    order = order_factory(source)
    with pytest.raises(PaperDomainError) as error:
        transition_order(
            order,
            target,
            expected_version=order.version,
            occurred_at=NOW,
            event_id="event:invalid",
        )
    assert error.value.reason_code in {
        PaperReasonCode.PAPER_ORDER_INVALID_TRANSITION,
        PaperReasonCode.PAPER_ORDER_TERMINAL,
    }


def test_open_to_filled_requires_full_fill(order_factory, fill_factory):
    order = order_factory(PaperOrderState.OPEN)
    result = fill_order(
        order,
        fill_factory(),
        expected_version=order.version,
        event_id="event:fill",
    )
    assert result.order.state is PaperOrderState.FILLED
    assert result.order.filled_quantity == result.order.requested_quantity
    assert result.order.version == order.version + 1
    assert result.events[0].event_type is PaperEventType.PAPER_ORDER_FILLED


def test_duplicate_fill_is_idempotent(order_factory, fill_factory):
    order = order_factory(PaperOrderState.OPEN)
    fill = fill_factory()
    filled = fill_order(order, fill, expected_version=order.version, event_id="event:fill").order
    replay = fill_order(filled, fill, expected_version=filled.version, event_id="event:fill-replay")
    assert replay.applied is False
    assert replay.order is filled
    assert replay.events == ()
    assert replay.reason_code is PaperReasonCode.PAPER_FILL_DUPLICATE


def test_different_fill_cannot_refill_terminal_order(order_factory, fill_factory):
    order = order_factory(PaperOrderState.OPEN)
    first = fill_factory()
    filled = fill_order(order, first, expected_version=order.version, event_id="event:fill").order
    with pytest.raises(PaperDomainError) as error:
        fill_order(
            filled,
            fill_factory(fill_id="fill:2"),
            expected_version=filled.version,
            event_id="event:fill-2",
        )
    assert error.value.reason_code is PaperReasonCode.PAPER_ORDER_TERMINAL


def test_partial_fill_rejected(order_factory, fill_factory):
    order = order_factory(PaperOrderState.OPEN)
    with pytest.raises(PaperDomainError) as error:
        fill_order(
            order,
            fill_factory(quantity=Decimal("1")),
            expected_version=order.version,
            event_id="event:partial",
        )
    assert error.value.reason_code is PaperReasonCode.PAPER_FILL_PARTIAL_UNSUPPORTED


@pytest.mark.parametrize(
    "state",
    [PaperOrderState.CREATED, PaperOrderState.VALIDATED, PaperOrderState.REJECTED, PaperOrderState.FAILED],
)
def test_non_open_order_cannot_fill(order_factory, fill_factory, state):
    order = order_factory(state)
    with pytest.raises(PaperDomainError):
        fill_order(
            order,
            fill_factory(),
            expected_version=order.version,
            event_id="event:bad-fill",
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"order_id": "order:other"},
        {"symbol": "ETHUSDT"},
        {"side": PaperSide.SHORT},
    ],
)
def test_fill_causal_mismatch_rejected(order_factory, fill_factory, changes):
    order = order_factory(PaperOrderState.OPEN)
    with pytest.raises(PaperDomainError) as error:
        fill_order(
            order,
            fill_factory(**changes),
            expected_version=order.version,
            event_id="event:mismatch",
        )
    assert error.value.reason_code is PaperReasonCode.PAPER_FILL_INVALID


def test_stale_order_version_rejected(order_factory):
    order = order_factory(PaperOrderState.CREATED)
    with pytest.raises(PaperDomainError) as error:
        transition_order(
            order,
            PaperOrderState.VALIDATED,
            expected_version=99,
            occurred_at=NOW,
        )
    assert error.value.reason_code is PaperReasonCode.PAPER_ORDER_INVALID_TRANSITION


def test_original_order_is_unchanged(order_factory):
    order = order_factory(PaperOrderState.CREATED)
    result = transition_order(
        order,
        PaperOrderState.VALIDATED,
        expected_version=0,
        occurred_at=NOW,
    )
    assert order.state is PaperOrderState.CREATED
    assert order.version == 0
    assert result.order is not order


def test_order_version_increments_once_per_transition(order_factory, fill_factory):
    created = order_factory(PaperOrderState.CREATED)
    validated = transition_order(
        created, PaperOrderState.VALIDATED, expected_version=0, occurred_at=NOW
    ).order
    opened = transition_order(
        validated, PaperOrderState.OPEN, expected_version=1, occurred_at=NOW
    ).order
    filled = fill_order(opened, fill_factory(), expected_version=2, event_id="event:fill").order
    assert [created.version, validated.version, opened.version, filled.version] == [0, 1, 2, 3]


def test_transition_timestamp_cannot_regress(order_factory):
    order = replace(order_factory(PaperOrderState.CREATED), updated_at=NOW + timedelta(seconds=1))
    with pytest.raises(PaperDomainError) as error:
        transition_order(
            order,
            PaperOrderState.VALIDATED,
            expected_version=0,
            occurred_at=NOW,
        )
    assert error.value.reason_code is PaperReasonCode.PAPER_INPUT_TIME_INVALID


def test_order_is_frozen(order_factory):
    order = order_factory(PaperOrderState.CREATED)
    with pytest.raises(FrozenInstanceError):
        order.version = 2


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("quantity", 2.0),
        ("quantity", Decimal("NaN")),
        ("quantity", Decimal("0")),
        ("price", 100.0),
        ("price", Decimal("Infinity")),
        ("price", Decimal("0")),
        ("fee_amount", 0.1),
        ("fee_amount", Decimal("NaN")),
        ("fee_amount", Decimal("-1")),
    ],
)
def test_invalid_fill_decimal_rejected(fill_factory, field_name, value):
    with pytest.raises(PaperDomainError):
        fill_factory(**{field_name: value})


def test_zero_fee_is_valid(fill_factory):
    assert fill_factory(fee_amount=Decimal("0")).fee_amount == Decimal("0")


def test_future_fill_rejected(fill_factory):
    with pytest.raises(PaperDomainError) as error:
        fill_factory(future_bars_used=True)
    assert error.value.reason_code is PaperReasonCode.PAPER_FILL_FUTURE_DATA


def test_fill_requires_utc(fill_factory):
    with pytest.raises(PaperDomainError):
        fill_factory(filled_at=datetime(2026, 7, 29, 6, 0))


def test_fill_is_frozen(fill_factory):
    fill = fill_factory()
    with pytest.raises(FrozenInstanceError):
        fill.price = Decimal("1")


def test_no_wall_clock_or_random_id_generation():
    source = inspect.getsource(create_paper_order) + inspect.getsource(transition_order) + inspect.getsource(fill_order)
    assert "datetime.now" not in source
    assert "utcnow" not in source
    assert "uuid4" not in source
    assert "random" not in source
