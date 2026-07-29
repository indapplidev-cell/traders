from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from decimal import (
    Decimal,
    ROUND_DOWN,
    ROUND_HALF_EVEN,
    getcontext,
)
import inspect
import random

import pytest

from app.db.paper_mappings import paper_fill_to_orm_values
from app.engine_execution.paper_idempotency import (
    PAPER_IDEMPOTENCY_VERSION,
    simulated_fill_id,
    simulated_fill_idempotency_key,
)
from app.engine_execution.paper_models import PaperFill
from app.engine_paper.fill_simulator import (
    FillSimulationOutcome,
    FillSimulationResult,
    PaperFillRole,
    SimulatedTradeAction,
    adverse_fill_price,
    quote_fee_amount,
    resolve_trade_action,
    simulate_paper_fill,
)
from app.engine_safety import PaperSide
from tests.paper_fill_simulator.conftest import (
    COMMAND_BOUNDARY_MS,
    EXPECTED_CLOSE_BOUNDARY_MS,
)


@pytest.mark.parametrize(
    ("side", "role", "expected"),
    [
        (PaperSide.LONG, PaperFillRole.ENTRY, SimulatedTradeAction.BUY),
        (PaperSide.LONG, PaperFillRole.CLOSE, SimulatedTradeAction.SELL),
        (PaperSide.SHORT, PaperFillRole.ENTRY, SimulatedTradeAction.SELL),
        (PaperSide.SHORT, PaperFillRole.CLOSE, SimulatedTradeAction.BUY),
    ],
)
def test_exact_role_action_table(side, role, expected):
    assert resolve_trade_action(side, role) is expected


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        (SimulatedTradeAction.BUY, Decimal("100.02")),
        (SimulatedTradeAction.SELL, Decimal("99.98")),
    ],
)
def test_exact_two_bps_formula(action, expected):
    assert adverse_fill_price(
        Decimal("100"),
        Decimal("2"),
        Decimal("0.01"),
        action,
    ) == expected


@pytest.mark.parametrize("action", list(SimulatedTradeAction))
def test_zero_slippage_returns_exact_quantized_open(action):
    assert adverse_fill_price(
        Decimal("100.00"),
        Decimal("0"),
        Decimal("0.01"),
        action,
    ) == Decimal("100.00")


@pytest.mark.parametrize(
    ("action", "base", "quantum", "expected"),
    [
        (SimulatedTradeAction.BUY, Decimal("1.001"), Decimal("0.01"), Decimal("1.01")),
        (SimulatedTradeAction.SELL, Decimal("1.009"), Decimal("0.01"), Decimal("1.00")),
        (SimulatedTradeAction.BUY, Decimal("100"), Decimal("0.05"), Decimal("100.05")),
        (SimulatedTradeAction.SELL, Decimal("100"), Decimal("0.05"), Decimal("99.95")),
    ],
)
def test_adverse_rounding_direction(action, base, quantum, expected):
    result = adverse_fill_price(base, Decimal("2"), quantum, action)
    assert result == expected
    if action is SimulatedTradeAction.BUY:
        assert result >= base
    else:
        assert result <= base


@pytest.mark.parametrize(
    ("price", "quantity", "fee_bps", "quantum", "expected"),
    [
        (Decimal("100"), Decimal("2"), Decimal("10"), Decimal("0.01"), Decimal("0.20")),
        (Decimal("100.02"), Decimal("2"), Decimal("10"), Decimal("0.01"), Decimal("0.21")),
        (Decimal("0.0001"), Decimal("0.0001"), Decimal("10"), Decimal("0.000001"), Decimal("0.000001")),
        (Decimal("999999"), Decimal("999"), Decimal("10"), Decimal("0.01"), Decimal("998999.01")),
        (Decimal("100"), Decimal("2"), Decimal("0"), Decimal("0.01"), Decimal("0.00")),
    ],
)
def test_quote_fee_formula_and_ceiling(price, quantity, fee_bps, quantum, expected):
    assert quote_fee_amount(price, quantity, fee_bps, quantum) == expected


def test_fee_uses_final_rounded_fill_price(request_factory, policy_factory):
    policy = policy_factory(price_quantum=Decimal("0.01"), fee_quantum=Decimal("0.01"))
    result = simulate_paper_fill(request_factory(policy=policy))
    assert result.fill is not None
    expected = quote_fee_amount(
        result.fill.price,
        result.fill.quantity,
        policy.fee_bps,
        policy.fee_quantum,
    )
    assert result.fill.fee_amount == expected


def test_quote_asset_is_explicit_and_symbol_suffix_is_not_parsed(request_factory):
    result = simulate_paper_fill(request_factory(quote_asset="EUR"))
    assert result.fill is not None
    assert result.fill.fee_asset == "EUR"
    assert result.fill.symbol == "BTCUSDT"


