# ML38.10.22 - directional side walk-forward stability and report enrichment

## Status
Implemented / research-only reporting hardening.

## Goal
ML38.10.21.1 fixed the directional side comparator payload source-of-truth. Runtime showed that LONG_ONLY / SUPPRESS_SHORT can improve test-window PF and Total R, but walk-forward evidence is still weak or missing because of low-signal folds. ML38.10.22 adds walk-forward stability diagnostics for directional side ablation candidates.

## Safety
- live trading: disabled
- orders: disabled
- traders-core integration: disabled
- model auto-activation: disabled
- side suppression: research-only
- cleanup/runtime execution in this Codex pass: forbidden

## Main changes
- Enriched walk-forward profit diagnostics with fold snapshots and signal stability summary.
- Added directional side walk-forward stability analyzer.
- Added verdicts for side profiles:
  - REJECT_NO_WALK_FORWARD_EVIDENCE
  - REJECT_LOW_SIGNAL_WALK_FORWARD
  - REJECT_WALK_FORWARD_UNSTABLE
  - CANDIDATE_FOR_NEXT_GRID_RESEARCH_ONLY
- Added multi-symbol report payload and markdown sections for directional side walk-forward stability.
- Preserved runtime config counts: fast-debug 16 candidates, quick-quality 16 candidates.

## Impact
This stage does not change model training, labels, runtime shortlists, gates, live trading, or candidate acceptance thresholds. It improves diagnostics and prevents false confidence when a side-filter looks profitable on the test-window but lacks walk-forward signal stability.

## Runtime expectations after manual run
- `--fast-debug`: 16 candidates.
- `--quick-quality --quick-quality-symbol SOLUSDT`: 16 candidates.

## Acceptance note
A LONG_ONLY or SUPPRESS_SHORT profile must not be considered a trading candidate unless walk-forward fold signal counts, PF, Total R, profitable fold rate, and multi-symbol confirmation improve together. Until then, side suppression remains research-only.
