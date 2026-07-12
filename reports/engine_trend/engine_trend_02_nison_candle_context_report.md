# ENGINE-TREND-02 - Nison Candle Morphology and Candlestick Context

## Status

`PASS`

## Purpose

This stage implements the first book-based evidence block for the clean `engine_trend` module. The implemented source is Steve Nison candlestick analysis.

## Created files

- `app/market_reader/engine_trend/candle_morphology.py`
- `app/market_reader/engine_trend/nison_candlestick_context.py`
- `tests/test_engine_trend_02_nison_candle_context.py`

## Updated files

- `app/market_reader/engine_trend/__init__.py`

## Implemented

- candle direction and body/range/shadow measurements
- open and close positions in range with zero-range safety
- doji, spinning top, small body, long body, and strong body morphology
- upper/lower shadow and close-location context
- hammer-like and shooting-star-like shapes requiring context
- bullish and bearish engulfing context
- piercing and dark-cloud context
- doji and small-body window clusters
- bullish and bearish body dominance
- Nison evidence, cautious contributions, reason codes, summaries, and dictionary export

## Reason codes added

- `STRONG_BULLISH_CANDLE_BODY`
- `STRONG_BEARISH_CANDLE_BODY`
- `LONG_UPPER_SHADOW_REJECTION`
- `LONG_LOWER_SHADOW_REJECTION`
- `SMALL_BODY_INDECISION`
- `CLOSE_NEAR_HIGH`
- `CLOSE_NEAR_LOW`
- `DOJI_INDECISION`
- `SPINNING_TOP_INDECISION`
- `DOJI_CLUSTER_FLAT_CONTEXT`
- `SMALL_BODY_CLUSTER`
- `LOW_DIRECTIONAL_PROGRESS`
- `BULLISH_BODY_DOMINANCE`
- `BEARISH_BODY_DOMINANCE`
- `HAMMER_LIKE_SHAPE_CONTEXT_REQUIRED`
- `SHOOTING_STAR_LIKE_SHAPE_CONTEXT_REQUIRED`
- `CANDLE_PATTERN_NEEDS_TREND_CONTEXT`
- `BULLISH_ENGULFING_CONTEXT`
- `BEARISH_ENGULFING_CONTEXT`
- `ENGULFING_WITHOUT_FOLLOW_THROUGH`
- `DARK_CLOUD_BEARISH_CONTEXT`
- `PIERCING_BULLISH_CONTEXT`
- `REVERSAL_PATTERN_NEEDS_FOLLOW_THROUGH`

## What this stage does not do

- no market regime decision
- no trend or level analysis
- no breakout, retest, or false-breakout logic
- no trading instruction
- no L2 integration

## Safety

No trading logic was added. `engine_trend` remains fail-closed through its foundation safety contract: `trade_signal = NOT_EVALUATED` and `safe_for_runtime_trading = false`.

## Checks

- py_compile: PASS
- targeted tests: PASS
- forbidden trading scan: PASS
- old L1 import scan: PASS
- git diff --cached --check: PASS

## Next stage

`ENGINE-TREND-03 — Altunina Trend, Impulse and Correction Foundation`

The next stage should implement technical-analysis structure for trend, impulse, and correction without using the old L1.
