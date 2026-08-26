"""Historical cutoff selection that never substitutes later microstructure."""

from __future__ import annotations

from dataclasses import dataclass


NOT_REPLAYABLE_WITHOUT_FUTURE_LEAKAGE = "NOT_REPLAYABLE_WITHOUT_FUTURE_LEAKAGE"


@dataclass(frozen=True, slots=True)
class HistoricalMicrostructureCapture:
    captured_at_ms: int
    bid: float
    ask: float
    spread_bps: float
    depth_impact_bps: float
    source: str


@dataclass(frozen=True, slots=True)
class HistoricalMicrostructureSelection:
    replayable: bool
    capture: HistoricalMicrostructureCapture | None
    reason: str | None


def select_historical_microstructure(
    captures: tuple[HistoricalMicrostructureCapture, ...],
    *, decision_cutoff_ms: int, maximum_age_ms: int,
) -> HistoricalMicrostructureSelection:
    if maximum_age_ms <= 0:
        raise ValueError("maximum age must be positive")
    eligible = [
        item for item in captures
        if 0 <= decision_cutoff_ms - item.captured_at_ms <= maximum_age_ms
    ]
    if not eligible:
        return HistoricalMicrostructureSelection(
            False, None, NOT_REPLAYABLE_WITHOUT_FUTURE_LEAKAGE
        )
    return HistoricalMicrostructureSelection(
        True, max(eligible, key=lambda item: item.captured_at_ms), None
    )


def timestamps_are_causal(
    timestamps_ms: tuple[int, ...], *, decision_cutoff_ms: int
) -> bool:
    """Applies equally to candles, swings, targets, quotes, and depth."""
    return all(int(value) <= int(decision_cutoff_ms) for value in timestamps_ms)
