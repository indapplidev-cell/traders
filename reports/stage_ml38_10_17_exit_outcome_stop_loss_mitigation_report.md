# ML38.10.17 — exit outcome / stop-loss mitigation tuning

## Status
Implemented / research-only.

## Goal
ML38.10.16.1 confirmed that MAE threshold propagation works, but runtime quality is still dominated by `stop_loss_hit`. ML38.10.17 adds research-only exit outcome simulation and stop-loss mitigation configs.

## Safety
- live trading: disabled
- orders: disabled
- traders-core integration: disabled
- model auto-activation: disabled
- research-only configs: yes

## Main changes
- Added `exit_policy_profile` to label grid configs.
- Added `stop_loss_mitigation_v1` research-only exit policy.
- Added `EXIT_MITIGATED` and `TIMEOUT_NEUTRAL` outcome reporting.
- Added exit mitigation counts/rates to profit-aware summary and root-cause audit.
- Added `lv25_*` stop-loss mitigation configs.
- Added `lv25` candidates to fast-debug and quick-quality runtime profiles.

## Runtime expectations
- `--fast-debug`: 2 symbols * 5 configs = 10 candidates.
- `--quick-quality --symbol SOLUSDT`: 1 symbol * 9 configs = 9 candidates.

## Acceptance rule
Do not accept a candidate only because `exit_mitigated_count` is high. Candidate can be considered only if PF, total R, walk-forward PF, walk-forward total R, SL-rate, MFE/MAE diagnostics, and signal count improve together against lv24/lv23 comparators.
