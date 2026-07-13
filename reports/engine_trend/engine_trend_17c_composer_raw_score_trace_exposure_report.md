# ENGINE-TREND-17C — Composer Raw Score Trace Exposure

## Stage goal
Expose composer internals without changing decisions.

## Baseline
60/60 UNKNOWN at confidence 0.3.

## Files created/changed
Trace-only composer fields, runner, tests, per-window and aggregate artifacts.

## Input windows
15 ENGINE-TREND-15 and 45 ENGINE-TREND-15B windows. DB configuration was unavailable, so the committed blocked artifacts retain 17B replay metadata and do not claim a new replay.

## Behavior lock
{'stage': 'ENGINE-TREND-17C', 'window_count': 60, 'market_regime_counts': {'UNKNOWN': 60}, 'confidence_counts': {'0.3': 60}, 'unknown_0_3_count': 60, 'safety_violations': 0, 'behavior_changed': False, 'behavior_lock_ok': True}

## Composer trace exposure
The core now exposes raw/clamped scores, rankings, gaps, fallback and confidence path as observational fields. Existing clamped decision ranking is unchanged. Artifact raw values remain explicitly unavailable until the PostgreSQL runner succeeds.

## Unified all-windows report
Aggregate summary does not replace per-window review. The all-windows report is the primary artifact for human analysis.

## Raw score matrix
Contains 60 rows.

## Missing composer fields
{'raw_scores': 60, 'ranking_before_clamp': 60, 'score_gap_before_clamp': 60, 'confidence_path': 60}

## Safety verification
No runtime or live trading is connected; safety violations: 0.

## Tests executed
See delivery record.

## Scans executed
Protected-file, rejected-candidate, legacy import, write SQL, trading, and credential scans are required before commit.

## Known limitations
Reference labels are descriptive; 96 candles may be insufficient.

## What this stage proves
Composer score and fallback paths are reviewable per window.

## What this stage does not prove
No edge, profitability, tuning safety, runtime readiness, or live execution readiness is proven.

## Next recommended stage
ENGINE-TREND-17D — Composer Internal Score Instrumentation
