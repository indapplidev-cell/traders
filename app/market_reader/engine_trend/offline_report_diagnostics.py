"""One-way adapter that exposes 28A diagnostics in offline replay artifacts.

This module consumes an already finalized report document.  It is intentionally
not imported by the engine, composer, setup selection, or trading runtime.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from app.market_reader.engine_trend.contextual_diagnostics import (
    ContextualDiagnosticInput,
    DiagnosticZone,
    diagnose_context,
)


def _zone(value: Mapping[str, Any]) -> DiagnosticZone | None:
    zone_type = value.get("current_zone_type") or value.get("zone_type")
    low = value.get("lower_price")
    high = value.get("upper_price")
    if zone_type not in {"SUPPORT", "RESISTANCE"} or low is None or high is None:
        return None
    touches = value.get("touch_count")
    return DiagnosticZone(
        str(zone_type), float(low), float(high), "replay.unified_market_context",
        int(touches) if touches is not None else None,
    )


def _candle_value(candle: Any, name: str) -> float:
    value = candle.get(name) if isinstance(candle, Mapping) else getattr(candle, name)
    return float(value)


def attach_contextual_diagnostics(
    artifact: Mapping[str, Any], *, candles: Sequence[Any] = ()
) -> dict[str, Any]:
    """Return a copy with diagnostics; every pre-existing value is untouched."""

    output = deepcopy(dict(artifact))
    window = output.get("window") if isinstance(output.get("window"), dict) else {}
    composer = output.get("composer") if isinstance(output.get("composer"), dict) else {}
    context = (
        output.get("unified_market_context")
        if isinstance(output.get("unified_market_context"), dict)
        else {}
    )
    range_context = context.get("range") if isinstance(context.get("range"), dict) else None
    breakout = context.get("breakout_state") if isinstance(context.get("breakout_state"), dict) else None
    indicators = (
        context.get("technical_indicators")
        if isinstance(context.get("technical_indicators"), dict)
        else None
    )
    raw_zones = context.get("active_support_resistance_zones")
    zones_observable = isinstance(raw_zones, list)
    zones = tuple(
        zone
        for value in (raw_zones if zones_observable else [])
        if isinstance(value, Mapping) and (zone := _zone(value)) is not None
    )
    price_observable = bool(candles)
    last_close = _candle_value(candles[-1], "close") if price_observable else None
    highs = [_candle_value(item, "high") for item in candles]
    lows = [_candle_value(item, "low") for item in candles]

    hypotheses = output.get("hypotheses")
    hypotheses_observable = isinstance(hypotheses, dict)
    confirmed = hypotheses.get("CONFIRMED", []) if hypotheses_observable else []
    confirmed_types = tuple(
        str(item.get("hypothesis_type"))
        for item in confirmed
        if isinstance(item, Mapping) and item.get("hypothesis_type")
    )
    conflicted = hypotheses.get("CONFLICTED", []) if hypotheses_observable else []
    conflict_codes = tuple(
        str(code)
        for item in conflicted
        if isinstance(item, Mapping)
        for code in item.get("reason_codes", [])
    )

    diagnostic = diagnose_context(
        ContextualDiagnosticInput(
            symbol=str(window.get("symbol", "UNKNOWN")),
            timeframe=str(window.get("interval", "UNKNOWN")),
            as_of=str(window.get("period_end", "UNKNOWN")),
            source_regime=str(composer.get("regime", "UNKNOWN")),
            source_confidence=float(composer.get("confidence", 0.0)),
            last_close=last_close,
            day_high=max(highs) if highs else None,
            day_low=min(lows) if lows else None,
            atr=float(indicators["atr_14"]) if indicators and indicators.get("atr_14") is not None else None,
            structure=str(context.get("trend_structure")) if context.get("trend_structure") is not None else None,
            zones=zones,
            range_confirmed=bool(range_context.get("is_detected")) if range_context else False,
            range_lower=float(range_context["lower_boundary"]) if range_context and range_context.get("lower_boundary") is not None else None,
            range_upper=float(range_context["upper_boundary"]) if range_context and range_context.get("upper_boundary") is not None else None,
            breakout_status=str(breakout.get("status", "NO_BREAKOUT")) if breakout else "NO_BREAKOUT",
            breakout_direction=str(breakout.get("direction", "NONE")) if breakout else "NONE",
            confirmed_hypotheses=confirmed_types,
            indicator_direction=str(indicators.get("direction", "NEUTRAL")) if indicators else "NEUTRAL",
            indicator_strength="OBSERVED" if indicators and indicators.get("available") else "UNAVAILABLE",
            indicator_reason=",".join(str(code) for code in indicators.get("reason_codes", [])) if indicators else "",
            bullish_votes=int(indicators.get("bullish_votes", 0)) if indicators else 0,
            bearish_votes=int(indicators.get("bearish_votes", 0)) if indicators else 0,
            adx=float(indicators["adx_14"]) if indicators and indicators.get("adx_14") is not None else None,
            conflict_codes=conflict_codes,
            observable_fields={
                "price_position": price_observable,
                "zones": zones_observable,
                "range": range_context is not None,
                "breakout": breakout is not None,
                "indicators": indicators is not None,
                "multi_timeframe": False,
                "hypotheses": hypotheses_observable,
            },
        )
    )
    diagnostic["artifact_contract"] = {
        "attachment_point": "offline_replay_report_after_final_decision",
        "source_fields_mutated": False,
        "setup_eligibility_mutated": False,
        "trade_signal_created": False,
    }
    output["contextual_diagnostics"] = diagnostic
    return output
