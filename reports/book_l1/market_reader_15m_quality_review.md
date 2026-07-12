# BOOK-L1-26 - 15m Market Reader Quality Review

## Status

`PASS_WITH_QUALITY_WARNINGS`

## Purpose

This stage reviews the quality of the current 15m Market Reader output.

It does not change market analysis logic.

## Request

| Field | Value |
|---|---|
| Symbols | BTCUSDT, ETHUSDT, SOLUSDT |
| Interval | 15m |
| Window size | 300 |
| Window count | 4 |
| Min candles | 50 |

## Source Artifacts

| Artifact | Path |
|---|---|
| L1 timeline JSON | reports/book_l1/timeline_preview.json |
| L2 context JSON | reports/book_l2/timeline_context.json |
| L2 answer Markdown | reports/book_l2/l1_l2_interval_answer.md |
| 15m stabilization JSON | reports/book_data/market_reader_15m_stabilization.json |

## Current 15m Answer

| Field | Value |
|---|---|
| L2 overall state | UNKNOWN |
| Observation candidates | none |
| Skip candidates | SOLUSDT, BTCUSDT, ETHUSDT |

## Global Findings

- ALL_SYMBOLS_SKIPPED
- NO_OBSERVATION_CANDIDATES
- STABLE_PIPELINE_BUT_WEAK_CONTEXT

## Per-Symbol Review

| Symbol | L1 Regime | Confidence | L2 Bucket | L2 Quality | Skip | Main Findings |
|---|---|---:|---|---|---|---|
| BTCUSDT | FLAT | 0.94 | UNKNOWN | SKIP | true | UNKNOWN_REGIME_DOMINANT, RANGE_DOMINANT, NO_ACTIVE_BREAKOUT, CONFLICTING_TECHNICAL_CONTEXT |
| ETHUSDT | FLAT | 0.87 | UNKNOWN | SKIP | true | UNKNOWN_REGIME_DOMINANT, RANGE_DOMINANT, NO_ACTIVE_BREAKOUT, CONFLICTING_TECHNICAL_CONTEXT |
| SOLUSDT | UNKNOWN | 0.00 | UNKNOWN | SKIP | true | UNKNOWN_REGIME_DOMINANT, LOW_CONFIDENCE, MIXED_TREND_STRUCTURE, NO_ACTIVE_BREAKOUT, CONFLICTING_TECHNICAL_CONTEXT |

## Symbol Details

### BTCUSDT

#### L1

- Market regime: `FLAT`
- Confidence: `0.94`
- Directional bias: `NEUTRAL`
- Trend strength: `NONE`
- Stability: `CHANGING`
- Last transition: `NO_CHANGE`
- Reason codes:
  - MARKET_READER_ORCHESTRATED
  - MARKET_REGIME_COMPOSED
  - COMPOSER_FLAT_RANGE_DOMINANT
  - UP_TREND_STRUCTURE
  - HIGHER_HIGHS
  - HIGHER_LOWS
  - RANGE_STRUCTURE_DETECTED
  - RANGE_WIDTH_ACCEPTABLE
  - LOW_CLOSE_DRIFT_INSIDE_RANGE
  - SUPPORT_TOUCHES_DETECTED
  - RESISTANCE_TOUCHES_DETECTED
  - NO_CLOSE_BREAKOUT
  - PRICE_INSIDE_RANGE
  - EMA_TREND_MIXED
  - FAST_EMA_BELOW_SLOW_EMA
  - PRICE_BELOW_EMAS
  - ATR_NORMAL_VOLATILITY

#### L2

- Bucket: `UNKNOWN`
- Skip candidate: `true`
- Quality score: `0.20`
- Quality grade: `SKIP`
- Main reason: Unknown current regime.
- Context reason codes:
  - CONTEXT_RULE_UNMATCHED
  - SKIP_CANDIDATE_CONTEXT
- Quality reason codes:
  - CONTEXT_QUALITY_SCORED
  - QUALITY_CHANGING_CONTEXT_READABLE
  - QUALITY_CURRENT_CONFIDENCE_HIGH
  - QUALITY_LAST_TRANSITION_NO_CHANGE
  - QUALITY_SKIP_CANDIDATE_PENALTY
  - QUALITY_BUCKET_UNKNOWN
  - QUALITY_GRADE_SKIP

#### Quality findings

- UNKNOWN_REGIME_DOMINANT
- RANGE_DOMINANT
- NO_ACTIVE_BREAKOUT
- CONFLICTING_TECHNICAL_CONTEXT

#### Recommended next focus

- review composer unknown decision path
- review range dominance contribution
- review breakout/retest contribution
- review technical context conflicts

### ETHUSDT

#### L1

