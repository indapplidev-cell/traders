from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from decimal import Decimal

import pytest

from app.engine_paper.fill_policy import (
    FillPolicyValidationError,
    PaperFillPriceSource,
    PaperFillSimulationPolicy,
    PaperIntrabarConflictPolicy,
    is_numeric_38_18_compatible,
)
from app.engine_paper.fill_simulator import (
    FillCandleValidationError,
    FillSimulationOutcome,
    FillSimulationRequest,
    MAX_CANDIDATE_CANDLES,
    PaperFillCandle,
    PaperFillRole,
)
from tests.paper_fill_simulator.conftest import (
    COMMAND_BOUNDARY_MS,
    EXPECTED_CLOSE_BOUNDARY_MS,
)


def test_exact_foundation_policy_is_accepted(policy_factory):
    policy = policy_factory()
    assert policy.price_source is PaperFillPriceSource.NEXT_ELIGIBLE_CLOSED_1M_OPEN
    assert policy.intrabar_conflict_policy is PaperIntrabarConflictPolicy.STOP_FIRST_CONSERVATIVE
    assert policy.slippage_bps == Decimal("2")
    assert policy.fee_bps == Decimal("10")


@pytest.mark.parametrize(
    ("field_name", "value", "expected_path"),
    [
        ("price_source", "CLOSE", "price_source"),
        ("timeframe", "5m", "timeframe"),
        ("timeframe", "1M", "timeframe"),
        ("latency_candles", 0, "latency_candles"),
        ("latency_candles", 2, "latency_candles"),
        ("latency_candles", True, "latency_candles"),
        ("slippage_bps", Decimal("0"), "slippage_bps"),
        ("slippage_bps", Decimal("1.999"), "slippage_bps"),
        ("slippage_bps", Decimal("10000"), "slippage_bps"),
        ("slippage_bps", Decimal("-1"), "slippage_bps"),
        ("slippage_bps", Decimal("NaN"), "slippage_bps"),
        ("slippage_bps", Decimal("Infinity"), "slippage_bps"),
        ("slippage_bps", 2.0, "slippage_bps"),
        ("fee_bps", Decimal("0"), "fee_bps"),
        ("fee_bps", Decimal("9.999"), "fee_bps"),
        ("fee_bps", Decimal("10001"), "fee_bps"),
        ("fee_bps", Decimal("-1"), "fee_bps"),
        ("fee_bps", Decimal("NaN"), "fee_bps"),
        ("fee_bps", 10.0, "fee_bps"),
        ("partial_fill_enabled", True, "partial_fill_enabled"),
        ("future_data_allowed", True, "future_data_allowed"),
        ("intrabar_conflict_policy", "TARGET_FIRST", "intrabar_conflict_policy"),
    ],
)
def test_wrong_foundation_policy_value_is_rejected(
    policy_factory,
    field_name,
    value,
    expected_path,
):
    with pytest.raises(FillPolicyValidationError) as error:
        policy_factory(**{field_name: value})
    assert error.value.field_path == expected_path
    assert len(error.value.public_message) <= 160


@pytest.mark.parametrize(
    "field_name",
    [
        "simulation_policy_id",
        "fee_policy_id",
        "slippage_policy_id",
        "latency_policy_id",
        "contract_version",
    ],
)
@pytest.mark.parametrize("value", ["", " ", "invalid/value", "é", "x" * 129])
def test_policy_identity_is_bounded(policy_factory, field_name, value):
    with pytest.raises(FillPolicyValidationError) as error:
        policy_factory(**{field_name: value})
    assert error.value.reason_code == "PAPER_FILL_SIMULATOR_INVALID_POLICY"


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("price_quantum", Decimal("0")),
        ("price_quantum", Decimal("-0.01")),
        ("price_quantum", Decimal("NaN")),
        ("price_quantum", Decimal("Infinity")),
        ("price_quantum", Decimal("0.0000000000000000001")),
        ("price_quantum", 0.01),
        ("fee_quantum", Decimal("0")),
        ("fee_quantum", Decimal("-1")),
        ("fee_quantum", Decimal("NaN")),
        ("fee_quantum", Decimal("0.0000000000000000001")),
        ("fee_quantum", 0.01),
    ],
)
def test_invalid_explicit_quantum_is_rejected(policy_factory, field_name, value):
    with pytest.raises(FillPolicyValidationError) as error:
        policy_factory(**{field_name: value})
    assert error.value.reason_code == "PAPER_FILL_SIMULATOR_INVALID_PRECISION"
    assert error.value.field_path == field_name


