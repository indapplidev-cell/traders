# ML38.10.16 — MAE-aware entry and exit/risk-reward tuning

## Status
Implemented / research-only.

## Goal
ML38.10.15 improved final stream filtering but the best quick-quality SOLUSDT candidate remained rejected with stop-loss dominant losses. ML38.10.16 adds MAE-aware ex-ante entry filtering and wider / asymmetric risk-reward label configs.

## Safety
- live trading: disabled
- orders: disabled
- traders-core integration: disabled
- model auto-activation: disabled
- research-only configs: yes

## Main changes
- Added `mae_aware_rr_v3` entry-path score profile.
- Added `mae_pressure_risk_score` and `rr_adjusted_entry_score` to entry-path diagnostics.
- Added `mae_pressure_max_risk_score` to label grid configs.
- Added final-stream audit counts for `high_mae_pressure` blocks.
- Added `lv24_*` MAE-aware entry/exit configs.
- Added `lv24` candidates to fast-debug and quick-quality runtime profiles.

## Runtime expectations
- `--fast-debug`: 2 symbols * 4 configs = 8 candidates.
- `--quick-quality --symbol SOLUSDT`: 1 symbol * 7 configs = 7 candidates.

## Acceptance rule
Do not accept any candidate unless profit-aware PF, total R, walk-forward PF, walk-forward total R, and stop-loss / MAE diagnostics improve together. Entry-path filter precision alone is not enough.
