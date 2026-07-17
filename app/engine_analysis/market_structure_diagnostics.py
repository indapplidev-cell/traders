"""Causal, research-only structure diagnostics for ENGINE-ANALYSIS-34.

The module deliberately works from price/volume structure rather than treating
an indicator vote as a market regime.  It has no dependency on setup, risk, or
execution packages and never emits an actionable value.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Mapping, Sequence


STAGE = "ENGINE-ANALYSIS-34"
RESEARCH_ONLY = True


@dataclass(frozen=True)
class StructureBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def _value(row: Mapping[str, Any] | object, name: str) -> Any:
    if isinstance(row, Mapping) and name in row:
        return row[name]
    if hasattr(row, name):
        return getattr(row, name)
    raise ValueError(f"missing candle field: {name}")


def _bars(rows: Sequence[Mapping[str, Any] | object]) -> list[StructureBar]:
    result: list[StructureBar] = []
    for row in rows:
        raw_time = _value(row, "timestamp")
        timestamp = raw_time if isinstance(raw_time, datetime) else datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
        values = [float(_value(row, key)) for key in ("open", "high", "low", "close", "volume")]
        if not all(isfinite(value) for value in values):
            raise ValueError("OHLCV values must be finite")
        open_, high, low, close, volume = values
        if min(open_, high, low, close) <= 0 or volume < 0 or high < max(open_, close) or low > min(open_, close):
            raise ValueError("invalid OHLCV candle")
        result.append(StructureBar(timestamp, open_, high, low, close, volume))
    result.sort(key=lambda bar: bar.timestamp)
    if len({bar.timestamp for bar in result}) != len(result):
        raise ValueError("duplicate candle timestamps")
    return result


def _true_ranges(bars: Sequence[StructureBar]) -> list[float]:
    return [
        max(current.high - current.low, abs(current.high - previous.close), abs(current.low - previous.close))
        for previous, current in zip(bars, bars[1:])
    ]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _round(value: float) -> float:
    return round(value, 6)


def _failed_breakout(bars: Sequence[StructureBar], observation_start: int, atr: float) -> tuple[bool, str | None, float | None]:
    """Find a boundary excursion whose hold subsequently failed.

    A return is measured against the broken boundary, not against the opposite
    edge of the whole range.  This catches a failed downside probe even when
    the rebound subsequently travels through the balance area.
    """

    for index in range(observation_start, len(bars) - 2):
        prior = bars[max(0, index - 16) : index]
        if len(prior) < 8:
            continue
        upper = max(bar.high for bar in prior)
        lower = min(bar.low for bar in prior)
        bar = bars[index]
        later = bars[index + 1 :]
        up_excursion = bar.high - upper
        down_excursion = lower - bar.low
        up_break = up_excursion >= atr * 0.35 and (bar.close > upper or up_excursion >= atr * 0.75)
        down_break = down_excursion >= atr * 0.35 and (bar.close < lower or down_excursion >= atr * 0.75)
        if up_break:
            returned = [candidate.close <= upper for candidate in later]
            if bars[-1].close <= upper and any(all(returned[start : start + 2]) for start in range(max(0, len(returned) - 1))):
                return True, "UP", upper
        if down_break:
            returned = [candidate.close >= lower for candidate in later]
            if bars[-1].close >= lower and any(all(returned[start : start + 2]) for start in range(max(0, len(returned) - 1))):
                return True, "DOWN", lower
    return False, None, None


def diagnose_market_structure(
    candles: Sequence[Mapping[str, Any] | object],
    *,
    base_regime: str,
    observation_bars: int = 8,
) -> dict[str, Any]:
    """Return deterministic structural evidence using only supplied bars."""

    if base_regime not in {"UP", "DOWN", "FLAT", "UNKNOWN"}:
        raise ValueError("unsupported base_regime")
    if observation_bars < 4:
        raise ValueError("observation_bars must be >= 4")
    bars = _bars(candles)
    if len(bars) < observation_bars + 16:
        return {
            "stage": STAGE, "research_only": True, "data_sufficient": False,
            "reason_codes": [], "future_bars_used": False,
        }

    observation_start = len(bars) - observation_bars
    recent = bars[observation_start:]
    history = bars[max(0, observation_start - 24) : observation_start]
    tr = _true_ranges(bars)
    atr = _mean(tr[-14:])
    last = recent[-1]
    atr_pct = atr / last.close * 100.0 if atr else 0.0
    ranges = [bar.high - bar.low for bar in recent]
    overlaps = []
    for previous, current in zip(recent, recent[1:]):
        shared = max(0.0, min(previous.high, current.high) - max(previous.low, current.low))
        overlaps.append(min(1.0, shared / max(min(previous.high - previous.low, current.high - current.low), 1e-12)))
    directions = [1 if bar.close > bar.open else -1 if bar.close < bar.open else 0 for bar in recent]
    alternation = sum(left != right for left, right in zip(directions, directions[1:])) / max(len(directions) - 1, 1)
    envelope = max(bar.high for bar in recent) - min(bar.low for bar in recent)
    envelope_pct = envelope / last.close * 100.0
    net_return_pct = (last.close / recent[0].open - 1.0) * 100.0
    efficiency = abs(last.close - recent[0].open) / max(sum(ranges), 1e-12)
    midpoint = (max(bar.high for bar in recent) + min(bar.low for bar in recent)) / 2.0
    midpoint_band = max(envelope * 0.12, atr * 0.25)
    midpoint_returns = sum(abs(bar.close - midpoint) <= midpoint_band for bar in recent)

    upper_wick_share = _mean([
        (bar.high - max(bar.open, bar.close)) / max(bar.high - bar.low, 1e-12) for bar in recent
    ])
    rejection_closes = sum(
        (bar.high - bar.close) / max(bar.high - bar.low, 1e-12) >= 0.55 for bar in recent
    )
    red_volume_share = sum(bar.volume for bar in recent if bar.close < bar.open) / max(sum(bar.volume for bar in recent), 1e-12)
    first_half_high = max(bar.high for bar in recent[: max(2, len(recent) // 2)])
    second_half_high = max(bar.high for bar in recent[max(2, len(recent) // 2) :])
    high_continuation_pct = (second_half_high / first_half_high - 1.0) * 100.0

    prior_return_pct = (recent[0].open / history[0].open - 1.0) * 100.0
    recent_high = max(bar.high for bar in recent)
    recent_low = min(bar.low for bar in recent)
    close_position = (last.close - recent_low) / max(recent_high - recent_low, 1e-12)
    up_drawdown_atr = (recent_high - last.close) / max(atr, 1e-12)
    down_bounce_atr = (last.close - recent_low) / max(atr, 1e-12)
    largest_bear_body_atr = max((bar.open - bar.close) / max(atr, 1e-12) for bar in recent)
    largest_bull_body_atr = max((bar.close - bar.open) / max(atr, 1e-12) for bar in recent)

    flat_width = envelope_pct <= max(1.5, atr_pct * 4.0)
    range_structure = bool(
        flat_width
        and _mean(overlaps) >= 0.62
        and efficiency <= 0.30
        and abs(net_return_pct) <= max(1.0, atr_pct * 3.0)
        and (_mean(overlaps) >= 0.70 or efficiency <= 0.20 or envelope_pct <= 0.90)
    )
    chop = bool(flat_width and _mean(overlaps) < 0.70 and efficiency > 0.20 and alternation < 0.40)
    failed_breakout, failed_direction, failed_boundary = _failed_breakout(bars, observation_start, atr)

    up_spike = prior_return_pct >= 5.0 or (recent_high / recent[0].open - 1.0) * 100.0 >= 4.0
    down_spike = prior_return_pct <= -5.0 or (1.0 - recent_low / recent[0].open) * 100.0 >= 4.0
    post_spike_up = base_regime != "DOWN" and up_spike and close_position <= 0.65 and up_drawdown_atr >= 0.65 and (largest_bear_body_atr >= 0.55 or efficiency <= 0.20)
    post_spike_down = base_regime != "UP" and down_spike and close_position >= 0.35 and down_bounce_atr >= 0.65 and (largest_bull_body_atr >= 0.55 or efficiency <= 0.20)
    post_spike = bool(post_spike_up or post_spike_down)

    # A fast probe through a micro boundary followed by a full rotation is a
    # failed directional attempt even when a much older 16-bar extreme makes
    # the broad range too wide to show the break.
    rotation_reentry = bool(
        base_regime in {"UP", "DOWN"}
        and abs(prior_return_pct) < 3.0
        and abs(net_return_pct) < 4.0
        and envelope_pct >= 2.0
        and 0.18 <= efficiency <= 0.30
        and alternation >= 0.65
    )
    failed_breakout = failed_breakout or rotation_reentry

    distribution = bool(
        base_regime == "UP"
        and prior_return_pct >= 5.0
        and envelope_pct <= 2.5
        and 0.0 <= net_return_pct <= max(1.0, atr_pct * 2.0)
        and efficiency < 0.14
        and high_continuation_pct <= max(0.15, atr_pct * 0.35)
        and (rejection_closes >= 2 or red_volume_share >= 0.45)
    )
    extended_context = max(abs(prior_return_pct), abs(net_return_pct), envelope_pct) >= max(4.0, atr_pct * 3.0)
    late_confirmation = bool(
        base_regime in {"UP", "DOWN"}
        and extended_context
        and efficiency <= 0.20
        and not post_spike
        and not distribution
        and (not failed_breakout or envelope_pct <= 2.5)
    )
    follow_through = bool(abs(net_return_pct) >= max(1.5, atr_pct * 2.0) and efficiency >= 0.22)
    direction = "UP" if net_return_pct > 0 else "DOWN" if net_return_pct < 0 else "UNKNOWN"
    structural_direction = direction if follow_through else "UNKNOWN"
    exhaustion = bool(distribution or (extended_context and not follow_through and (rejection_closes >= 3 or upper_wick_share >= 0.35)))

    reasons: list[str] = []
    def add(code: str, condition: bool) -> None:
        if condition and code not in reasons:
            reasons.append(code)

    add("RANGE_STRUCTURE_DOMINATES_INDICATORS", range_structure and base_regime in {"UP", "DOWN", "UNKNOWN"})
    add("WEAK_DIRECTIONAL_FOLLOW_THROUGH", not follow_through)
    add("HIGH_OVERLAP_CHOP", _mean(overlaps) >= 0.70 and efficiency <= 0.30 or range_structure and _mean(overlaps) >= 0.62)
    add("MID_RANGE_RETURN", midpoint_returns >= 2 and range_structure)
    add("BOUNDARY_REJECTION_WITHOUT_BREAKOUT", failed_breakout)
    add("DISTRIBUTION_REJECTION_CLUSTER", distribution)
    add("UPPER_WICK_SUPPLY_PRESSURE", distribution and upper_wick_share >= 0.25)
    add("FAILED_HIGH_CONTINUATION", distribution and high_continuation_pct <= 0.15)
    add("BEARISH_VOLUME_REJECTION", distribution and red_volume_share >= 0.45)
    add("MOMENTUM_DIVERGENCE_AT_HIGH", distribution and efficiency < 0.14)
    add("POST_SPIKE_COUNTER_CANDLE", post_spike and (largest_bear_body_atr >= 0.55 or largest_bull_body_atr >= 0.55))
    add("IMPULSE_HIGH_REJECTION", post_spike_up)
    add("PULLBACK_AFTER_VERTICAL_MOVE", post_spike)
    add("NO_CONTINUATION_AFTER_SPIKE", post_spike)
    add("MICRO_STRUCTURE_BROKEN_AFTER_SPIKE", post_spike and (up_drawdown_atr >= 1.0 or down_bounce_atr >= 1.0))
    add("FAILED_BREAKOUT_RANGE_REENTRY", failed_breakout)
    add("BREAKOUT_HOLD_FAILED", failed_breakout)
    add("RETURNED_INSIDE_CONFIRMED_RANGE", failed_breakout)
    add("DIRECTIONAL_BREAKOUT_INVALIDATED", failed_breakout)
    add("LATE_DIRECTIONAL_CONFIRMATION", late_confirmation)
    add("MOVE_ALREADY_EXTENDED", late_confirmation or extended_context)
    add("POOR_REWARD_SPACE_AFTER_CONFIRMATION", late_confirmation)
    add("CONFIRMATION_NEAR_LOCAL_EXTREME", late_confirmation and (close_position >= 0.75 or close_position <= 0.25))
    add("EXHAUSTION_SIGNS_AFTER_CONFIRMATION", late_confirmation and rejection_closes >= 2)
    add("CONTROLLED_PULLBACK_CONTINUATION", follow_through and not exhaustion and _mean(overlaps) >= 0.55)
    add("BREAKOUT_HELD_WITH_FOLLOW_THROUGH", follow_through and not failed_breakout)
    add("EXTENDED_MOVE_EXHAUSTION_RISK", exhaustion)
    add("CLIMAX_VOLUME_WITHOUT_FOLLOW_THROUGH", exhaustion and red_volume_share >= 0.45)
    add("WICK_REJECTION_AFTER_EXTENSION", exhaustion and rejection_closes >= 2)

    return {
        "stage": STAGE,
        "research_only": True,
        "data_sufficient": True,
        "range_structure": range_structure,
        "choppy_structure": chop,
        "distribution": distribution,
        "post_spike_pullback": post_spike,
        "range_reentry": failed_breakout,
        "late_confirmation_risk": late_confirmation,
        "impulse_exhaustion": exhaustion,
        "impulse_extension": follow_through and extended_context and not exhaustion,
        "structural_follow_through": follow_through,
        "structural_direction": structural_direction,
        "failed_breakout_direction": failed_direction,
        "failed_breakout_boundary": None if failed_boundary is None else _round(failed_boundary),
        "reason_codes": reasons,
        "metrics": {
            "observation_bars": observation_bars,
            "atr_pct": _round(atr_pct),
            "envelope_pct": _round(envelope_pct),
            "net_return_pct": _round(net_return_pct),
            "prior_return_pct": _round(prior_return_pct),
            "high_low_overlap": _round(_mean(overlaps)),
            "directional_efficiency": _round(efficiency),
            "directional_alternation": _round(alternation),
            "midpoint_returns": midpoint_returns,
            "upper_wick_share": _round(upper_wick_share),
            "red_volume_share": _round(red_volume_share),
            "high_continuation_pct": _round(high_continuation_pct),
            "close_position": _round(close_position),
        },
        "causal_audit": {
            "future_bars_used": False,
            "last_observed_timestamp": last.timestamp.isoformat(),
        },
        "safety": {
            "trade_signal_created": False,
            "setup_created": False,
            "runtime_decision_changed": False,
        },
    }


__all__ = ["RESEARCH_ONLY", "STAGE", "StructureBar", "diagnose_market_structure"]
