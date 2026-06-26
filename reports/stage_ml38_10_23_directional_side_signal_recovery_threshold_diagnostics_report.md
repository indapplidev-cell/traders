# ML38.10.23 - side-aware walk-forward signal recovery and threshold diagnostics

## Status
Implemented / research-only diagnostics.

## Goal
ML38.10.22 showed that LONG_ONLY / SUPPRESS_SHORT can be profitable on the final test window, but walk-forward evidence remains weak because side-aware candidates can produce zero/low-signal folds. ML38.10.23 explains where signals disappear: before side-filter, after side-filter, or after selected gate/threshold.

## Runtime range update
Fast-debug start date was expanded from `2026-05-01` to `2026-04-01`. End date remains `2026-06-15`. This increases the quick smoke training/evaluation range without changing candidate count.

## Safety
- live trading: disabled
- orders: disabled
- model auto-activation: disabled
- research-only diagnostics: yes
- no new lv configs: yes

## Main changes
- Added `DirectionalSideSignalRecoveryDiagnostics`.
- Added fold-level signal-loss reasons.
- Added side-filter removed-all and threshold-too-strict counters.
- Added recovery diagnostics into `walk_forward_profit_diagnostics`.
- Enriched directional side walk-forward stability board.
- Enriched multi-symbol and feature-regime reports.
- Updated fast-debug date range to `2026-04-01 -> 2026-06-15`.

## Runtime expectations
- `--fast-debug`: 2 symbols * 8 configs = 16 candidates.
- `--quick-quality --quick-quality-symbol SOLUSDT`: 1 symbol * 16 configs = 16 candidates.

## Acceptance rule
This stage must not accept any model. It only explains why side-aware research candidates have weak walk-forward evidence. Do not promote LONG_ONLY or SUPPRESS_SHORT unless later stages show stable fold-level signal counts and profitable walk-forward.
