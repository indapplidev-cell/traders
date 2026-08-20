"""Causal entry-quality projection for the public engine-analysis contract."""

from __future__ import annotations

from typing import Any

from app.engine_analysis.impulse_phase_diagnostics import (
    ImpulseDiagnosticInput,
    MIN_BARS,
    diagnose_impulse_phase,
)
from app.engine_analysis.analysis_contract import AnalysisWindowConfig
from app.engine_analysis.market_hypothesis import HypothesisStatus
from app.engine_analysis.regime_composer import RegimeComposerOutput
from app.engine_analysis.schwager_range_context import ZoneType


def build_analysis_quality_basis(
    output: RegimeComposerOutput,
    config: AnalysisWindowConfig | None = None,
) -> dict[str, Any] | None:
    """Build entry quality from the same closed candles used by the composer.

    Invalid/insufficient composer results have no matrix and therefore no honest
    quality basis.  In that case callers retain ``None`` rather than inventing a
    tier.
    """

    matrix = output.matrix
    if matrix is None or len(matrix.unified_context.candles) < MIN_BARS:
        return None

    context = matrix.unified_context
    hypotheses = matrix.hypothesis_result
    confirmed = tuple(
        item for item in hypotheses.hypotheses
        if item.status is HypothesisStatus.CONFIRMED
    )
    dominant = hypotheses.dominant_hypothesis
    confirmation_at = None
    if dominant is not None and dominant.confirmation_index is not None:
        index = int(dominant.confirmation_index)
        if 0 <= index < len(context.candles):
            confirmation_at = context.candles[index].timestamp

    schwager = context.schwager_context
    trading_range = schwager.trading_range
    range_lower = trading_range.lower_boundary if trading_range.is_detected else None
    range_upper = trading_range.upper_boundary if trading_range.is_detected else None

    support = None
    resistance = None
    for zone in schwager.zones:
        zone_type = zone.current_zone_type or zone.zone_type
        if zone_type is ZoneType.SUPPORT:
            support = max(support, zone.upper_price) if support is not None else zone.upper_price
        elif zone_type is ZoneType.RESISTANCE:
            resistance = min(resistance, zone.lower_price) if resistance is not None else zone.lower_price

    diagnostic = diagnose_impulse_phase(ImpulseDiagnosticInput(
        symbol=output.result.symbol,
        timeframe=output.result.interval,
        cutoff=context.candles[-1].timestamp,
        market_regime=output.result.market_regime.value,
        final_action="NO_ACTION",
        candles=context.candles,
        lookback_bars=min(
            (config.impulse_lookback_candles if config else 96),
            len(context.candles),
        ),
        minimum_required_bars=min(
            MIN_BARS,
            (config.impulse_lookback_candles if config else 96),
        ),
        confirmed_hypotheses=tuple(item.hypothesis_type.value for item in confirmed),
        directional_confirmation_at=confirmation_at,
        breakout_status=schwager.breakout_context.status.value,
        successful_retest=bool(schwager.polarity_flip_context.held),
        range_lower=range_lower,
        range_upper=range_upper,
        resistance=resistance,
        support=support,
        evidence_conflicted=matrix.confluence_conflict.conflict_level.value in {"MEDIUM", "HIGH"},
    ))
    quality = diagnostic["entry_quality"]
    return {
        "impulse_phase": diagnostic["impulse_phase"],
        "entry_quality": quality["value"],
        "entry_quality_reason_codes": list(quality["reason_codes"]),
        "impulse_context": diagnostic["impulse_context"],
        "human_explanation": diagnostic["human_explanation"],
        "causal_audit": diagnostic.get("causal_audit", {
            "future_bars_used": False,
        }),
        "source_stage": diagnostic["stage"],
        "schema_version": diagnostic["schema_version"],
    }