def test_policy_is_frozen_and_has_no_mutable_fields(policy_factory):
    policy = policy_factory()
    with pytest.raises(FrozenInstanceError):
        policy.fee_bps = Decimal("0")
    assert not any(isinstance(getattr(policy, item.name), (dict, list, set)) for item in fields(policy))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0"), True),
        (Decimal("1.000000000000000000"), True),
        (Decimal("99999999999999999999.999999999999999999"), True),
        (Decimal("100000000000000000000"), False),
        (Decimal("0.0000000000000000001"), False),
        (Decimal("NaN"), False),
        (Decimal("Infinity"), False),
    ],
)
def test_numeric_38_18_compatibility(value, expected):
    assert is_numeric_38_18_compatible(value) is expected


def test_exact_decimal_candle_is_accepted(candle_factory):
    candle = candle_factory()
    assert candle.identity == (
        "BTCUSDT",
        "1m",
        COMMAND_BOUNDARY_MS,
        EXPECTED_CLOSE_BOUNDARY_MS,
    )


def test_candle_symbol_is_normalized(candle_factory):
    assert candle_factory(symbol=" btcusdt ").symbol == "BTCUSDT"


@pytest.mark.parametrize(
    ("field_name", "value", "outcome"),
    [
        ("timeframe", "5m", FillSimulationOutcome.TIMEFRAME_MISMATCH),
        ("open_time_ms", -1, FillSimulationOutcome.INVALID_CANDLE),
        ("open_time_ms", True, FillSimulationOutcome.INVALID_CANDLE),
        ("open_time_ms", COMMAND_BOUNDARY_MS + 1, FillSimulationOutcome.INVALID_CANDLE),
        ("close_boundary_ms", EXPECTED_CLOSE_BOUNDARY_MS - 1, FillSimulationOutcome.INVALID_CANDLE),
        ("close_boundary_ms", EXPECTED_CLOSE_BOUNDARY_MS + 1, FillSimulationOutcome.INVALID_CANDLE),
        ("observed_closed_until_ms", -1, FillSimulationOutcome.INVALID_CANDLE),
        ("observed_closed_until_ms", COMMAND_BOUNDARY_MS - 1, FillSimulationOutcome.INVALID_CANDLE),
        ("is_closed", 1, FillSimulationOutcome.INVALID_CANDLE),
        ("open_price", 100.0, FillSimulationOutcome.INVALID_CANDLE),
        ("high_price", "105", FillSimulationOutcome.INVALID_CANDLE),
        ("low_price", Decimal("NaN"), FillSimulationOutcome.INVALID_CANDLE),
        ("close_price", Decimal("Infinity"), FillSimulationOutcome.INVALID_CANDLE),
        ("open_price", Decimal("0"), FillSimulationOutcome.INVALID_CANDLE),
        ("open_price", Decimal("-1"), FillSimulationOutcome.INVALID_CANDLE),
        ("high_price", Decimal("99"), FillSimulationOutcome.INVALID_CANDLE),
        ("low_price", Decimal("102"), FillSimulationOutcome.INVALID_CANDLE),
        ("low_price", Decimal("106"), FillSimulationOutcome.INVALID_CANDLE),
        ("symbol", "BTC/USDT", FillSimulationOutcome.INVALID_CANDLE),
    ],
)
def test_invalid_candle_contract_rejected(
    candle_factory,
    field_name,
    value,
    outcome,
):
    with pytest.raises(FillCandleValidationError) as error:
        candle_factory(**{field_name: value})
    assert error.value.outcome is outcome


def test_candle_is_frozen_and_has_no_mutable_fields(candle_factory):
    candle = candle_factory()
    with pytest.raises(FrozenInstanceError):
        candle.open_price = Decimal("1")
    assert not any(isinstance(getattr(candle, item.name), (dict, list, set)) for item in fields(candle))


def test_request_requires_immutable_bounded_candidates(request_factory, candle_factory):
    with pytest.raises(TypeError):
        request_factory(candidate_candles=[candle_factory()])
    with pytest.raises(ValueError):
        request_factory(candidate_candles=tuple(candle_factory() for _ in range(MAX_CANDIDATE_CANDLES + 1)))


def test_request_is_frozen(request_factory):
    request = request_factory()
    with pytest.raises(FrozenInstanceError):
        request.quote_asset = "BTC"


def test_fill_role_has_exact_persistence_mapping():
    assert PaperFillRole.ENTRY.persistence_role == "ENTRY"
    assert PaperFillRole.CLOSE.persistence_role == "EXIT"
