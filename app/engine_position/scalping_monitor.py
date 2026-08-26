"""Immutable observations for a Scalping position; no exit policy decisions."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class ScalpingPositionObservation:
    position_id: str
    observed_at_ms: int
    holding_time_ms: int
    current_price: float
    mfe_bps: float
    mae_bps: float
    spread_bps: float | None
    momentum: float | None
    relative_volume: float | None
    structure: str | None
    distance_to_target_bps: float
    distance_to_stop_bps: float


def observe_scalping_position(
    *, position_id: str, side: str, entry_price: float, stop_price: float,
    target_price: float, opened_at_ms: int, observed_at_ms: int,
    current_price: float, highest_price: float, lowest_price: float,
    spread_bps: float | None = None, momentum: float | None = None,
    relative_volume: float | None = None, structure: str | None = None,
) -> ScalpingPositionObservation:
    prices = (entry_price, stop_price, target_price, current_price, highest_price, lowest_price)
    if any(not isfinite(float(value)) or float(value) <= 0 for value in prices):
        raise ValueError("position prices must be positive and finite")
    if side not in {"BULLISH", "BEARISH"} or observed_at_ms < opened_at_ms:
        raise ValueError("position direction or observation time is invalid")
    if spread_bps is not None and (not isfinite(float(spread_bps)) or spread_bps < 0):
        raise ValueError("spread must be finite and non-negative")
    optional = (momentum, relative_volume)
    if any(value is not None and not isfinite(float(value)) for value in optional):
        raise ValueError("optional market metrics must be finite when evaluated")

    if side == "BULLISH":
        mfe = (highest_price - entry_price) / entry_price * 10_000
        mae = max(0.0, (entry_price - lowest_price) / entry_price * 10_000)
        target_distance = (target_price - current_price) / current_price * 10_000
        stop_distance = (current_price - stop_price) / current_price * 10_000
    else:
        mfe = (entry_price - lowest_price) / entry_price * 10_000
        mae = max(0.0, (highest_price - entry_price) / entry_price * 10_000)
        target_distance = (current_price - target_price) / current_price * 10_000
        stop_distance = (stop_price - current_price) / current_price * 10_000
    return ScalpingPositionObservation(
        position_id=position_id,
        observed_at_ms=observed_at_ms,
        holding_time_ms=observed_at_ms - opened_at_ms,
        current_price=current_price,
        mfe_bps=max(0.0, mfe),
        mae_bps=mae,
        spread_bps=spread_bps,
        momentum=momentum,
        relative_volume=relative_volume,
        structure=structure,
        distance_to_target_bps=target_distance,
        distance_to_stop_bps=stop_distance,
    )
