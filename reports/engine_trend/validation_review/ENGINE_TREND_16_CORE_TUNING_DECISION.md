# ENGINE-TREND-16 — Core Tuning Decision

## Decision context
All 60 historical windows returned UNKNOWN. This stage reviews saved traces without changing behavior.

## Evidence reviewed
Validation matrices and their 60 referenced result JSON artifacts; reason codes, matrix summaries, candidate scores, confidence decomposition, warnings, errors, and safety metadata.

## Options
- Option A — Tune composer thresholds immediately.
- Option B — Add trace/debug instrumentation first.
- Option C — Compare 96 vs 192/384 context windows before tuning.
- Option D — Tune lower-level evidence extraction first.
- Option E — Stop core changes and keep the conservative baseline.

## Selected decision
**Option A — Tune composer thresholds in a separate stage.** No tuning is implemented in ENGINE-TREND-16.

## Rationale
Trace sufficiency is True; composer fallback appears in 60/60 windows and small candidate gaps in 60/60. Evidence extraction is not empty in 60/60 windows. Context length remains a secondary uncertainty rather than the best-supported universal cause.

## What is explicitly not allowed yet
No core, threshold, evidence matrix, adapter, CLI, schema, or runtime behavior change is authorized by this decision record.

## Next stage
**ENGINE-TREND-17 — Conservative Composer Threshold Review**

## Exit criteria for next stage
Predeclare candidate-separation and regime-selection diagnostics; compare against the frozen 60-window baseline; preserve OHLC integrity and safety; report all behavior changes; make no runtime or trading-readiness claims.
