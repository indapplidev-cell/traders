# ENGINE-TREND-17C — Trace Readiness Decision

## What was exposed
Raw and clamped scores, both observational rankings, top-two gaps, fallback reason, confidence path, and selection before/after fallback are exposed per window.

## What remains hidden
{'raw_scores': 60, 'ranking_before_clamp': 60, 'score_gap_before_clamp': 60, 'confidence_path': 60}

## Can we safely tune composer now?
No; required score fields remain hidden.

## Why aggregate-only reports are insufficient
Clamp collisions, evidence conflicts, and fallback paths differ by window despite identical final results.

## Per-window review readiness
60 sections are available in the primary all-windows artifact.

## Required next stage
ENGINE-TREND-17D — Composer Internal Score Instrumentation
