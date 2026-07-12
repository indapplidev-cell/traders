# BOOK-L1-28 - FLAT Context Alignment Diagnostic

## Status

`PASS_WITH_FLAT_ALIGNMENT_WARNINGS`

## Purpose

This stage diagnoses how high-confidence L1 `FLAT` should be interpreted by BOOK-L2.

It does not change L1 or L2 logic.

## Request

| Field | Value |
|---|---|
| Symbols | BTCUSDT, ETHUSDT, SOLUSDT |
| Interval | 15m |
| High confidence threshold | 0.80 |

## Source Artifacts

| Artifact | Path |
|---|---|
| Alignment review JSON | reports/book_l1/l1_l2_regime_alignment_review.json |
| Quality review JSON | reports/book_l1/market_reader_15m_quality_review.json |
| L1 timeline JSON | reports/book_l1/timeline_preview.json |
| L2 context JSON | reports/book_l2/timeline_context.json |

## Main Finding

High-confidence L1 FLAT is received by L2 but mapped to UNKNOWN/SKIP.

## FLAT Cases

| Symbol | L1 Regime | Confidence | High Confidence FLAT | L2 Bucket | L2 Skip | Current Behavior |
|---|---|---:|---|---|---|---|
| BTCUSDT | FLAT | 0.94 | true | UNKNOWN | true | L1 FLAT is received by L2 but mapped to UNKNOWN/SKIP. |
| ETHUSDT | FLAT | 0.87 | true | UNKNOWN | true | L1 FLAT is received by L2 but mapped to UNKNOWN/SKIP. |
| SOLUSDT | UNKNOWN | 0.00 | false | UNKNOWN | true | No high-confidence FLAT case for this symbol. |

## Semantic Options Considered

### Option A - FLAT is always skip

High-confidence `FLAT` always remains a skip case.

This is conservative, but L2 should still explain it as `FLAT/SKIP`, not `UNKNOWN/SKIP`.

### Option B - FLAT is valid observe-only context

High-confidence `FLAT` is a valid market context, without becoming an action signal.

This preserves L1 meaning, but requires careful L2 bucket and reason-code handling.

### Option C - FLAT is context but not observation candidate

High-confidence `FLAT` is preserved as market context, but does not enter observation candidates.

This is the recommended safe interpretation for the current project goal.

### Option D - FLAT quality depends on reason codes

`FLAT` becomes valid context only when reason codes show a readable range/flat structure.

This is a useful follow-up after reason-code review.

## Recommended Interpretation

`OPTION_C_FLAT_CONTEXT_NOT_OBSERVATION_CANDIDATE`

Meaning:

High-confidence `FLAT` should not become `UNKNOWN`.

It may remain non-observation / skip, but L2 should preserve and explain it as `FLAT` context.

## Recommended Next Stage

`BOOK-L2-08 - FLAT Context Handling Proposal`

Purpose:

Prepare a safe proposal for L2 to preserve high-confidence FLAT as observe-only context without creating action signals.

## Not Approved In This Stage

- L1 logic changes
- L2 rule changes
- Bucket behavior changes
- Trading signals
- Edge validation
- Runtime execution
- 1h/4h expansion

## Safety

- read_only: `true`
- market_logic_changed: `false`
- l2_rules_changed: `false`
- trading_signal: `NOT_EVALUATED`
- safe_for_runtime_trading: `false`
- live_trading_connected: `false`

## Conclusion

The next work should propose how L2 handles high-confidence `FLAT`.

Do not move to BOOK-L3, edge validation, runtime execution, or interval expansion yet.
