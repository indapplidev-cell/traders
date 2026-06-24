# ML38.10.18 — exit mitigation path audit and recovery-risk filter

## Status
Implemented / research-only.

## Goal
ML38.10.17.1 confirmed that `lv25` exit mitigation runs without DB label-version failures, but runtime showed that simple early mitigation reduces full SL count while worsening PF and Total R. ML38.10.18 separates useful early exits from premature recovery cuts.

## Safety
- live trading: disabled
- orders: disabled
- traders-core integration: disabled
- model auto-activation: disabled
- research-only configs: yes
- future-path guard: research-only / not live-ready

## Main changes
- Added path audit for `EXIT_MITIGATED` outcomes.
- Added path classes:
  - `SAVED_FULL_SL`
  - `PREMATURE_CUT_TP_RECOVERY`
  - `PREMATURE_CUT_BREAKEVEN_RECOVERY`
  - `UNRESOLVED_AFTER_MITIGATION`
- Added `stop_loss_mitigation_recovery_guard_v1` research-only profile.
- Added `lv26_*` recovery-guard configs.
- Added `lv26` candidates to fast-debug and quick-quality runtime profiles.

## Runtime expectations
- `--fast-debug`: 2 symbols * 6 configs = 12 candidates.
- `--quick-quality --quick-quality-symbol SOLUSDT`: 1 symbol * 11 configs = 11 candidates.

## Acceptance rule
Do not accept a candidate only because it reduces `EXIT_MITIGATED` or `SL`. Candidate can be considered only if PF, total R, walk-forward PF, walk-forward total R, SL-rate, saved-full-SL rate, premature-recovery-cut rate, MFE/MAE diagnostics, and signal count improve together against lv25/lv24/lv23 comparators.
