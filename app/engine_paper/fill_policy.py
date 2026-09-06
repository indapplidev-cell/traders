"""Immutable policy and precision contracts for deterministic PAPER fills."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import re


_IDENTITY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_MAX_MESSAGE_LENGTH = 160


class PaperFillPriceSource(StrEnum):
    NEXT_ELIGIBLE_CLOSED_1M_OPEN = "NEXT_ELIGIBLE_CLOSED_1M_OPEN"


class PaperIntrabarConflictPolicy(StrEnum):
    STOP_FIRST_CONSERVATIVE = "STOP_FIRST_CONSERVATIVE"


@dataclass(frozen=True, slots=True)
class FillPolicyValidationError(ValueError):
    """Bounded validation failure without raw input or traceback data."""

    reason_code: str
    public_message: str
    field_path: str | None = None

    def __post_init__(self) -> None:
        message = str(self.public_message).strip() or self.reason_code
        object.__setattr__(self, "reason_code", str(self.reason_code)[:96])
        object.__setattr__(self, "public_message", message[:_MAX_MESSAGE_LENGTH])
        if self.field_path is not None:
            object.__setattr__(self, "field_path", str(self.field_path)[:80])
        ValueError.__init__(self, self.public_message)


def _fail(message: str, field_path: str, *, precision: bool = False) -> None:
    code = (
        "PAPER_FILL_SIMULATOR_INVALID_PRECISION"
        if precision
        else "PAPER_FILL_SIMULATOR_INVALID_POLICY"
    )
    raise FillPolicyValidationError(code, message, field_path)


def _identity(value: object, field_path: str) -> str:
    if not isinstance(value, str):
        _fail("bounded public identity required", field_path)
    normalized = value.strip()
    if _IDENTITY_RE.fullmatch(normalized) is None:
        _fail("bounded public identity required", field_path)
    return normalized


def _decimal(
    value: object,
    field_path: str,
    *,
    nonnegative: bool = False,
    positive: bool = False,
    precision: bool = False,
) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal) or not value.is_finite():
        _fail("finite Decimal required", field_path, precision=precision)
    if nonnegative and value < 0:
        _fail("nonnegative Decimal required", field_path, precision=precision)
    if positive and value <= 0:
        _fail("positive Decimal required", field_path, precision=precision)
    return value


def is_numeric_38_18_compatible(value: Decimal) -> bool:
    """Return whether ``value`` round-trips through PostgreSQL NUMERIC(38,18)."""

    if not isinstance(value, Decimal) or not value.is_finite():
        return False
    if value.is_zero():
        return value.as_tuple().exponent >= -18
    exponent = value.as_tuple().exponent
    scale = max(0, -exponent)
    integer_digits = max(0, value.adjusted() + 1)
    return scale <= 18 and integer_digits <= 20


@dataclass(frozen=True, slots=True)
class PaperFillSimulationPolicy:
    """The exact approved foundation policy plus explicit precision inputs."""

    simulation_policy_id: str
    fee_policy_id: str
    slippage_policy_id: str
    latency_policy_id: str
    price_source: PaperFillPriceSource
    timeframe: str
    latency_candles: int
    slippage_bps: Decimal
    fee_bps: Decimal
    partial_fill_enabled: bool
    future_data_allowed: bool
    intrabar_conflict_policy: PaperIntrabarConflictPolicy
    price_quantum: Decimal
    fee_quantum: Decimal
    contract_version: str

    def __post_init__(self) -> None:
        for name in (
            "simulation_policy_id",
            "fee_policy_id",
            "slippage_policy_id",
            "latency_policy_id",
            "contract_version",
        ):
            object.__setattr__(self, name, _identity(getattr(self, name), name))

        try:
            price_source = PaperFillPriceSource(self.price_source)
        except (TypeError, ValueError):
            _fail("unsupported fill price source", "price_source")
        object.__setattr__(self, "price_source", price_source)
        if price_source is not PaperFillPriceSource.NEXT_ELIGIBLE_CLOSED_1M_OPEN:
            _fail("unsupported fill price source", "price_source")

        if self.timeframe != "1m":
            _fail("foundation fill timeframe must be 1m", "timeframe")
        if (
            isinstance(self.latency_candles, bool)
            or not isinstance(self.latency_candles, int)
            or self.latency_candles != 1
        ):
            _fail("foundation latency must be one candle", "latency_candles")

        slippage = _decimal(
            self.slippage_bps,
            "slippage_bps",
            nonnegative=True,
        )
        fee = _decimal(self.fee_bps, "fee_bps", nonnegative=True)
        if slippage >= Decimal("10000"):
            _fail("slippage must be below 10000 bps", "slippage_bps")
        if fee > Decimal("10000"):
            _fail("fee must not exceed 10000 bps", "fee_bps")
        if slippage != Decimal("2"):
            _fail("foundation slippage must be exactly 2 bps", "slippage_bps")
        dynamic_exit_fee = self.fee_policy_id.startswith("fee:binance-account:")
        if dynamic_exit_fee:
            if fee <= 0:
                _fail("account exit fee must be positive", "fee_bps")
        elif fee != Decimal("10"):
            _fail("foundation fee must be exactly 10 bps", "fee_bps")

        if self.partial_fill_enabled is not False:
            _fail("partial fills are unsupported", "partial_fill_enabled")
        if self.future_data_allowed is not False:
            _fail("future data is forbidden", "future_data_allowed")

        try:
            conflict_policy = PaperIntrabarConflictPolicy(
                self.intrabar_conflict_policy
            )
        except (TypeError, ValueError):
            _fail("unsupported intrabar conflict policy", "intrabar_conflict_policy")
        object.__setattr__(self, "intrabar_conflict_policy", conflict_policy)
        if conflict_policy is not PaperIntrabarConflictPolicy.STOP_FIRST_CONSERVATIVE:
            _fail("unsupported intrabar conflict policy", "intrabar_conflict_policy")

        for name in ("price_quantum", "fee_quantum"):
            quantum = _decimal(
                getattr(self, name),
                name,
                positive=True,
                precision=True,
            )
            if not is_numeric_38_18_compatible(quantum):
                _fail(
                    "quantum must be NUMERIC(38,18) compatible",
                    name,
                    precision=True,
                )
