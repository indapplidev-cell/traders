# ENGINE-TREND-17B вЂ” Per-Window Market Evidence Trace Expansion

## Stage goal
Make existing market evidence readable for every validation window without decision changes.
## Baseline
ENGINE-TREND-17 confirmed 60/60 UNKNOWN at confidence 0.3.
## Files created/changed
One reporting runner, offline contract tests, 120 per-window artifacts, indexes, coverage, missing-field, lock, manifest and this report. No engine core file changed.
## Input windows
15 ENGINE-TREND-15 plus 45 ENGINE-TREND-15B rows; none silently deduplicated.
## Behavior lock
60/60 replayed; UNKNOWN 0.3: 60; safety violations: 0; behavior changed: False.
## Trace expansion approach
Read existing facade composer/matrix output; do not recompute decisions or pre-clamp scores.
## Per-window report generation
Each row has JSON and readable Markdown covering all required layers.
## Trace coverage summary
Nison, Altunina, Schwager, matrix and clamped composer scores are visible on all ready rows.
## Missing trace fields
Pre-clamp composer scores/ranking/gap and confidence adjustments remain unexposed.
## Safety contract verification
All results remain NOT_EVALUATED, runtime false, live false.
## Tests executed
Recorded in the delivery summary after execution.
## Scans executed
Protected diff, legacy, write-SQL, trading term and secret scans recorded after execution.
## Known limitations
Reference labels are descriptive; 96-candle sufficiency, tuning safety, predictive value and runtime readiness are not established.
## What this stage proves
Existing evidence paths can be inspected per validation row and remaining opacity can be enumerated.
## What this stage does not prove
No edge, profitability, runtime readiness, live execution readiness, or safe composer tuning is proven.
## Next recommended stage
ENGINE-TREND-17C trace-only raw composer/event exposure; do not tune behavior yet.
