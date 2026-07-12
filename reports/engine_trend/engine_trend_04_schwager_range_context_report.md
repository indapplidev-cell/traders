# ENGINE-TREND-04 - Schwager Range, Levels and False Breakout Foundation

## Status

`PASS`

## Purpose

This stage implements the third book-based evidence block for the clean `engine_trend` module. It applies Jack Schwager practical chart-analysis concepts to ranges, support and resistance zones, boundary movement, retests, polarity flips, and false breakouts.

## Created files

- `app/market_reader/engine_trend/schwager_range_context.py`
- `tests/test_engine_trend_04_schwager_range_context.py`

## Updated files

- `app/market_reader/engine_trend/__init__.py`

## Implemented

- support and resistance zone clustering from swing points
- zone bands with source indexes, touch counts, and relative width
- trading range detection and inside-close ratio
- upper and lower boundary context
- upward and downward boundary attempts
- follow-through confirmation and absence context
- price-returned-to-range and false-breakout context
- retest and polarity-flip context
- Schwager evidence, reason codes, summaries, and dictionary export

## Reason codes added

- `SCHWAGER_SUPPORT_ZONE_IDENTIFIED`
- `SCHWAGER_RESISTANCE_ZONE_IDENTIFIED`
- `SCHWAGER_SUPPORT_ZONE_HELD`
- `SCHWAGER_RESISTANCE_ZONE_HELD`
- `SCHWAGER_ZONE_TOO_WIDE`
- `SCHWAGER_ZONE_OVERLAP_CONFLICT`
- `SCHWAGER_INSUFFICIENT_LEVEL_TOUCHES`
- `SCHWAGER_TRADING_RANGE_DETECTED`
- `SCHWAGER_PRICE_INSIDE_RANGE`
- `SCHWAGER_RANGE_UPPER_BOUNDARY_HELD`
- `SCHWAGER_RANGE_LOWER_BOUNDARY_HELD`
- `SCHWAGER_RANGE_NOT_CONFIRMED`
- `SCHWAGER_BULLISH_RANGE_BREAKOUT_CONTEXT`
- `SCHWAGER_BEARISH_RANGE_BREAKDOWN_CONTEXT`
- `SCHWAGER_BREAKOUT_REQUIRES_CONFIRMATION`
- `SCHWAGER_BREAKOUT_FOLLOW_THROUGH_CONFIRMED`
- `SCHWAGER_BREAKOUT_NO_FOLLOW_THROUGH`
- `SCHWAGER_BREAKOUT_RETEST_HELD`
- `SCHWAGER_BREAKOUT_RETEST_FAILED`
- `SCHWAGER_RESISTANCE_TURNED_SUPPORT`
- `SCHWAGER_SUPPORT_TURNED_RESISTANCE`
- `SCHWAGER_POLARITY_FLIP_CONFIRMED`
- `SCHWAGER_POLARITY_FLIP_FAILED`
- `SCHWAGER_FALSE_BREAKOUT_UP`
- `SCHWAGER_FALSE_BREAKOUT_DOWN`
- `SCHWAGER_PRICE_RETURNED_TO_RANGE`

## What this stage does not do

- no final market state decision
- no book evidence matrix or final composer
- no runtime JSON export
- no L2 integration
- no trading instruction

## Safety

No trading logic was added. `engine_trend` remains fail-closed through its foundation safety contract:

- `trade_signal = NOT_EVALUATED`
- `safe_for_runtime_trading = false`

No old L1 module is imported by the new context.

## Checks

- py_compile: PASS
- targeted tests: PASS
- forbidden trading scan: PASS
- old L1 import scan: PASS
- git diff --cached --check: PASS

## Next stage

`ENGINE-TREND-05 — Book Evidence Matrix Foundation`

The next stage should combine Nison, Altunina, and Schwager evidence into one book-based evidence matrix without making the final market state decision.
