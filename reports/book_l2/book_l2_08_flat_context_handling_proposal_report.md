# BOOK-L2-08 - FLAT Context Handling Proposal

## Status

`PASS_WITH_PROPOSAL_WARNINGS`

## Purpose

This stage proposes safe handling for high-confidence L1 `FLAT` in BOOK-L2.

## Source context

- BOOK-DATA-03C stabilization: PASS
- BOOK-L1-26 quality review: PASS_WITH_QUALITY_WARNINGS
- BOOK-L1-27 regime alignment review: PASS_WITH_ALIGNMENT_WARNINGS
- BOOK-L1-28 FLAT context diagnostic: PASS_WITH_FLAT_ALIGNMENT_WARNINGS
- Active interval: `15m`

## Outputs

- `reports/book_l2/flat_context_handling_proposal.json`
- `reports/book_l2/flat_context_handling_proposal.md`

## Current problem

High-confidence L1 `FLAT` is received by L2, but currently mapped to `UNKNOWN/SKIP`.

## Proposal

High-confidence L1 `FLAT` should be preserved as L2 `FLAT_CONTEXT`.

Default behavior:

- observation_candidate: `false`
- skip_candidate: `true`
- trading_signal: `NOT_EVALUATED`
- safe_for_runtime_trading: `false`

## Recommended option

`OPTION_C_FLAT_CONTEXT_NOT_OBSERVATION_CANDIDATE`

## Recommended next stage

`BOOK-L2-09 — Implement FLAT Context Handling`

## Safety

No L1 logic was changed.
No L2 runtime rules were changed.
No trading signals were generated.
No live trading is connected.

## Checks

- py_compile: PASS
- targeted proposal tests: PASS
- L2 targeted pack: PASS
- relevant BOOK-L1/L2/DATA pack: PASS
- real FLAT diagnostic smoke: PASS_WITH_FLAT_ALIGNMENT_WARNINGS
- real proposal smoke: PASS_WITH_PROPOSAL_WARNINGS
- forbidden terms check: PASS
- git diff --cached --check: PASS

## Conclusion

The next work should implement the proposed L2 handling for high-confidence FLAT in a separate controlled stage.