- Market regime: `FLAT`
- Confidence: `0.87`
- Directional bias: `NEUTRAL`
- Trend strength: `NONE`
- Stability: `CHANGING`
- Last transition: `NO_CHANGE`
- Reason codes:
  - MARKET_READER_ORCHESTRATED
  - MARKET_REGIME_COMPOSED
  - COMPOSER_FLAT_RANGE_DOMINANT
  - UP_TREND_STRUCTURE
  - HIGHER_HIGHS
  - HIGHER_LOWS
  - RANGE_STRUCTURE_DETECTED
  - RANGE_WIDTH_ACCEPTABLE
  - LOW_CLOSE_DRIFT_INSIDE_RANGE
  - SUPPORT_TOUCHES_DETECTED
  - RESISTANCE_TOUCHES_DETECTED
  - NO_CLOSE_BREAKOUT
  - PRICE_INSIDE_RANGE
  - EMA_TREND_MIXED
  - FAST_EMA_ABOVE_SLOW_EMA
  - PRICE_AROUND_EMA
  - ATR_NORMAL_VOLATILITY

#### L2

- Bucket: `UNKNOWN`
- Skip candidate: `true`
- Quality score: `0.20`
- Quality grade: `SKIP`
- Main reason: Unknown current regime.
- Context reason codes:
  - CONTEXT_RULE_UNMATCHED
  - SKIP_CANDIDATE_CONTEXT
- Quality reason codes:
  - CONTEXT_QUALITY_SCORED
  - QUALITY_CHANGING_CONTEXT_READABLE
  - QUALITY_CURRENT_CONFIDENCE_HIGH
  - QUALITY_LAST_TRANSITION_NO_CHANGE
  - QUALITY_SKIP_CANDIDATE_PENALTY
  - QUALITY_BUCKET_UNKNOWN
  - QUALITY_GRADE_SKIP

#### Quality findings

- UNKNOWN_REGIME_DOMINANT
- RANGE_DOMINANT
- NO_ACTIVE_BREAKOUT
- CONFLICTING_TECHNICAL_CONTEXT

#### Recommended next focus

- review composer unknown decision path
- review range dominance contribution
- review breakout/retest contribution
- review technical context conflicts

### SOLUSDT

#### L1

- Market regime: `UNKNOWN`
- Confidence: `0.00`
- Directional bias: `UNKNOWN`
- Trend strength: `UNKNOWN`
- Stability: `UNSTABLE`
- Last transition: `TO_UNKNOWN`
- Reason codes:
  - MARKET_READER_ORCHESTRATED
  - MARKET_REGIME_COMPOSED
  - COMPOSER_MIXED_OR_WEAK_CONTEXT
  - UP_TREND_STRUCTURE
  - HIGHER_HIGHS
  - HIGHER_LOWS
  - NOT_RANGE_STRUCTURE
  - WEAK_BOUNDARY_TOUCHES
  - NO_CLOSE_BREAKOUT
  - PRICE_INSIDE_RANGE
  - EMA_TREND_MIXED
  - FAST_EMA_ABOVE_SLOW_EMA
  - PRICE_AROUND_EMA
  - ATR_NORMAL_VOLATILITY

#### L2

- Bucket: `UNKNOWN`
- Skip candidate: `true`
- Quality score: `0.00`
- Quality grade: `SKIP`
- Main reason: Unknown current regime.
- Context reason codes:
  - CURRENT_REGIME_UNKNOWN
  - SKIP_CANDIDATE_CONTEXT
- Quality reason codes:
  - CONTEXT_QUALITY_SCORED
  - QUALITY_SKIP_CANDIDATE_PENALTY
  - QUALITY_BUCKET_UNKNOWN
  - QUALITY_CURRENT_REGIME_UNKNOWN
  - QUALITY_UNSTABLE_CONTEXT
  - QUALITY_TRANSITION_TO_UNKNOWN
  - QUALITY_LOW_CONFIDENCE
  - QUALITY_GRADE_SKIP

#### Quality findings

- UNKNOWN_REGIME_DOMINANT
- LOW_CONFIDENCE
- MIXED_TREND_STRUCTURE
- NO_ACTIVE_BREAKOUT
- CONFLICTING_TECHNICAL_CONTEXT

#### Recommended next focus

- review composer unknown decision path
- review trend structure reason codes
- review breakout/retest contribution
- review technical context conflicts
- review low confidence windows

## What This Means

The current 15m pipeline is technically stable, but the Market Reader does not yet produce a strong readable market context for the tested symbols.

This is a quality issue, not a pipeline failure.

## Safety

- read_only: `true`
- market_logic_changed: `false`
- trading_signal: `NOT_EVALUATED`
- safe_for_runtime_trading: `false`
- live_trading_connected: `false`

## Recommended Next Stage

`BOOK-L1-27 - 15m Reason Codes Inspection`

or:

`BOOK-L1-28 - 15m UNKNOWN/FLAT Reduction Diagnostic`

## Conclusion

Continue improving Market Reader quality on `15m`.

Do not move to runtime execution, interval expansion, or BOOK-L3 yet.
