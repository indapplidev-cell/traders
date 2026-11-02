# Traders full-pipeline scalping calibration implementation

## Verdict

`IMPLEMENTED_CONTROL_PLANE; BASELINE_AND_TRAIN_BLOCKED_DATA`

The full-chain calibration control plane is implemented for the LONG pipeline:

`analysis -> setup -> strategy -> risk -> geometry -> target -> costs -> RR -> final risk -> portfolio -> approval -> PAPER plan -> fill -> position -> exit -> accounting`.

The implementation deliberately did not manufacture a candidate from incomplete
history.  The first immutable read-only freeze proved that the requested
walk-forward dataset is not present for all 20 symbols, so baseline, training and
PAPER canary remain fail-closed.

## Implemented interfaces

- `FullPipelineCalibrationRequestV1`;
- `StageParameterRegistryV1`;
- `PipelineDecisionTraceV1`;
- `EndToEndTradeEvaluationV1` with an accounting invariant;
- `FullPipelineCandidateV1` with deterministic economic gates;
- `PaperCanaryManifestV1` which cannot become ready without every gate passing;
- CLI actions `freeze`, `baseline`, `train`, `verify` and `paper-canary`.

The registry covers the native analysis modules, setup, seven entry components,
geometry, target, economics, RR, bounded risk and portfolio settings, approval,
fill lifecycle, position management and analytical exit.  Actual commission,
observed spread/slippage, closed-candle causality, idempotency, accounting and
LIVE prohibition are immutable safety inputs.

## Dataset result

Request: `config/research/full_pipeline_calibration_v1.json`.

Freeze artifact:
`artifacts/full_pipeline_calibration/freeze_20261102_v3`.

```text
STATUS = BLOCKED_DATA
DATASET_HASH = 85f4ab2d4f890d06871f517e5c6138fdb1ac22e292142afa015a0e686d2e6b1e
BLOCKER = INCOMPLETE_20_SYMBOL_WALK_FORWARD_CANDLE_COVERAGE
COVERAGE_FAILURES = 74
STRICT_COST_EVIDENCE_ROWS = 1803
STRICT_COST_EVIDENCE_PERIOD = 2026-09-02T21:50:00Z..2026-10-31T22:25:00Z
PRODUCTION_MUTATIONS = 0
```

Full 20-symbol history begins at different times:

| Timeframe | Earliest database row | First boundary with all 20 symbols represented |
|---|---:|---:|
| 1m | 2025-07-03 03:00 UTC | 2026-09-19 14:21 UTC |
| 5m | 2025-07-03 02:00 UTC | 2026-09-13 14:20 UTC |
| 15m | 2025-07-03 02:00 UTC | 2026-08-30 14:15 UTC |
| 1h | 2025-07-03 02:00 UTC | 2026-08-21 14:00 UTC |

The requested 2025/2026 walk-forward folds therefore cannot be replayed across
the same 20-symbol universe.  Candle coverage fails for all 20 symbols on 1m and
5m and for 17 symbols on each context timeframe.  Replacing the missing history
with current observations or silently shrinking the universe would violate the
approved calibration contract.

## Fail-closed behavior

- `baseline` writes `BLOCKED_DATA` and no metrics when the manifest is blocked;
- `train` writes `BLOCKED_DATA` and does not start a search;
- `verify` recomputes accounting, PF, expectancy, drawdown, concentration,
  walk-forward and stressed-cost gates from causal closed trades;
- `paper-canary` rejects every non-eligible candidate;
- no active parameter set, production database row, PAPER control state or LIVE
  setting is changed by research commands.

## Verification

- selected contract, causality, accounting, gate, canary, CLI and historical
  reconstruction suites: `62 passed`;
- Python compilation: `PASS`;
- immutable manifest freeze: deterministic read-only completion;
- baseline status: `BLOCKED_DATA`;
- training status: `BLOCKED_DATA`.

## Required next stage

Create a separate immutable research backfill for the missing 20-symbol candle
history and matching historical execution-cost evidence.  The backfill must not
write to the production database and must preserve source checksums and causal
timestamps.  If authoritative historical spread/commission evidence cannot be
obtained for a period, that period must remain excluded or be placed in a
separately labelled conservative scenario; it cannot be treated as verified
history.  After the freeze status becomes `FROZEN`, the existing production
component reconstructor can generate `DECISION_TRACES.jsonl`, allowing baseline
and training to proceed.
