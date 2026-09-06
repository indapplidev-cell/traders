from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.engine_execution.paper_models import PaperExecutionCommand
from app.engine_safety import (
    ExecutionMode,
    PaperDomainError,
    PaperEventType,
    PaperExitCause,
    PaperInputHealthStatus,
    PaperOrderState,
    PaperOrderType,
    PaperPositionState,
    PaperReasonCode,
    PaperSide,
    parse_execution_mode,
    require_paper_mode,
)


@pytest.mark.parametrize(
    ("enum_type", "expected"),
    [
        (ExecutionMode, {"OFF", "PAPER", "LIVE"}),
        (PaperSide, {"LONG", "SHORT"}),
        (PaperOrderType, {"MARKET_SIMULATED"}),
        (PaperOrderState, {"CREATED", "VALIDATED", "OPEN", "FILLED", "REJECTED", "FAILED"}),
        (PaperPositionState, {"OPEN", "CLOSING", "CLOSED", "FAILED"}),
        (PaperExitCause, {
            "STOP_LOSS", "TAKE_PROFIT", "SYSTEM_SAFETY_EXIT",
            "OPERATOR_RECOVERY_CLOSE",
        }),
        (
            PaperEventType,
            {
                "PAPER_COMMAND_CREATED",
                "PAPER_COMMAND_REJECTED",
                "PAPER_ORDER_CREATED",
                "PAPER_ORDER_VALIDATED",
                "PAPER_ORDER_OPENED",
                "PAPER_ORDER_FILLED",
                "PAPER_POSITION_OPENED",
                "PAPER_EXIT_TRIGGERED",
                "PAPER_POSITION_CLOSED",
                "PAPER_EXECUTION_FAILED",
                "PAPER_SAFETY_BLOCKED",
            },
        ),
    ],
)
def test_strict_enum_members(enum_type, expected):
    assert {item.value for item in enum_type} == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, ExecutionMode.OFF), ("", ExecutionMode.OFF), ("paper", ExecutionMode.PAPER),
     ("OFF", ExecutionMode.OFF), ("LIVE", ExecutionMode.LIVE)],
)
def test_mode_parser(raw, expected):
    assert parse_execution_mode(raw) is expected


def test_unknown_mode_fails_closed():
    with pytest.raises(PaperDomainError) as error:
        parse_execution_mode("DRY_RUN")
    assert error.value.reason_code is PaperReasonCode.PAPER_CONFIG_MODE_UNKNOWN


def test_paper_mode_is_accepted():
    assert require_paper_mode("PAPER") is ExecutionMode.PAPER


@pytest.mark.parametrize(
    ("mode", "code"),
    [
        ("OFF", PaperReasonCode.PAPER_CONFIG_MODE_OFF),
        ("LIVE", PaperReasonCode.PAPER_CONFIG_LIVE_DISABLED),
        (None, PaperReasonCode.PAPER_CONFIG_MODE_OFF),
    ],
)
def test_non_paper_mode_cannot_create_command(command_factory, mode, code):
    with pytest.raises(PaperDomainError) as error:
        command_factory(mode=mode)
    assert error.value.reason_code is code


@pytest.mark.parametrize("side", [PaperSide.LONG, PaperSide.SHORT])
def test_valid_directional_command(command_factory, side):
    command = command_factory(side=side)
    assert command.side is side
    assert command.mode is ExecutionMode.PAPER


def test_symbol_is_normalized(command_factory):
    assert command_factory(symbol=" btcusdt ").symbol == "BTCUSDT"


@pytest.mark.parametrize(
    "field_name",
    [
        "command_id",
        "idempotency_key",
        "strategy_decision_id",
        "risk_decision_id",
        "setup_id",
        "pipeline_run_id",
        "analysis_result_id",
        "configuration_fingerprint",
        "simulation_policy_id",
        "fee_policy_id",
        "slippage_policy_id",
        "latency_policy_id",
    ],
)
def test_blank_causal_identity_rejected(command_factory, field_name):
    with pytest.raises(PaperDomainError) as error:
        command_factory(**{field_name: " "})
    assert error.value.reason_code is PaperReasonCode.PAPER_INPUT_IDENTITY_INVALID
    assert error.value.field_path == field_name


