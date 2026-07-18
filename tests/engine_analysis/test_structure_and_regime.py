from __future__ import annotations

import pytest

from app.engine_analysis import (
    AltuninaStructureDirection,
    EngineAnalysisRegime,
    SwingPoint,
    SwingPointType,
    classify_structure_direction,
    run_engine_analysis,
)
from app.engine_analysis.impulse_phase_conflict_resolver import PhaseConflictInput, resolve_phase_conflicts


def _pivots(highs: list[float], lows: list[float]) -> list[SwingPoint]:
    output: list[SwingPoint] = []
    for index, (low, high) in enumerate(zip(lows, highs)):
        output.append(SwingPoint(index * 2, str(index * 2), low, SwingPointType.LOW))
        output.append(SwingPoint(index * 2 + 1, str(index * 2 + 1), high, SwingPointType.HIGH))
    return output


@pytest.mark.parametrize(
    ("highs", "lows", "expected"),
    [
        ([11, 13, 15], [8, 9, 10], AltuninaStructureDirection.BULLISH_STRUCTURE),
        ([15, 13, 11], [10, 9, 8], AltuninaStructureDirection.BEARISH_STRUCTURE),
        ([11, 13, 12], [8, 7, 9], AltuninaStructureDirection.SIDEWAYS_STRUCTURE),
    ],
)
def test_hh_hl_lh_ll_and_sideways_structure(highs, lows, expected):
    """Given confirmed pivots, when structure is classified, then HH/HL, LH/LL, or range wins."""
    assert classify_structure_direction(_pivots(highs, lows)) is expected


def test_insufficient_pivots_are_unknown():
    """Given fewer than two highs and lows, when classified, then structure remains unconfirmed."""
    one = [SwingPoint(0, "0", 10, SwingPointType.LOW)]
    assert classify_structure_direction(one) is AltuninaStructureDirection.UNCLEAR_STRUCTURE


@pytest.mark.parametrize(
    ("kind", "expected"),
    [("up", "UP"), ("down", "DOWN"), ("range", "FLAT"), ("unknown", "UNKNOWN")],
)
def test_composer_covers_all_public_regimes(candle_factory, kind, expected):
    """Given current market shapes, when composed, then every public regime is reachable safely."""
    result = run_engine_analysis("BTCUSDT", "15m", candle_factory(kind)).composer_output.result
    assert result.market_regime is EngineAnalysisRegime(expected)
    assert result.safety.safe_for_runtime_trading is False


def test_no_confirmed_hypothesis_has_conservative_reason(candle_factory):
    """Given conflicting/noisy evidence, when composed, then UNKNOWN carries stable fallback reasons."""
    result = run_engine_analysis("BTCUSDT", "15m", candle_factory("unknown")).composer_output.result
    assert "COMPOSER_NO_CONFIRMED_HYPOTHESIS" in result.reason_codes
    assert "COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN" in result.reason_codes


def test_conflict_resolver_prefers_structure_without_action():
    """Given trend/range conflict, when resolved, then fallback is conservative and non-actionable."""
    resolved = resolve_phase_conflicts(
        PhaseConflictInput("UP", "IMPULSE_DETECTED", "GOOD", {"range_structure": True, "reason_codes": []})
    )
    assert resolved["analysis_regime"] == "FLAT"
    assert resolved["entry_quality"] == "INVALID"
    assert resolved["safety"]["final_action"] == "NO_ACTION"
    assert "PHASE_CONFLICT_RESOLVED_TO_RANGE" in resolved["reason_codes"]
