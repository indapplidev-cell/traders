# ENGINE-TREND-21 — Future Integration Plan

## Goal

Add a separate, side-effect-free setup layer after ENGINE-TREND without modifying the composer, hypothesis generation, `technical_indicator_context`, trading runtime, or baseline output schema.

## Proposed boundary

The existing engine remains the authoritative producer of market context and causal hypotheses. A future adapter copies its immutable result into a versioned `SetupEvaluationInput`; it does not call composer internals or feed setup results back into regime selection.

Proposed modules, only after separate implementation authorization:

- `setup_layer/input_adapter.py`: lossless mapping from public engine result plus causal evidence references.
- `setup_layer/contracts.py`: contract definitions and status transitions.
- `setup_layer/evaluator.py`: pure evaluation; no I/O, clock reads, database writes, or execution calls.
- `setup_layer/reward_risk.py`: decimal-safe directional RR calculation.
- `setup_layer/schemas.py`: versioned input/output types matching the JSON Schema.
- `setup_layer/reason_codes.py`: stable reason-code vocabulary.

## Integration sequence

1. Freeze golden ENGINE-TREND-19/20 outputs and assert byte/semantic equivalence before and after adding the optional consumer.
2. Define the adapter only against the existing public engine result. Missing setup evidence must cause `NO_TRADE`, not a composer change.
3. Implement `NO_TRADE_CONTRACT` and hard blockers first, especially `UNKNOWN_ALWAYS_NO_TRADE`.
4. Implement pure setup evaluators behind a disabled feature flag, with trend-only and range contracts independently gated.
5. Add causal fixture tests for status transitions, level provenance, no lookahead, expiry, and conflicts.
6. Validate proposed minimum RR, expiry, confirmation definitions, and stop buffers out of sample. Do not reuse current task defaults as production thresholds without approval.
7. Perform separate ENGINE-TREND-20B validation before enabling `SHORT_TREND_ONLY_CONTINUATION_CANDIDATE` under any circumstances.
8. Shadow-run setup outputs to reports only. Compare without orders, PnL, or trading side effects.
9. Create profitability labels later in a separate project phase using frozen setup outputs. ML meta-filter, risk gate, and execution remain downstream and out of scope.
10. Require a separate decision record and explicit authorization for any runtime wiring.

## Composer isolation

The composer remains unchanged and unaware of setup results. Integration is one-way:

`engine.evaluate(...) -> existing EngineResult`

`setup_input_adapter(existing EngineResult, evidence snapshot) -> SetupEvaluationInput`

`setup_evaluator.evaluate(input) -> SetupOutput`

No setup field is added to composer scores, no setup result changes regime confidence, and no missing setup input is repaired by changing engine thresholds. A caller may expose engine and setup outputs side-by-side in a new envelope while preserving the baseline payload exactly.

## State and expiration

Pure snapshot evaluation can produce `NO_TRADE`, `WAIT_CONFIRMATION`, or `TRADE_CANDIDATE`. To emit `INVALIDATED`, a future orchestration layer passes the previous setup output/state into the evaluator. State is keyed by `setup_id`, symbol, timeframe, and source evidence IDs. The evaluator never queries future candles. Expiry counts only closed candles in the same timeframe after the causal trigger/confirmation defined by the contract.

## Validation gates

- Schema validation and stable serialization.
- Golden regression: no baseline engine-output changes.
- Property tests: long/short RR symmetry, positive risk/reward, no candidate with null levels.
- Causality tests: appending future candles cannot alter a frozen historical output.
- Conflict tests: `UNKNOWN`, confirmed opposing reversal/range/trap, and bad data block.
- Lifecycle tests: pending -> candidate, pending/candidate -> invalidated, pending -> stale no-trade.
- Independent manual labels and OOS review for each contract family.
- ENGINE-TREND-20B gate for trend-only short.

## Explicit exclusions

No exchange connector, order model, position sizing, portfolio risk, leverage, fees/slippage implementation, PnL, backtest, ML model, or live trading wiring belongs in this phase.

