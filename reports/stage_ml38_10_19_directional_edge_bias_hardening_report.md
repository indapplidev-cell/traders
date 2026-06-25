# ML38.10.19 — directional edge and bias hardening after recovery guard

## Status
Implemented / research-only.

## Goal
ML38.10.18 confirmed that recovery guard improves lv25 by reducing premature mitigation, but candidates still fail profit, bias, and baseline-edge gates. ML38.10.19 adds directional edge/bias diagnostics and new directional-bias hardened lv27 configs.

## Why this stage exists
After recovery guard, the remaining loss may come not only from exits but from directional imbalance:
- too many LONG or too many SHORT signals;
- one side dominates signal count;
- one side is consistently unprofitable;
- model confidence may be high on the wrong direction;
- baseline edge and bias gates reject the candidate even when walk-forward looks better.

## Main changes
- Added `directional_edge_bias_audit` to profit-aware gate summaries.
- Added long/short average R, total R, win/loss diagnostics.
- Added direction balance and profit skew metrics.
- Added `lv27_*` recovery-guard + directional hardening configs.
- Added `lv27` to fast-debug and quick-quality runtime shortlists.

## Runtime expectations
- `--fast-debug`: 2 symbols * 7 configs = 14 candidates.
- `--quick-quality --quick-quality-symbol SOLUSDT`: 1 symbol * 13 configs = 13 candidates.

## Safety
- live trading: disabled
- orders/trades: disabled
- traders-core integration: disabled
- model auto-activation: disabled
- research-only configs: yes

## Acceptance rule
Do not accept a candidate only because direction balance looks better. A candidate can be considered only if profit factor, total R, walk-forward PF, walk-forward total R, directional bias warning, baseline edge, signal count, and drawdown diagnostics improve together against lv26/lv25/lv24 comparators.
