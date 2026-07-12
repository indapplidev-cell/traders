# ENGINE-TREND-03 - Altunina Trend, Impulse and Correction Foundation

## Status

`PASS`

## Purpose

This stage implements the second book-based evidence block for the clean `engine_trend` module. The source is T. M. Altunina technical analysis methodology for trend, impulse, correction, pullback, progress, and structural context.

## Created files

- `app/market_reader/engine_trend/altunina_trend_context.py`
- `tests/test_engine_trend_03_altunina_trend_context.py`

## Updated files

- `app/market_reader/engine_trend/__init__.py`

## Implemented

- swing point detection and stable ordering
- normalization to alternating structural pivots
- price leg construction
- full-sequence structural direction classification with noise tolerance
- trend line summary anchored to structural lows or highs
- fail-closed calendar duration and hierarchy classification
- bounded strength, consistency, and progress scores
- directional impulse and correction summary
- safe pullback depth calculation using the 38, 50, and 62 percent book levels
- independent previous-pivot preservation check
- Altunina evidence and reason codes
- explicit metadata separating book rules from derived engine heuristics
- dictionary export

## Reason codes added

All 18 Altunina codes specified by the stage are implemented, covering availability, structural direction, trend quality, impulse dominance, pullback depth, progress, and conflict.

## Book alignment correction

The correction limit now follows the source text: a pullback at or below 62 percent of the preceding impulse remains eligible for correction context. A pullback above 62 percent produces structural-break warning evidence. Exact boundary comparison is tolerant of floating-point representation.

The significant 38, 50, and 62 percent retracement levels are exposed in the impulse/correction summary. The nearest level is included as descriptive context and is not a forecast.

## Book rules and derived heuristics

The source describes prevailing trend, trend duration, impulse direction, opposite correction, and the significant correction levels. It does not prescribe the local-neighbor swing detector, numeric score formulas, score thresholds, noise tolerance, or evidence contributions used here.

Every evidence item therefore contains:

- `method_origin`, distinguishing a book rule from a derived engine heuristic
- `contribution_origin = ENGINE_TREND_DERIVED_HEURISTIC`

The context summary also marks swing detection and all three scores as derived heuristics.

## Trend foundation additions

- Classification examines every consecutive swing high and every consecutive swing low.
- Consecutive pivots of the same type are reduced to the more extreme pivot before legs are built.
- A bullish trend line is anchored to structural lows; a bearish trend line is anchored to structural highs.
- Calendar duration is classified only when timestamps can be parsed reliably.
- Primary, intermediate, and minor hierarchy roles are returned only for unambiguous book-guided ranges; other windows remain `UNKNOWN`.
- Pullback invalidation checks both the 62 percent book limit and preservation of the previous structural pivot.

## What this stage does not do

- no final market state decision
- no support or resistance zones
- no breakout or retest logic
- no false-breakout logic
- no Schwager logic
- no trading instruction
- no L2 integration

## Safety

No trading logic was added. The module returns structural evidence only and does not return the final engine result contract. The foundation safety contract remains unchanged and fail-closed.

## Checks

- py_compile: PASS
- targeted tests: PASS
- forbidden trading scan: PASS
- old L1 import scan: PASS
- staged diff check: PASS

## Next stage

`ENGINE-TREND-04 — Schwager Range, Levels and False Breakout Foundation`

The next stage should implement practical chart-structure protection from Jack Schwager without using the old L1.
