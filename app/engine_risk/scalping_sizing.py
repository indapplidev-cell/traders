"""Side-effect-free Scalping position sizing after a valid economic plan."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class ScalpingPositionSize:
    account_equity: float
    risk_per_trade_bps: float
    allowed_loss: float
    stop_distance: float
    unconstrained_quantity: float
    final_quantity: float
    liquidity_quantity_cap: float | None
    notional_quantity_cap: float | None
    limiting_factor: str


def size_scalping_position(
    *, account_equity: float, risk_per_trade_bps: float,
    stop_distance: float, entry_price: float,
    liquidity_quantity_cap: float | None = None,
    maximum_notional: float | None = None,
) -> ScalpingPositionSize:
    required = (account_equity, risk_per_trade_bps, stop_distance, entry_price)
    if any(not isfinite(float(value)) or float(value) <= 0 for value in required):
        raise ValueError("equity, risk, stop distance, and entry must be positive and finite")
    if risk_per_trade_bps not in {10.0, 15.0, 20.0, 25.0}:
        raise ValueError("risk per trade is outside declared Scalping cohorts")
    optional = (liquidity_quantity_cap, maximum_notional)
    if any(value is not None and (not isfinite(float(value)) or float(value) <= 0)
           for value in optional):
        raise ValueError("liquidity and notional caps must be positive and finite")

    allowed_loss = account_equity * risk_per_trade_bps / 10_000
    unconstrained = allowed_loss / stop_distance
    notional_cap = maximum_notional / entry_price if maximum_notional is not None else None
    candidates = [("RISK", unconstrained)]
    if liquidity_quantity_cap is not None:
        candidates.append(("LIQUIDITY", liquidity_quantity_cap))
    if notional_cap is not None:
        candidates.append(("NOTIONAL", notional_cap))
    limiting_factor, final = min(candidates, key=lambda item: item[1])
    return ScalpingPositionSize(
        account_equity=float(account_equity),
        risk_per_trade_bps=float(risk_per_trade_bps),
        allowed_loss=allowed_loss,
        stop_distance=float(stop_distance),
        unconstrained_quantity=unconstrained,
        final_quantity=final,
        liquidity_quantity_cap=liquidity_quantity_cap,
        notional_quantity_cap=notional_cap,
        limiting_factor=limiting_factor,
    )