@pytest.mark.parametrize("symbol", ["", " ", "BTC/USDT", "é", "A", "A" * 33])
def test_invalid_symbol_rejected(command_factory, symbol):
    with pytest.raises(PaperDomainError) as error:
        command_factory(symbol=symbol)
    assert error.value.reason_code is PaperReasonCode.PAPER_INPUT_SYMBOL_INVALID


@pytest.mark.parametrize(
    ("field_name", "value", "expected_code"),
    [
        ("requested_quantity", 1.0, PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID),
        ("requested_quantity", Decimal("NaN"), PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID),
        ("requested_quantity", Decimal("Infinity"), PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID),
        ("requested_quantity", Decimal("-Infinity"), PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID),
        ("requested_quantity", Decimal("0"), PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID),
        ("requested_quantity", Decimal("-1"), PaperReasonCode.PAPER_INPUT_QUANTITY_INVALID),
        ("requested_notional", 1.0, PaperReasonCode.PAPER_INPUT_NOTIONAL_INVALID),
        ("requested_notional", Decimal("NaN"), PaperReasonCode.PAPER_INPUT_NOTIONAL_INVALID),
        ("requested_notional", Decimal("0"), PaperReasonCode.PAPER_INPUT_NOTIONAL_INVALID),
        ("entry_reference_price", 100.0, PaperReasonCode.PAPER_INPUT_PRICE_INVALID),
        ("entry_reference_price", Decimal("NaN"), PaperReasonCode.PAPER_INPUT_PRICE_INVALID),
        ("entry_reference_price", Decimal("Infinity"), PaperReasonCode.PAPER_INPUT_PRICE_INVALID),
        ("entry_reference_price", Decimal("0"), PaperReasonCode.PAPER_INPUT_PRICE_INVALID),
        ("stop_price", Decimal("-1"), PaperReasonCode.PAPER_INPUT_PRICE_INVALID),
        ("target_price", Decimal("0"), PaperReasonCode.PAPER_INPUT_PRICE_INVALID),
    ],
)
def test_invalid_decimal_contract(command_factory, field_name, value, expected_code):
    with pytest.raises(PaperDomainError) as error:
        command_factory(**{field_name: value})
    assert error.value.reason_code is expected_code


def test_tiny_decimal_is_preserved(command_factory):
    tiny = Decimal("0.00000000000000000001")
    command = command_factory(
        requested_quantity=tiny,
        requested_notional=tiny * Decimal("100"),
    )
    assert command.requested_quantity is tiny
    assert command.requested_notional == Decimal("0.00000000000000000100")


def test_large_decimal_is_preserved(command_factory):
    large = Decimal("1E+100")
    command = command_factory(
        requested_quantity=large,
        requested_notional=large * Decimal("100"),
    )
    assert command.requested_quantity is large


def test_optional_notional_may_be_absent(command_factory):
    assert command_factory(requested_notional=None).requested_notional is None


def test_notional_is_derived_from_authoritative_quantity(command_factory):
    with pytest.raises(PaperDomainError) as error:
        command_factory(requested_notional=Decimal("201"))
    assert error.value.reason_code is PaperReasonCode.PAPER_INPUT_NOTIONAL_INVALID


@pytest.mark.parametrize(
    ("side", "stop", "target"),
    [
        (PaperSide.LONG, Decimal("100"), Decimal("120")),
        (PaperSide.LONG, Decimal("90"), Decimal("100")),
        (PaperSide.SHORT, Decimal("100"), Decimal("90")),
        (PaperSide.SHORT, Decimal("120"), Decimal("100")),
    ],
)
def test_invalid_stop_target_geometry(command_factory, side, stop, target):
    with pytest.raises(PaperDomainError) as error:
        command_factory(side=side, stop_price=stop, target_price=target)
    assert error.value.reason_code is PaperReasonCode.PAPER_INPUT_STOP_TARGET_INVALID


