"""Versioned mapping from analysis/setup regimes to empirical bucket regimes."""

from __future__ import annotations

from dataclasses import dataclass


EMPIRICAL_REGIME_MAPPING_VERSION = "empirical-regime-v1"


@dataclass(frozen=True, slots=True)
class EmpiricalRegimeMapping:
    source_regime: str
    normalized_regime: str
    reason: str
    version: str = EMPIRICAL_REGIME_MAPPING_VERSION


_MAPPING = {
    "UP": ("UP", "DIRECTIONAL_REGIME_PRESERVED"),
    "DOWN": ("DOWN", "DIRECTIONAL_REGIME_PRESERVED"),
    "FLAT": ("RANGE", "ENGINE_FLAT_MAPS_TO_SCALPING_RANGE"),
    "RANGE": ("RANGE", "SCALPING_RANGE_PRESERVED"),
    "COMPRESSION": ("COMPRESSION", "SCALPING_VOLATILITY_REGIME_PRESERVED"),
    "EXPANSION": ("EXPANSION", "SCALPING_VOLATILITY_REGIME_PRESERVED"),
    "UNKNOWN": ("UNKNOWN", "SOURCE_REGIME_UNKNOWN"),
}


def normalize_empirical_regime(value: object) -> EmpiricalRegimeMapping:
    source = str(value or "UNKNOWN").strip().upper() or "UNKNOWN"
    normalized, reason = _MAPPING.get(
        source, ("UNKNOWN", "UNSUPPORTED_SOURCE_REGIME_QUARANTINED")
    )
    return EmpiricalRegimeMapping(source, normalized, reason)


__all__ = (
    "EMPIRICAL_REGIME_MAPPING_VERSION",
    "EmpiricalRegimeMapping",
    "normalize_empirical_regime",
)
