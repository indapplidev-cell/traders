# ENGINE-TREND-15 — Historical Market Reading Validation Plan

## Purpose

Evaluate how the unchanged engine reads selected historical market contexts. This stage creates evidence for a later decision; it does not tune the core or test trading performance.

## Validation principle

Freeze windows and manual reference labels before reviewing engine results. Treat labels as review references, not ground truth or trade signals. Preserve raw output, reasons, ambiguity, and reviewer notes.

## Symbols

- BTCUSDT
- ETHUSDT
- SOLUSDT

## Interval

Use `15m`, the currently confirmed interval.

## Window types

- visually clear UP
- visually clear DOWN
- visually clear FLAT/range
- choppy/unclear
- possible breakout/fakeout
- recent latest-window baseline

## Window count

Use at least 3 windows per symbol, with a target of 5 per symbol. The minimum total is 9 and the target total is 15. Across the pack, include all window types where the available history supports a defensible selection; document any unavailable type.

## Window length

Use 96 candles as the baseline. A 192-candle view may be captured as a secondary comparison, but is not required for the first pack and must not replace the baseline.

## Manual labeling rules

Allowed reference labels are:

- `EXPECTED_UP`
- `EXPECTED_DOWN`
- `EXPECTED_FLAT`
- `EXPECTED_UNKNOWN_OR_MIXED`

Labels are not trade signals. Record selection rationale and visible structural evidence without future-candle leakage beyond the frozen window. Prefer clear price structure over expected subsequent movement. Ambiguous, transitional, conflicting, breakout/fakeout, and choppy windows should use `EXPECTED_UNKNOWN_OR_MIXED` when a directional label cannot be defended. Record reviewer and label timestamp; disagreements become `NEEDS_REVIEW` rather than forced consensus.

## Engine output to collect

For every frozen window capture symbol, interval, exact inclusive bounds, loaded candle count, boundary status, market regime, confidence, top reason codes, warnings, errors, decision trace, integrity status, and safety fields. Store outputs as evidence only, never as candle input.

## Comparison matrix

Each row must contain:

| Field | Meaning |
| --- | --- |
| `symbol` | BTCUSDT, ETHUSDT, or SOLUSDT |
| `interval` | `15m` |
| `period_start` / `period_end` | frozen window bounds |
| `manual_label` | allowed reference label |
| `engine_market_regime` | unchanged engine output |
| `confidence` | unchanged engine output |
| `top_reason_codes` | reviewable decision reasons |
| `warnings_count` / `errors_count` | pipeline diagnostics |
| `match_status` | comparison assessment |
| `notes` | rationale, ambiguity, and review findings |

Allowed match statuses are `MATCH`, `ACCEPTABLE_UNKNOWN`, `QUESTIONABLE_UNKNOWN`, `MISMATCH`, and `NEEDS_REVIEW`. `ACCEPTABLE_UNKNOWN` applies when ambiguity supports UNKNOWN; `QUESTIONABLE_UNKNOWN` marks UNKNOWN on a clearly labeled window for later review, not automatic proof of a defect.

## Success criteria

- The pipeline runs on all selected historical windows, or each failure is explicitly recorded.
- Outputs are captured consistently and reason codes are reviewable.
- At least 9 windows meet the scope and labeling contract.
- UNKNOWN cases are separated into acceptable and questionable categories.
- The comparison matrix and source-window selection are reproducible.
- No core tuning is performed during the validation pack.

## Failure criteria

The pack is incomplete if fewer than nine valid windows are available, required symbols or `15m` coverage is missing, labels or bounds are absent, outputs are inconsistent/unreviewable, future data contaminates labels, or core behavior is changed during collection. Such failure triggers a new decision, not tuning.

## Non-goals

- no profitability or edge testing
- no directional trading actions or signals
- no runtime trading or live execution
- no model training
- no threshold, composer, evidence-matrix, schema, adapter, or CLI tuning in this stage
- no expansion to additional symbols/intervals as a prerequisite

## Expected artifacts

- historical window-selection manifest with immutable bounds and labels
- reviewer labeling guide and review notes
- per-window engine JSON outputs
- comparison matrix in machine-readable form
- summary of MATCH, acceptable/questionable UNKNOWN, MISMATCH, and NEEDS_REVIEW counts
- integrity, safety, and secret scans
- ENGINE-TREND-15 stage report and offline artifact tests
