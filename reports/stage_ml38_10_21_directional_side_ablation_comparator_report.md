# ML38.10.21 — directional side ablation comparator board and research-only acceptance hardening

## Status
Implemented / research-only reporting hardening.

## Goal
ML38.10.20 added directional side ablation and short-side suppression research configs. ML38.10.21 adds a comparator board so runtime results can be interpreted safely before any acceptance discussion.

## Main changes
- Added `DirectionalSideAblationComparator`.
- Added side-profile classification:
  - BOTH_DIRECTIONS
  - LONG_ONLY
  - SHORT_ONLY
  - SUPPRESS_SHORT
- Added best-by-side-profile board.
- Added deltas vs both-direction comparator.
- Added research-only warnings for side suppression.
- Added report fields for side ablation analysis.

## Safety
- live trading: disabled
- orders: disabled
- traders-core integration: disabled
- model auto-activation: disabled
- side suppression: research-only
- no runtime executed in this stage

## Why this matters
If LONG-only improves PF/Total R, that is useful research but not automatically a trading solution. It can overfit a symbol/window or hide a broken SHORT side. Comparator output must be used to decide whether future work should repair SHORT features, suppress SHORT temporarily in research, or split models by direction.

## Runtime expectation after this stage
The next manual runtime remains:
- `--fast-debug`: 16 candidates
- `--quick-quality --quick-quality-symbol SOLUSDT`: 16 candidates