@pytest.mark.parametrize(
    ("side", "role", "price_relation"),
    [
        (PaperSide.LONG, PaperFillRole.ENTRY, "higher"),
        (PaperSide.LONG, PaperFillRole.CLOSE, "lower"),
        (PaperSide.SHORT, PaperFillRole.ENTRY, "lower"),
        (PaperSide.SHORT, PaperFillRole.CLOSE, "higher"),
    ],
)
def test_simulated_fill_respects_adverse_action(
    request_factory,
    command_factory,
    candle_factory,
    side,
    role,
    price_relation,
):
    command = command_factory(side=side)
    result = simulate_paper_fill(
        request_factory(
            command=command,
            role=role,
            candles=(candle_factory(open_price=Decimal("100")),),
        )
    )
    assert result.fill is not None
    if price_relation == "higher":
        assert result.fill.price >= Decimal("100")
    else:
        assert result.fill.price <= Decimal("100")
    assert result.fill.side is side


def test_fill_is_immutable_existing_domain_contract(request_factory):
    fill = simulate_paper_fill(request_factory()).fill
    assert isinstance(fill, PaperFill)
    with pytest.raises(FrozenInstanceError):
        fill.price = Decimal("1")


def test_fill_output_maps_to_existing_orm_shape_without_session(request_factory):
    result = simulate_paper_fill(request_factory(role=PaperFillRole.CLOSE))
    assert result.fill is not None
    values = paper_fill_to_orm_values(
        result.fill,
        fill_role=PaperFillRole.CLOSE.persistence_role,
    )
    assert values["fill_role"] == "EXIT"
    assert values["source_closed_until_ms"] == EXPECTED_CLOSE_BOUNDARY_MS
    assert values["future_bars_used"] is False


def test_filled_at_is_exact_close_boundary_utc(request_factory):
    fill = simulate_paper_fill(request_factory()).fill
    assert fill is not None
    assert fill.filled_at == datetime.fromtimestamp(
        EXPECTED_CLOSE_BOUNDARY_MS / 1000,
        timezone.utc,
    )


def test_source_boundary_and_policy_ids_are_preserved(request_factory, policy_factory):
    policy = policy_factory()
    fill = simulate_paper_fill(request_factory(policy=policy)).fill
    assert fill is not None
    assert fill.source_closed_until_ms == EXPECTED_CLOSE_BOUNDARY_MS
    assert fill.simulation_policy_id == policy.simulation_policy_id
    assert fill.slippage_policy_id == policy.slippage_policy_id
    assert fill.fee_policy_id == policy.fee_policy_id
    assert fill.latency_policy_id == policy.latency_policy_id


def test_same_input_repeated_128_times_is_field_equivalent(request_factory):
    request = request_factory()
    first = simulate_paper_fill(request)
    assert all(simulate_paper_fill(request) == first for _ in range(128))


def test_input_order_does_not_change_success(request_factory, candle_factory):
    previous = candle_factory(
        open_time_ms=COMMAND_BOUNDARY_MS - 60_000,
        close_boundary_ms=COMMAND_BOUNDARY_MS,
    )
    exact = candle_factory()
    first = simulate_paper_fill(request_factory(candles=(previous, exact)))
    second = simulate_paper_fill(request_factory(candles=(exact, previous)))
    assert first == second


def test_global_decimal_context_does_not_change_result(request_factory):
    request = request_factory()
    baseline = simulate_paper_fill(request)
    original = getcontext().copy()
    try:
        getcontext().prec = 6
        getcontext().rounding = ROUND_DOWN
        changed = simulate_paper_fill(request)
        getcontext().prec = 50
        getcontext().rounding = ROUND_HALF_EVEN
        changed_again = simulate_paper_fill(request)
    finally:
        getcontext().prec = original.prec
        getcontext().rounding = original.rounding
    assert baseline == changed == changed_again


def test_global_decimal_exponent_limits_do_not_change_arithmetic():
    original = getcontext().copy()
    try:
        getcontext().Emax = 9
        getcontext().Emin = -9
        result = adverse_fill_price(
            Decimal("1000000000000000000"),
            Decimal("2"),
            Decimal("0.000000000000000001"),
            SimulatedTradeAction.BUY,
        )
    finally:
        getcontext().prec = original.prec
        getcontext().rounding = original.rounding
        getcontext().Emax = original.Emax
        getcontext().Emin = original.Emin
    assert result == Decimal("1000200000000000000.000000000000000000")


@pytest.mark.parametrize("timezone_value", ["UTC", "Europe/Moscow", "America/New_York"])
def test_local_timezone_environment_does_not_change_result(
    request_factory,
    monkeypatch,
    timezone_value,
):
    monkeypatch.setenv("TZ", timezone_value)
    result = simulate_paper_fill(request_factory())
    assert result.fill is not None
    assert result.fill.filled_at.tzinfo is timezone.utc


def test_identity_is_versioned_and_bounded(request_factory):
    fill = simulate_paper_fill(request_factory()).fill
    assert fill is not None
    assert fill.idempotency_key.startswith(f"paper:fill:{PAPER_IDEMPOTENCY_VERSION}:")
    assert fill.fill_id.startswith(f"paper:fill-id:{PAPER_IDEMPOTENCY_VERSION}:")
    assert len(fill.idempotency_key) <= 128
    assert len(fill.fill_id) <= 128


