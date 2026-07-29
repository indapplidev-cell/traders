from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from app.engine_paper.fill_simulator import (
    FillSimulationOutcome,
    authoritative_next_1m_open_after_command_boundary,
    simulate_paper_fill,
)
from app.engine_execution.paper_idempotency import order_idempotency_key
from app.engine_safety import PaperOrderState
from tests.paper_fill_simulator.conftest import (
    COMMAND_BOUNDARY_MS,
    EXPECTED_CLOSE_BOUNDARY_MS,
)


def test_exclusive_command_boundary_is_the_next_candle_open():
    assert (
        authoritative_next_1m_open_after_command_boundary(COMMAND_BOUNDARY_MS)
        == COMMAND_BOUNDARY_MS
    )


@pytest.mark.parametrize(
    "boundary",
    [-1, True, 1, COMMAND_BOUNDARY_MS - 1, COMMAND_BOUNDARY_MS + 1],
)
def test_unaligned_or_invalid_command_boundary_is_rejected(boundary):
    with pytest.raises(ValueError):
        authoritative_next_1m_open_after_command_boundary(boundary)


def test_exact_next_closed_candle_fills(request_factory):
    result = simulate_paper_fill(request_factory())
    assert result.outcome is FillSimulationOutcome.FILLED
    assert result.fill is not None
    assert result.fill.source_closed_until_ms == EXPECTED_CLOSE_BOUNDARY_MS


def test_snapshot_equal_to_close_boundary_is_eligible(request_factory):
    result = simulate_paper_fill(
        request_factory(market_snapshot_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS)
    )
    assert result.successful


@pytest.mark.parametrize(
    "snapshot",
    [COMMAND_BOUNDARY_MS, EXPECTED_CLOSE_BOUNDARY_MS - 1],
)
def test_snapshot_before_close_is_not_yet_eligible(
    request_factory,
    candle_factory,
    snapshot,
):
    candle = candle_factory(observed_closed_until_ms=snapshot)
    result = simulate_paper_fill(
        request_factory(
            candles=(candle,),
            market_snapshot_closed_until_ms=snapshot,
        )
    )
    assert result.outcome is FillSimulationOutcome.NOT_YET_ELIGIBLE
    assert result.fill is None


def test_exact_candle_not_closed_is_rejected(request_factory, candle_factory):
    result = simulate_paper_fill(
        request_factory(candles=(candle_factory(is_closed=False),))
    )
    assert result.outcome is FillSimulationOutcome.CANDLE_NOT_CLOSED


def test_previous_candle_is_never_used(request_factory, candle_factory):
    previous = candle_factory(
        open_time_ms=COMMAND_BOUNDARY_MS - 60_000,
        close_boundary_ms=COMMAND_BOUNDARY_MS,
        observed_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS,
    )
    result = simulate_paper_fill(request_factory(candles=(previous,)))
    assert result.outcome is FillSimulationOutcome.ELIGIBLE_CANDLE_MISSING
    assert result.fill is None


def test_later_closed_candle_proves_gap_and_is_never_used(
    request_factory,
    candle_factory,
):
    later = candle_factory(
        open_time_ms=COMMAND_BOUNDARY_MS + 60_000,
        close_boundary_ms=EXPECTED_CLOSE_BOUNDARY_MS + 60_000,
        observed_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS + 60_000,
    )
    result = simulate_paper_fill(
        request_factory(
            candles=(later,),
            market_snapshot_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS + 60_000,
        )
    )
    assert result.outcome is FillSimulationOutcome.MARKET_DATA_GAP
    assert result.fill is None


def test_absent_exact_candle_before_close_is_not_yet_available(request_factory):
    result = simulate_paper_fill(
        request_factory(
            candles=(),
            market_snapshot_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS - 1,
        )
    )
    assert result.outcome is FillSimulationOutcome.NOT_YET_ELIGIBLE


def test_absent_exact_candle_after_close_is_missing(request_factory):
    result = simulate_paper_fill(request_factory(candles=()))
    assert result.outcome is FillSimulationOutcome.ELIGIBLE_CANDLE_MISSING


def test_later_unclosed_future_candle_is_rejected(request_factory, candle_factory):
    future = candle_factory(
        open_time_ms=COMMAND_BOUNDARY_MS + 60_000,
        close_boundary_ms=EXPECTED_CLOSE_BOUNDARY_MS + 60_000,
        is_closed=False,
        observed_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS,
    )
    result = simulate_paper_fill(request_factory(candles=(future,)))
    assert result.outcome is FillSimulationOutcome.FUTURE_DATA_REJECTED


def test_valid_exact_plus_future_candle_rejects_lookahead(
    request_factory,
    candle_factory,
):
    exact = candle_factory()
    future = candle_factory(
        open_time_ms=COMMAND_BOUNDARY_MS + 60_000,
        close_boundary_ms=EXPECTED_CLOSE_BOUNDARY_MS + 60_000,
        is_closed=False,
        observed_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS,
    )
    result = simulate_paper_fill(request_factory(candles=(future, exact)))
    assert result.outcome is FillSimulationOutcome.FUTURE_DATA_REJECTED
    assert result.fill is None


def test_selected_candle_observed_after_request_snapshot_is_future_data(
    request_factory,
    candle_factory,
):
    candle = candle_factory(
        observed_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS + 60_000
    )
    result = simulate_paper_fill(request_factory(candles=(candle,)))
    assert result.outcome is FillSimulationOutcome.FUTURE_DATA_REJECTED


