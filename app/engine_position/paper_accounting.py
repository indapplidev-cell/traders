"""Pure Decimal accounting primitives for unleveraged PAPER positions."""

from __future__ import annotations

from decimal import Decimal

from app.engine_safety.paper_domain import (
    PaperReasonCode,
    PaperSide,
    require_decimal,
    require_enum,
)


def _economic(value: object, field: str, *, positive: bool = False) -> Decimal:
    return require_decimal(
        value,
        field,
        positive=positive,
        reason_code=PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
    )


def gross_realized_pnl(
    side: PaperSide,
    entry_price: Decimal,
    exit_price: Decimal,
    quantity: Decimal,
) -> Decimal:
    side = require_enum(
        side,
        PaperSide,
        PaperReasonCode.PAPER_INPUT_SIDE_INVALID,
        "side",
    )
    entry = _economic(entry_price, "entry_price", positive=True)
    exit_value = _economic(exit_price, "exit_price", positive=True)
    size = _economic(quantity, "quantity", positive=True)
    if side is PaperSide.LONG:
        return (exit_value - entry) * size
    return (entry - exit_value) * size


def net_realized_pnl(
    gross_pnl: Decimal,
    entry_fees: Decimal,
    exit_fees: Decimal,
) -> Decimal:
    gross = _economic(gross_pnl, "gross_pnl")
    entry_fee = require_decimal(
        entry_fees,
        "entry_fees",
        nonnegative=True,
        reason_code=PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
    )
    exit_fee = require_decimal(
        exit_fees,
        "exit_fees",
        nonnegative=True,
        reason_code=PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
    )
    return gross - entry_fee - exit_fee


def unrealized_pnl(
    side: PaperSide,
    entry_price: Decimal,
    mark_price: Decimal,
    remaining_quantity: Decimal,
) -> Decimal:
    return gross_realized_pnl(side, entry_price, mark_price, remaining_quantity)


def total_fees(entry_fees: Decimal, exit_fees: Decimal) -> Decimal:
    entry_fee = require_decimal(
        entry_fees,
        "entry_fees",
        nonnegative=True,
        reason_code=PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
    )
    exit_fee = require_decimal(
        exit_fees,
        "exit_fees",
        nonnegative=True,
        reason_code=PaperReasonCode.PAPER_POSITION_INVALID_TRANSITION,
    )
    return entry_fee + exit_fee


def return_percentage(
    net_pnl: Decimal,
    entry_price: Decimal,
    quantity: Decimal,
) -> Decimal:
    net = _economic(net_pnl, "net_pnl")
    entry = _economic(entry_price, "entry_price", positive=True)
    size = _economic(quantity, "quantity", positive=True)
    return net / abs(entry * size) * Decimal("100")


def risk_multiple(net_pnl: Decimal, initial_risk: Decimal) -> Decimal:
    net = _economic(net_pnl, "net_pnl")
    risk = _economic(initial_risk, "initial_risk", positive=True)
    return net / risk
