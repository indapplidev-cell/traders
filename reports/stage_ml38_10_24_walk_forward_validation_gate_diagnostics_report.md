# ML38.10.24 — walk-forward validation gate diagnostics and side-aware threshold relaxation

## Status
Implemented / research-only.

## Goal
ML38.10.23 showed that LONG_ONLY / SUPPRESS_SHORT can be profitable on the final test-window, but walk-forward produced zero-signal folds because no validation gate was selected. ML38.10.24 adds validation gate failure diagnostics and research-only side-aware validation relaxation.

## Safety
- live trading: disabled
- orders: disabled
- traders-core integration: disabled
- model auto-activation: disabled
- side-aware validation relaxation: research-only

## Main changes
- Added validation gate selection diagnostics to `GateSelector`.
- Added fold-level validation gate failure reason counts.
- Added side-aware single-direction validation support for research-only profiles.
- Added `lv29_*` research configs.
- Added validation gate failure summaries to side signal recovery and walk-forward diagnostics.

## Runtime expectations
- `--fast-debug`: 2 symbols * 9 configs = 18 candidates.
- `--quick-quality --quick-quality-symbol SOLUSDT`: 1 symbol * 19 configs = 19 candidates.

## Acceptance rule
Do not accept a candidate just because relaxed walk-forward gates produce more signals. Candidate can only be considered if PF, Total R, walk-forward PF, walk-forward Total R, fold signal counts, profitable fold ratio, and side-filter diagnostics improve together without hiding instability.
