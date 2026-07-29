"""Strict, side-effect-free safety vocabulary for the PAPER domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
import re
from typing import NoReturn, TypeVar


_IDENTITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_SYMBOL_RE = re.compile(r"[A-Z0-9]{2,32}\Z")
_MAX_MESSAGE_LENGTH = 240
_EnumT = TypeVar("_EnumT", bound=StrEnum)


class ExecutionMode(StrEnum):
    OFF = "OFF"
    PAPER = "PAPER"
    LIVE = "LIVE"


class PaperSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class PaperOrderType(StrEnum):
    MARKET_SIMULATED = "MARKET_SIMULATED"


class PaperOrderState(StrEnum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    OPEN = "OPEN"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class PaperPositionState(StrEnum):
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


class PaperExitCause(StrEnum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    SYSTEM_SAFETY_EXIT = "SYSTEM_SAFETY_EXIT"


class PaperEventType(StrEnum):
    PAPER_COMMAND_CREATED = "PAPER_COMMAND_CREATED"
    PAPER_COMMAND_REJECTED = "PAPER_COMMAND_REJECTED"
    PAPER_ORDER_CREATED = "PAPER_ORDER_CREATED"
    PAPER_ORDER_FILLED = "PAPER_ORDER_FILLED"
    PAPER_POSITION_OPENED = "PAPER_POSITION_OPENED"
    PAPER_EXIT_TRIGGERED = "PAPER_EXIT_TRIGGERED"
    PAPER_POSITION_CLOSED = "PAPER_POSITION_CLOSED"
    PAPER_EXECUTION_FAILED = "PAPER_EXECUTION_FAILED"
    PAPER_SAFETY_BLOCKED = "PAPER_SAFETY_BLOCKED"


class PaperInputHealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    CURRENT = "CURRENT"
    WITHIN_GRACE = "WITHIN_GRACE"


class PaperReasonCode(StrEnum):
    PAPER_CONFIG_MODE_MISSING_OFF = "PAPER_CONFIG_MODE_MISSING_OFF"
    PAPER_CONFIG_MODE_OFF = "PAPER_CONFIG_MODE_OFF"
    PAPER_CONFIG_MODE_UNKNOWN = "PAPER_CONFIG_MODE_UNKNOWN"
    PAPER_CONFIG_LIVE_DISABLED = "PAPER_CONFIG_LIVE_DISABLED"
    PAPER_CONFIG_POLICY_MISSING = "PAPER_CONFIG_POLICY_MISSING"
    PAPER_INPUT_SYMBOL_INVALID = "PAPER_INPUT_SYMBOL_INVALID"
    PAPER_INPUT_SIDE_INVALID = "PAPER_INPUT_SIDE_INVALID"
    PAPER_INPUT_QUANTITY_INVALID = "PAPER_INPUT_QUANTITY_INVALID"
    PAPER_INPUT_NOTIONAL_INVALID = "PAPER_INPUT_NOTIONAL_INVALID"
    PAPER_INPUT_PRICE_INVALID = "PAPER_INPUT_PRICE_INVALID"
    PAPER_INPUT_STOP_TARGET_INVALID = "PAPER_INPUT_STOP_TARGET_INVALID"
    PAPER_INPUT_IDENTITY_INVALID = "PAPER_INPUT_IDENTITY_INVALID"
    PAPER_INPUT_VALIDITY_INVALID = "PAPER_INPUT_VALIDITY_INVALID"
    PAPER_INPUT_TIME_INVALID = "PAPER_INPUT_TIME_INVALID"
    PAPER_INPUT_STRATEGY_MISSING = "PAPER_INPUT_STRATEGY_MISSING"
    PAPER_INPUT_RISK_MISSING = "PAPER_INPUT_RISK_MISSING"
    PAPER_SAFETY_SOURCE_STALE = "PAPER_SAFETY_SOURCE_STALE"
    PAPER_SAFETY_HEALTH_DEGRADED = "PAPER_SAFETY_HEALTH_DEGRADED"
    PAPER_SAFETY_HEALTH_UNKNOWN = "PAPER_SAFETY_HEALTH_UNKNOWN"
    PAPER_SAFETY_FUTURE_DATA_DETECTED = "PAPER_SAFETY_FUTURE_DATA_DETECTED"
    PAPER_RISK_APPROVAL_MISSING = "PAPER_RISK_APPROVAL_MISSING"
    PAPER_RISK_NOT_APPROVED = "PAPER_RISK_NOT_APPROVED"
    PAPER_ORDER_CREATED = "PAPER_ORDER_CREATED"
    PAPER_ORDER_VALIDATED = "PAPER_ORDER_VALIDATED"
    PAPER_ORDER_OPENED = "PAPER_ORDER_OPENED"
    PAPER_ORDER_FILLED = "PAPER_ORDER_FILLED"
    PAPER_ORDER_REJECTED = "PAPER_ORDER_REJECTED"
    PAPER_ORDER_FAILED = "PAPER_ORDER_FAILED"
    PAPER_ORDER_INVALID_TRANSITION = "PAPER_ORDER_INVALID_TRANSITION"
    PAPER_ORDER_TERMINAL = "PAPER_ORDER_TERMINAL"
    PAPER_ORDER_TYPE_UNSUPPORTED = "PAPER_ORDER_TYPE_UNSUPPORTED"
    PAPER_FILL_DUPLICATE = "PAPER_FILL_DUPLICATE"
    PAPER_FILL_PARTIAL_UNSUPPORTED = "PAPER_FILL_PARTIAL_UNSUPPORTED"
    PAPER_FILL_INVALID = "PAPER_FILL_INVALID"
    PAPER_FILL_FUTURE_DATA = "PAPER_FILL_FUTURE_DATA"
    PAPER_POSITION_OPENED = "PAPER_POSITION_OPENED"
    PAPER_POSITION_CLOSING = "PAPER_POSITION_CLOSING"
    PAPER_POSITION_CLOSED = "PAPER_POSITION_CLOSED"
    PAPER_POSITION_INVALID_TRANSITION = "PAPER_POSITION_INVALID_TRANSITION"
    PAPER_POSITION_ALREADY_CLOSED = "PAPER_POSITION_ALREADY_CLOSED"
    PAPER_POSITION_VERSION_CONFLICT = "PAPER_POSITION_VERSION_CONFLICT"
    PAPER_POSITION_NEGATIVE_REMAINDER = "PAPER_POSITION_NEGATIVE_REMAINDER"
    PAPER_POSITION_DUPLICATE_FILL = "PAPER_POSITION_DUPLICATE_FILL"
    PAPER_EXIT_CAUSE_UNSUPPORTED = "PAPER_EXIT_CAUSE_UNSUPPORTED"
    PAPER_EXIT_STOP_FIRST_CONFLICT = "PAPER_EXIT_STOP_FIRST_CONFLICT"
    PAPER_EXIT_STOP_LOSS_TRIGGERED = "PAPER_EXIT_STOP_LOSS_TRIGGERED"
    PAPER_EXIT_TAKE_PROFIT_TRIGGERED = "PAPER_EXIT_TAKE_PROFIT_TRIGGERED"
    PAPER_EXIT_SYSTEM_SAFETY_TRIGGERED = "PAPER_EXIT_SYSTEM_SAFETY_TRIGGERED"
    PAPER_EXIT_NO_TRIGGER = "PAPER_EXIT_NO_TRIGGER"
    PAPER_EXIT_VERSION_CONFLICT = "PAPER_EXIT_VERSION_CONFLICT"
    PAPER_IDEMPOTENCY_KEY_INVALID = "PAPER_IDEMPOTENCY_KEY_INVALID"
    PAPER_IDEMPOTENCY_COMMAND_REPLAY = "PAPER_IDEMPOTENCY_COMMAND_REPLAY"
    PAPER_IDEMPOTENCY_FILL_REPLAY = "PAPER_IDEMPOTENCY_FILL_REPLAY"
    PAPER_IDEMPOTENCY_JOURNAL_REPLAY = "PAPER_IDEMPOTENCY_JOURNAL_REPLAY"
    PAPER_INTERNAL_INVARIANT_VIOLATION = "PAPER_INTERNAL_INVARIANT_VIOLATION"


@dataclass(frozen=True, slots=True)
class PaperDomainError(Exception):
    reason_code: PaperReasonCode
    public_message: str
    field_path: str | None = None

    def __post_init__(self) -> None:
        message = str(self.public_message).strip()
        if not message:
            message = self.reason_code.value
        object.__setattr__(self, "public_message", message[:_MAX_MESSAGE_LENGTH])
        if self.field_path is not None:
            object.__setattr__(self, "field_path", str(self.field_path)[:80])
        Exception.__init__(self, self.public_message)


def fail(reason_code: PaperReasonCode, message: str, field_path: str | None = None) -> NoReturn:
    raise PaperDomainError(reason_code, message, field_path)


def parse_execution_mode(raw: object | None) -> ExecutionMode:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return ExecutionMode.OFF
    value = getattr(raw, "value", raw)
    try:
        return ExecutionMode(str(value).strip().upper())
    except ValueError:
        fail(PaperReasonCode.PAPER_CONFIG_MODE_UNKNOWN, "unknown execution mode", "mode")


def require_paper_mode(raw: object | None) -> ExecutionMode:
    mode = parse_execution_mode(raw)
    if mode is ExecutionMode.OFF:
        fail(PaperReasonCode.PAPER_CONFIG_MODE_OFF, "paper command is disabled", "mode")
    if mode is ExecutionMode.LIVE:
        fail(PaperReasonCode.PAPER_CONFIG_LIVE_DISABLED, "live execution is disabled", "mode")
    return mode


def require_identity(value: object, field_path: str) -> str:
    if not isinstance(value, str) or _IDENTITY_RE.fullmatch(value.strip()) is None:
        fail(PaperReasonCode.PAPER_INPUT_IDENTITY_INVALID, "invalid public identity", field_path)
    return value.strip()


def require_enum(
    value: object,
    enum_type: type[_EnumT],
    reason_code: PaperReasonCode,
    field_path: str,
) -> _EnumT:
    try:
        return enum_type(value)
    except (TypeError, ValueError):
        fail(reason_code, f"invalid {field_path}", field_path)


def normalize_symbol(value: object) -> str:
    if not isinstance(value, str):
        fail(PaperReasonCode.PAPER_INPUT_SYMBOL_INVALID, "invalid symbol", "symbol")
    symbol = value.strip().upper()
    if _SYMBOL_RE.fullmatch(symbol) is None:
        fail(PaperReasonCode.PAPER_INPUT_SYMBOL_INVALID, "invalid symbol", "symbol")
    return symbol


def require_decimal(
    value: object,
    field_path: str,
    *,
    positive: bool = False,
    nonnegative: bool = False,
    reason_code: PaperReasonCode = PaperReasonCode.PAPER_INPUT_PRICE_INVALID,
) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal) or not value.is_finite():
        fail(reason_code, "finite Decimal required", field_path)
    if positive and value <= 0:
        fail(reason_code, "positive Decimal required", field_path)
    if nonnegative and value < 0:
        fail(reason_code, "nonnegative Decimal required", field_path)
    return value


def require_utc(value: object, field_path: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        fail(PaperReasonCode.PAPER_INPUT_TIME_INVALID, "timezone-aware UTC timestamp required", field_path)
    if value.utcoffset() != timedelta(0):
        fail(PaperReasonCode.PAPER_INPUT_TIME_INVALID, "UTC timestamp required", field_path)
    return value


def require_nonnegative_int(value: object, field_path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        fail(PaperReasonCode.PAPER_INPUT_VALIDITY_INVALID, "nonnegative integer required", field_path)
    return value