@pytest.mark.parametrize(
    ("health", "code"),
    [
        ("STALE", PaperReasonCode.PAPER_SAFETY_SOURCE_STALE),
        ("DEGRADED", PaperReasonCode.PAPER_SAFETY_HEALTH_DEGRADED),
        ("UNKNOWN", PaperReasonCode.PAPER_SAFETY_HEALTH_UNKNOWN),
    ],
)
def test_unhealthy_input_rejected(command_factory, health, code):
    with pytest.raises(PaperDomainError) as error:
        command_factory(input_health_status=health)
    assert error.value.reason_code is code


@pytest.mark.parametrize("health", list(PaperInputHealthStatus))
def test_allowed_input_health(command_factory, health):
    assert command_factory(input_health_status=health).input_health_status is health


def test_future_input_rejected(command_factory):
    with pytest.raises(PaperDomainError) as error:
        command_factory(future_bars_used=True)
    assert error.value.reason_code is PaperReasonCode.PAPER_SAFETY_FUTURE_DATA_DETECTED


def test_final_approval_is_required(command_factory):
    with pytest.raises(PaperDomainError) as error:
        command_factory(final_paper_approval=False)
    assert error.value.reason_code is PaperReasonCode.PAPER_RISK_APPROVAL_MISSING


def test_validity_cannot_precede_boundary(command_factory):
    with pytest.raises(PaperDomainError) as error:
        command_factory(valid_until_ms=999)
    assert error.value.reason_code is PaperReasonCode.PAPER_INPUT_VALIDITY_INVALID


@pytest.mark.parametrize("field_name", ["closed_until_ms", "valid_until_ms"])
def test_negative_boundary_rejected(command_factory, field_name):
    with pytest.raises(PaperDomainError):
        command_factory(**{field_name: -1})


@pytest.mark.parametrize(
    "created_at",
    [
        datetime(2026, 7, 29, 6, 0),
        datetime(2026, 7, 29, 9, 0, tzinfo=timezone(timedelta(hours=3))),
    ],
)
def test_created_at_must_be_utc(command_factory, created_at):
    with pytest.raises(PaperDomainError) as error:
        command_factory(created_at=created_at)
    assert error.value.reason_code is PaperReasonCode.PAPER_INPUT_TIME_INVALID


def test_command_is_frozen(command_factory):
    command = command_factory()
    with pytest.raises(FrozenInstanceError):
        command.symbol = "ETHUSDT"


def test_command_has_no_secret_or_credential_fields():
    names = {field.name.lower() for field in fields(PaperExecutionCommand)}
    assert not any(fragment in name for name in names for fragment in ("secret", "credential", "password", "api_key"))


def test_command_has_no_mutable_collection_fields(command_factory):
    command = command_factory()
    assert not any(isinstance(getattr(command, field.name), (dict, list, set)) for field in fields(command))


def test_unknown_side_is_not_defaulted(command_factory):
    with pytest.raises(PaperDomainError) as error:
        command_factory(side="BULLISH")
    assert error.value.reason_code is PaperReasonCode.PAPER_INPUT_SIDE_INVALID


def test_unknown_order_type_rejected(command_factory):
    with pytest.raises(PaperDomainError) as error:
        command_factory(order_type="MARKET")
    assert error.value.reason_code is PaperReasonCode.PAPER_ORDER_TYPE_UNSUPPORTED


def test_public_error_is_bounded():
    error = PaperDomainError(PaperReasonCode.PAPER_INTERNAL_INVARIANT_VIOLATION, "x" * 1_000, "field")
    assert len(error.public_message) == 240
    assert "Traceback" not in str(error)