def _identity_fields(**changes):
    values = {
        "contract_version": "PAPER_FILL_SIMULATION_V1",
        "order_id": "order:1",
        "fill_role": "ENTRY",
        "source_open_time_ms": COMMAND_BOUNDARY_MS,
        "source_close_boundary_ms": EXPECTED_CLOSE_BOUNDARY_MS,
        "simulation_policy_id": "simulation:v1",
        "slippage_policy_id": "slippage:v1",
        "fee_policy_id": "fee:v1",
        "latency_policy_id": "latency:v1",
    }
    values.update(changes)
    return values


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("contract_version", "PAPER_FILL_SIMULATION_V2"),
        ("order_id", "order:2"),
        ("fill_role", "CLOSE"),
        ("source_open_time_ms", COMMAND_BOUNDARY_MS - 60_000),
        ("source_close_boundary_ms", EXPECTED_CLOSE_BOUNDARY_MS + 60_000),
        ("simulation_policy_id", "simulation:v2"),
        ("slippage_policy_id", "slippage:v2"),
        ("fee_policy_id", "fee:v2"),
        ("latency_policy_id", "latency:v2"),
    ],
)
def test_each_public_causal_field_changes_identity(field_name, value):
    baseline = simulated_fill_idempotency_key(**_identity_fields())
    changed = simulated_fill_idempotency_key(
        **_identity_fields(**{field_name: value})
    )
    assert baseline != changed


def test_keyword_field_order_does_not_change_identity():
    fields_value = _identity_fields()
    reverse = dict(reversed(tuple(fields_value.items())))
    assert simulated_fill_idempotency_key(**fields_value) == simulated_fill_idempotency_key(**reverse)
    assert simulated_fill_id(**fields_value) == simulated_fill_id(**reverse)


def test_identity_api_has_no_secret_or_mutable_diagnostic_inputs():
    names = set(inspect.signature(simulated_fill_idempotency_key).parameters)
    assert names == {
        "contract_version",
        "order_id",
        "fill_role",
        "source_open_time_ms",
        "source_close_boundary_ms",
        "simulation_policy_id",
        "slippage_policy_id",
        "fee_policy_id",
        "latency_policy_id",
    }
    source = inspect.getsource(simulated_fill_idempotency_key)
    assert "secret" not in source.lower()
    assert "datetime" not in source.lower()
    assert "random" not in source.lower()


@pytest.mark.parametrize(
    "seed",
    list(range(20)),
)
def test_randomized_valid_decimals_preserve_adverse_invariant(seed):
    generator = random.Random(seed)
    base = Decimal(generator.randint(1, 1_000_000)) / Decimal("100")
    quantum = Decimal("0.0001")
    buy = adverse_fill_price(base, Decimal("2"), quantum, SimulatedTradeAction.BUY)
    sell = adverse_fill_price(base, Decimal("2"), quantum, SimulatedTradeAction.SELL)
    assert buy >= base
    assert sell <= base
    assert buy > 0 and sell > 0


@pytest.mark.parametrize(
    "quantity",
    [
        Decimal("0.000000000000000001"),
        Decimal("0.000001"),
        Decimal("0.01"),
        Decimal("1"),
        Decimal("10"),
        Decimal("999999.999999999999999999"),
    ],
)
def test_valid_quantities_produce_nonnegative_deterministic_fee(quantity):
    first = quote_fee_amount(
        Decimal("123.456789"),
        quantity,
        Decimal("10"),
        Decimal("0.000000000000000001"),
    )
    second = quote_fee_amount(
        Decimal("123.456789"),
        quantity,
        Decimal("10"),
        Decimal("0.000000000000000001"),
    )
    assert first == second
    assert first >= 0


def test_no_wall_clock_random_database_or_network_symbols_in_simulator():
    source = inspect.getsource(
        __import__(
            "app.engine_paper.fill_simulator",
            fromlist=["simulate_paper_fill"],
        )
    )
    forbidden = (
        "datetime.now",
        "datetime.utcnow",
        "time.time",
        "uuid4",
        "secrets.",
        "random.",
        "Session(",
        "requests.",
        "httpx.",
        "socket.",
    )
    assert not any(fragment in source for fragment in forbidden)


def test_result_contains_bounded_safe_machine_contract(request_factory):
    result = simulate_paper_fill(request_factory())
    assert result.outcome is FillSimulationOutcome.FILLED
    assert result.reason_code == "PAPER_FILL_SIMULATOR_FILLED"
    assert len(result.message) <= 160
    assert "Traceback" not in result.message
    assert not any(
        fragment in name.lower()
        for name in {item.name for item in fields(result)}
        for fragment in ("secret", "password", "credential", "payload")
    )


@pytest.mark.parametrize(
    ("outcome", "fill"),
    [
        (FillSimulationOutcome.FILLED, None),
        (FillSimulationOutcome.INVALID_POLICY, "not-a-fill"),
    ],
)
def test_result_cannot_represent_inconsistent_fill_presence(outcome, fill):
    with pytest.raises((TypeError, ValueError)):
        FillSimulationResult(
            outcome=outcome,
            fill=fill,
            reason_code="PAPER_FILL_SIMULATOR_TEST",
            message="test",
        )
