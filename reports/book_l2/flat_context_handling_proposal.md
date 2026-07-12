# BOOK-L2-08 - FLAT Context Handling Proposal

## Status

`PASS_WITH_PROPOSAL_WARNINGS`

## Purpose

This stage proposes how BOOK-L2 should handle high-confidence L1 `FLAT`.

It does not change L1 or L2 runtime logic.

## Request

| Field | Value |
|---|---|
| Symbols | BTCUSDT, ETHUSDT, SOLUSDT |
| Interval | 15m |
| High confidence threshold | 0.80 |

## Source Artifacts

| Artifact | Path |
|---|---|
| FLAT diagnostic JSON | reports/book_l1/flat_context_alignment_diagnostic.json |
| Alignment review JSON | reports/book_l1/l1_l2_regime_alignment_review.json |
| L1 timeline JSON | reports/book_l1/timeline_preview.json |
| L2 context JSON | reports/book_l2/timeline_context.json |

## Current Problem

High-confidence L1 FLAT is currently mapped by L2 to UNKNOWN/SKIP.

This conflates two different meanings:

- `FLAT` means the market was read as non-directional / range-like.
- `UNKNOWN` means the market was not read clearly.

## Proposed Interpretation

High-confidence L1 `FLAT` should be preserved by L2 as `FLAT_CONTEXT`.

Default proposal:

| Field | Proposed value |
|---|---|
| L2 bucket | FLAT_CONTEXT |
| Context label | HIGH_CONFIDENCE_FLAT |
| Observation candidate | false |
| Skip candidate | true |
| Trading signal | NOT_EVALUATED |
| Safe for runtime trading | false |

## Case Proposals

| Symbol | L1 Regime | Confidence | Current L2 Bucket | Current Skip | Proposed Bucket | Proposed Observation |
|---|---|---:|---|---|---|---|
| BTCUSDT | FLAT | 0.94 | UNKNOWN | true | FLAT_CONTEXT | false |
| ETHUSDT | FLAT | 0.87 | UNKNOWN | true | FLAT_CONTEXT | false |
| SOLUSDT | UNKNOWN | 0.00 | UNKNOWN | true | UNKNOWN | false |

## Semantic Options Considered

### Option A - Keep current behavior

Not recommended.

### Option B - FLAT as observation candidate

Not recommended now.

### Option C - FLAT context but not observation candidate

Recommended safe default.

### Option D - FLAT quality depends on reason codes

Recommended later after reason-code review.

## Recommended Option

`OPTION_C_FLAT_CONTEXT_NOT_OBSERVATION_CANDIDATE`

Meaning:

High-confidence `FLAT` should not become `UNKNOWN`.

It should be preserved as market context, but should not become an observation candidate by default.

## Implementation Not Approved Yet

This stage does not implement the rule.

Runtime implementation should be done in:

`BOOK-L2-09 — Implement FLAT Context Handling`

## Proposed BOOK-L2-09 Scope

- update L2 context mapping so high-confidence FLAT maps to FLAT_CONTEXT;
- keep observation_candidate false by default;
- keep skip_candidate true by default;
- keep safe_for_runtime_trading false;
- ensure UNKNOWN remains distinct from FLAT;
- update L2 JSON consumer/API readiness tests.

## Safety

- read_only: `true`
- proposal_only: `true`
- runtime_behavior_changed: `false`
- l1_logic_changed: `false`
- l2_rules_changed: `false`
- trading_signal: `NOT_EVALUATED`
- safe_for_runtime_trading: `false`
- live_trading_connected: `false`

## Conclusion

BOOK-L2 should preserve high-confidence L1 `FLAT` as `FLAT_CONTEXT`.

Do not move to edge validation, BOOK-L3, interval expansion, or runtime execution yet.
