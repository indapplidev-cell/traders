# BOOK-L1-27 - L1-L2 Regime Alignment Review

## Status

`PASS_WITH_ALIGNMENT_WARNINGS`

## Purpose

This stage reviews whether BOOK-L2 preserves and explains BOOK-L1 regimes correctly.

It does not change L1 or L2 logic.

## Request

| Field | Value |
|---|---|
| Symbols | BTCUSDT, ETHUSDT, SOLUSDT |
| Interval | 15m |

## Source Artifacts

| Artifact | Path |
|---|---|
| Quality review JSON | reports/book_l1/market_reader_15m_quality_review.json |
| L1 timeline JSON | reports/book_l1/timeline_preview.json |
| L2 context JSON | reports/book_l2/timeline_context.json |

## Main Finding

High-confidence L1 FLAT becomes L2 UNKNOWN/SKIP for BTCUSDT, ETHUSDT.

## Overall Alignment

| Field | Value |
|---|---|
| L2 overall state | UNKNOWN |
| Global findings | L2_OVERALL_UNKNOWN_DESPITE_L1_FLAT_SYMBOLS, L2_SKIPS_FLAT_CONTEXT, ALL_SYMBOLS_SKIPPED, NO_OBSERVATION_CANDIDATES, CONTRACT_ALIGNMENT_NEEDS_REVIEW |

## Per-Symbol Alignment

| Symbol | L1 Regime | L1 Confidence | L2 Bucket | L2 Skip | Alignment Status | Main Findings |
|---|---|---:|---|---|---|---|
| BTCUSDT | FLAT | 0.94 | UNKNOWN | true | WARNING | L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP, L2_SKIPS_FLAT_CONTEXT, L2_FLAT_CONTEXT_NOT_OBSERVABLE, CONTRACT_ALIGNMENT_NEEDS_REVIEW, L2_QUALITY_LOW_DESPITE_L1_CONFIDENCE |
| ETHUSDT | FLAT | 0.87 | UNKNOWN | true | WARNING | L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP, L2_SKIPS_FLAT_CONTEXT, L2_FLAT_CONTEXT_NOT_OBSERVABLE, CONTRACT_ALIGNMENT_NEEDS_REVIEW, L2_QUALITY_LOW_DESPITE_L1_CONFIDENCE |
| SOLUSDT | UNKNOWN | 0.00 | UNKNOWN | true | WARNING | L1_UNKNOWN_PROPAGATED_TO_L2_SKIP |

## Symbol Details

### BTCUSDT

#### L1

- Regime: `FLAT`
- Confidence: `0.94`
- Directional bias: `NEUTRAL`
- Trend strength: `NONE`
- Timeline stability: `CHANGING`
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

- Received regime: `FLAT`
- Received confidence: `0.94`
- Overall state: `UNKNOWN`
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

#### Alignment interpretation

L1 classifies the symbol as high-confidence FLAT, but L2 keeps the symbol in UNKNOWN/SKIP context.

#### Recommended next focus

- inspect L2 flat-context handling
- decide whether high-confidence FLAT can be observe-only context
- inspect L1-to-L2 contract mapping for market_regime/confidence
- inspect L2 quality scoring for high-confidence FLAT

### ETHUSDT

#### L1

- Regime: `FLAT`
- Confidence: `0.87`
- Directional bias: `NEUTRAL`
- Trend strength: `NONE`
- Timeline stability: `CHANGING`
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

- Received regime: `FLAT`
- Received confidence: `0.87`
- Overall state: `UNKNOWN`
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

#### Alignment interpretation

L1 classifies the symbol as high-confidence FLAT, but L2 keeps the symbol in UNKNOWN/SKIP context.

#### Recommended next focus

- inspect L2 flat-context handling
- decide whether high-confidence FLAT can be observe-only context
- inspect L1-to-L2 contract mapping for market_regime/confidence
- inspect L2 quality scoring for high-confidence FLAT

### SOLUSDT

#### L1

- Regime: `UNKNOWN`
- Confidence: `0.00`
- Directional bias: `UNKNOWN`
- Trend strength: `UNKNOWN`
- Timeline stability: `UNSTABLE`
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

- Received regime: `UNKNOWN`
- Received confidence: `0.00`
- Overall state: `UNKNOWN`
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

#### Alignment interpretation

L1 UNKNOWN is propagated to L2 skip context.

#### Recommended next focus

- confirm UNKNOWN propagation remains expected

## What This Means

The pipeline is technically stable, but high-confidence L1 FLAT currently becomes L2 UNKNOWN/SKIP. This is an alignment/interpretation issue.

## Safety

- read_only: `true`
- market_logic_changed: `false`
- l2_rules_changed: `false`
- trading_signal: `NOT_EVALUATED`
- safe_for_runtime_trading: `false`
- live_trading_connected: `false`

## Recommended Next Stage

`BOOK-L1-28 - FLAT Context Alignment Diagnostic`

## Conclusion

Do not move to BOOK-L3, edge validation, interval expansion, or runtime execution yet.

First, review the interpretation boundary between L1 FLAT and L2 context/skip behavior.