def test_incomplete_previous_candle_is_not_silently_ignored(
    request_factory,
    candle_factory,
):
    previous = candle_factory(
        open_time_ms=COMMAND_BOUNDARY_MS - 60_000,
        close_boundary_ms=COMMAND_BOUNDARY_MS,
        is_closed=False,
    )
    result = simulate_paper_fill(
        request_factory(candles=(previous, candle_factory()))
    )
    assert result.outcome is FillSimulationOutcome.CANDLE_NOT_CLOSED


def test_identical_duplicate_is_not_silently_deduplicated(
    request_factory,
    candle_factory,
):
    candle = candle_factory()
    result = simulate_paper_fill(request_factory(candles=(candle, candle)))
    assert result.outcome is FillSimulationOutcome.DUPLICATE_CANDLE


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("open_price", Decimal("100.1")),
        ("high_price", Decimal("106")),
        ("low_price", Decimal("94")),
        ("close_price", Decimal("102")),
    ],
)
def test_conflicting_duplicate_is_rejected(
    request_factory,
    candle_factory,
    field_name,
    value,
):
    first = candle_factory()
    second = candle_factory(**{field_name: value})
    result = simulate_paper_fill(request_factory(candles=(first, second)))
    assert result.outcome is FillSimulationOutcome.CANDLE_CONFLICT


def test_candidate_order_does_not_change_gap_outcome(request_factory, candle_factory):
    previous = candle_factory(
        open_time_ms=COMMAND_BOUNDARY_MS - 60_000,
        close_boundary_ms=COMMAND_BOUNDARY_MS,
    )
    later = candle_factory(
        open_time_ms=COMMAND_BOUNDARY_MS + 60_000,
        close_boundary_ms=EXPECTED_CLOSE_BOUNDARY_MS + 60_000,
        observed_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS + 60_000,
    )
    first = simulate_paper_fill(
        request_factory(
            candles=(previous, later),
            market_snapshot_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS + 60_000,
        )
    )
    second = simulate_paper_fill(
        request_factory(
            candles=(later, previous),
            market_snapshot_closed_until_ms=EXPECTED_CLOSE_BOUNDARY_MS + 60_000,
        )
    )
    assert first == second
    assert first.outcome is FillSimulationOutcome.MARKET_DATA_GAP


def test_wrong_candle_symbol_is_rejected(request_factory, candle_factory):
    result = simulate_paper_fill(
        request_factory(candles=(candle_factory(symbol="ETHUSDT"),))
    )
    assert result.outcome is FillSimulationOutcome.SYMBOL_MISMATCH


@pytest.mark.parametrize(
    "state",
    [
        PaperOrderState.CREATED,
        PaperOrderState.VALIDATED,
        PaperOrderState.REJECTED,
        PaperOrderState.FAILED,
    ],
)
def test_only_open_order_is_eligible(request_factory, order_factory, state):
    order = order_factory(state=state)
    result = simulate_paper_fill(request_factory(order=order))
    assert result.outcome is FillSimulationOutcome.INVALID_ORDER_STATE


def test_filled_order_is_not_eligible(request_factory, order_factory):
    order = order_factory(
        state=PaperOrderState.FILLED,
        filled_quantity=Decimal("2"),
        average_fill_price=Decimal("100"),
        total_fees=Decimal("0.2"),
        applied_fill_id="fill:already-applied",
    )
    result = simulate_paper_fill(request_factory(order=order))
    assert result.outcome is FillSimulationOutcome.INVALID_ORDER_STATE


def test_order_command_identity_mismatch_is_rejected(
    request_factory,
    order_factory,
):
    order = order_factory(command_id="command:other")
    result = simulate_paper_fill(request_factory(order=order))
    assert result.outcome is FillSimulationOutcome.IDEMPOTENCY_CONFLICT


def test_fill_role_must_match_order_identity(request_factory, order_factory):
    order = order_factory(
        idempotency_key=order_idempotency_key("command:fill:1", "ENTRY")
    )
    result = simulate_paper_fill(
        request_factory(order=order, role="CLOSE")
    )
    assert result.outcome is FillSimulationOutcome.IDEMPOTENCY_CONFLICT
    assert result.field_path == "order.idempotency_key"


def test_order_symbol_mismatch_is_rejected(request_factory, order_factory):
    order = order_factory(symbol="ETHUSDT")
    result = simulate_paper_fill(request_factory(order=order))
    assert result.outcome is FillSimulationOutcome.SYMBOL_MISMATCH


def test_policy_command_identity_mismatch_is_rejected(request_factory, policy_factory):
    policy = policy_factory(simulation_policy_id="simulation:other:v1")
    result = simulate_paper_fill(request_factory(policy=policy))
    assert result.outcome is FillSimulationOutcome.INVALID_POLICY


def test_expired_one_millisecond_before_close_is_rejected(
    request_factory,
    command_factory,
):
    command = command_factory(valid_until_ms=EXPECTED_CLOSE_BOUNDARY_MS - 1)
    result = simulate_paper_fill(request_factory(command=command))
    assert result.outcome is FillSimulationOutcome.COMMAND_EXPIRED


def test_equal_validity_close_boundary_is_accepted(request_factory, command_factory):
    command = command_factory(valid_until_ms=EXPECTED_CLOSE_BOUNDARY_MS)
    result = simulate_paper_fill(request_factory(command=command))
    assert result.outcome is FillSimulationOutcome.FILLED


def test_unaligned_command_boundary_fails_closed(request_factory, command_factory):
    command = command_factory(
        closed_until_ms=COMMAND_BOUNDARY_MS + 1,
        valid_until_ms=EXPECTED_CLOSE_BOUNDARY_MS + 1,
    )
    with pytest.raises(ValueError, match="aligned 1m boundary"):
        request_factory(command=command)
