# ENGINE-TREND-16 — Historical Validation Review and Core Tuning Decision

## Stage goal
Diagnose the 60-window UNKNOWN pattern and record the next diagnostic/tuning decision without behavior changes.

## Baseline
ENGINE-TREND-15 `1fb4e5f`; ENGINE-TREND-15B `2b98eea`; engine core, adapter, and DB CLI unchanged.

## Files created/changed
One offline runner, one offline test, two review matrices, five diagnostic/decision artifacts, this report, and an artifact manifest.

## Input artifacts reviewed
Two validation matrices and 60 referenced result JSON artifacts. Candle data was not sourced from report JSON for execution; saved results were read only as review evidence.

## Validation evidence summary
Windows: 60; UNKNOWN: 60; QUESTIONABLE_UNKNOWN: 39; MISMATCH: 0; warning/error count: 0.

## Trace field availability
Trace sufficient: True. Intermediate confidence-after-conflict and confidence-after-coverage fields are absent and represented as null.

## Reason code summary
Evidence codes are present in 60/60 windows. Full frequencies are in `ENGINE_TREND_16_REASON_CODE_SUMMARY.json`.

## Confidence diagnostics
Confidence 0.3: 60/60; decomposition present: 60/60; possible fallback floor/clamp: True.

## UNKNOWN cause diagnosis
Primary: B — conservative evidence/composer decision path. Secondary: D — 96-candle context may be too short and has not been tested here.

## Decision options
Options A–E were evaluated using the documented decision rules.

## Selected decision
Option A — Tune composer thresholds in a separate stage.

## Next recommended stage
ENGINE-TREND-17 — Conservative Composer Threshold Review

## Tests executed
`py_compile` passed; the ENGINE-TREND-16 offline tests passed (2); the 15/15B tests passed (8); the 13/14 tests passed (10); adapter/DB CLI tests passed (17); and the relevant ENGINE-TREND suite passed (230). Full pytest was intentionally not used as a mandatory gate because of the known unrelated diagnostics failure.

## Scans executed
Protected-core diff, write-SQL, legacy-import, runtime-term, secret, and generated-artifact scans were executed before commit; any matching safety terms were descriptive only.

## Known limitations
Only three symbols, one interval, and 96-candle contexts are represented. Intermediate confidence transitions are not saved. The unrelated diagnostics test issue is outside scope.

## What this stage proves
Saved traces show evidence reaching covered matrices while the conservative decision path returns UNKNOWN across the reviewed sample.

## What this stage does not prove
It does not prove a safe tuning value, longer-context behavior, profitability, predictive power, or runtime readiness.
