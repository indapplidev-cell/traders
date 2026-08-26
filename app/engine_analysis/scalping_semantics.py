"""5m-only market-description semantics with no trading authority."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from app.engine_market_data.market_data_snapshot import MarketDataSnapshot


class ScalpingMarketRegime(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    RANGE = "RANGE"
    COMPRESSION = "COMPRESSION"
    EXPANSION = "EXPANSION"
    UNKNOWN = "UNKNOWN"


class AnalysisEvidenceStrength(StrEnum):
    STRONG = "STRONG"
    NORMAL = "NORMAL"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"
    NOT_EVALUATED = "NOT_EVALUATED"
    CONFLICTING = "CONFLICTING"
    INVALID = "INVALID"


def _range_ratio(snapshot: MarketDataSnapshot) -> float | None:
    candles = tuple(snapshot.candles)
    if len(candles) < 20:
        return None
    ranges = [float(item.high) - float(item.low) for item in candles]
    recent = sum(ranges[-5:]) / 5
    baseline_values = ranges[-20:-5]
    baseline = sum(baseline_values) / len(baseline_values)
    return recent / baseline if baseline > 0 else None


def _strength(entry_quality: str | None, *, conflicted: bool) -> AnalysisEvidenceStrength:
    if conflicted:
        return AnalysisEvidenceStrength.CONFLICTING
    return {
        "GOOD": AnalysisEvidenceStrength.STRONG,
        "ACCEPTABLE": AnalysisEvidenceStrength.NORMAL,
        "WEAK": AnalysisEvidenceStrength.WEAK,
        "POOR": AnalysisEvidenceStrength.WEAK,
        "INVALID": AnalysisEvidenceStrength.INVALID,
        "NOT_EVALUATED": AnalysisEvidenceStrength.NOT_EVALUATED,
        None: AnalysisEvidenceStrength.UNKNOWN,
        "UNKNOWN": AnalysisEvidenceStrength.UNKNOWN,
    }.get(entry_quality, AnalysisEvidenceStrength.UNKNOWN)


def project_scalping_analysis_semantics(
    analysis: object,
    snapshot: MarketDataSnapshot,
    *,
    compression_ratio: float = 0.75,
    expansion_ratio: float = 1.35,
) -> dict[str, Any]:
    """Project explicit Scalping semantics from the same closed input window."""
    if snapshot.timeframe != "5m" or snapshot.future_bars_used:
        raise ValueError("Scalping analysis semantics require a causal closed 5m snapshot")
    context = getattr(analysis, "analysis_context", None)
    context = context if isinstance(context, dict) else {}
    base_regime = str(getattr(analysis, "regime", None) or "UNKNOWN").upper()
    ratio = _range_ratio(snapshot)
    if not 0 < compression_ratio < 1 < expansion_ratio:
        raise ValueError("invalid Scalping volatility-regime thresholds")
    if ratio is not None and ratio >= expansion_ratio:
        regime = ScalpingMarketRegime.EXPANSION
    elif ratio is not None and ratio <= compression_ratio:
        regime = ScalpingMarketRegime.COMPRESSION
    else:
        regime = {
            "UP": ScalpingMarketRegime.UP,
            "DOWN": ScalpingMarketRegime.DOWN,
            "FLAT": ScalpingMarketRegime.RANGE,
            "RANGE": ScalpingMarketRegime.RANGE,
        }.get(base_regime, ScalpingMarketRegime.UNKNOWN)
    conflict_level = str(
        ((context.get("confluence_conflict") or {}).get("conflict_level") or "")
    ).upper()
    entry_quality = getattr(analysis, "entry_quality", None)
    strength = _strength(entry_quality, conflicted=conflict_level in {"MEDIUM", "HIGH"})
    if strength is AnalysisEvidenceStrength.NOT_EVALUATED:
        reason_codes = ["ENTRY_PATTERN_NOT_PRESENT_AT_DECISION_BOUNDARY"]
        provenance = "CLOSED_5M_IMPULSE_PHASE_DIAGNOSTIC"
    elif strength is AnalysisEvidenceStrength.UNKNOWN:
        reason_codes = ["ENTRY_QUALITY_SOURCE_UNAVAILABLE"]
        provenance = "ANALYSIS_SOURCE_UNAVAILABLE"
    else:
        reason_codes = list(context.get("entry_quality_reason_codes") or [])
        provenance = "CLOSED_5M_ANALYSIS_EVIDENCE"
    return {
        "semantics_version": "scalping-analysis-v1",
        "analysis_role": "MARKET_DESCRIPTION_ONLY",
        "market_regime": regime.value,
        "base_regime": base_regime,
        "entry_evidence_strength": strength.value,
        "entry_evidence_evaluation": {
            "status": strength.value,
            "reason_codes": reason_codes,
            "provenance": provenance,
            "decision_boundary_ms": int(snapshot.closed_until_ms),
        },
        "volatility_state": {
            "recent_to_baseline_range_ratio": ratio,
            "classification": regime.value if regime in {
                ScalpingMarketRegime.COMPRESSION, ScalpingMarketRegime.EXPANSION
            } else "NORMAL",
        },
        "future_bars_used": False,
    }


__all__ = ["AnalysisEvidenceStrength", "ScalpingMarketRegime", "project_scalping_analysis_semantics"]
