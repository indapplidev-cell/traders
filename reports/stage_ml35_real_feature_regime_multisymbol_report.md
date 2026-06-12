# Stage ML35 - Real Feature/Regime Multi-Symbol Analysis

Stage ML35 completed.

ML35 was needed after ML34 because ML34 established `fv2`, training-safe gap handling, real feature diagnostics foundations, and regime feature attachment foundations, but it still lacked a code-level multi-symbol analyzer for comparing BTCUSDT, ETHUSDT, and SOLUSDT in one deterministic report.

The real batch archive reference for this stage is `ml35_fr_3_symbols_15m_20260612_224659.zip`.

## Symbols Checked

- BTCUSDT
- ETHUSDT
- SOLUSDT

All candidates rejected:

- accepted_candidate_count: `0`
- rejected_candidate_count: `3`

Best symbol: `BTCUSDT` by score.

- best score: `-2.003547`

## BTC/ETH/SOL Comparison

- BTCUSDT: `score -2.003547`, `edge +0.018072`, `profit_factor 1.009218`, `walk_forward_pf 0.972727`, `real feature diagnostics true`, `row_count 50453`, `regime features true`
- ETHUSDT: `score -2.965675`, `edge +0.032728`, `profit_factor 0.0`, `walk_forward_pf 0.972161`, `real feature diagnostics false`, `row_count 0`, `regime features false`
- SOLUSDT: `score -3.388438`, `edge -0.003011`, `profit_factor 1.071715`, `walk_forward_pf 0.982248`, `real feature diagnostics false`, `row_count 0`, `regime features false`

## Feature/Gap Findings

- `fv2` used on all symbols
- gap training safe on all symbols
- `gap_quality_gate` passed on all symbols
- `gap_severity_for_training` remained `OK` on all symbols
- `effective_gap_count_for_training` remained `0` on all symbols

This confirms the ML34 gap-quality separation is holding and trailing incomplete current-day gaps are no longer blocking candidate selection.

## Real Feature Diagnostics

- BTCUSDT used real feature diagnostics
- ETHUSDT missing real feature diagnostics
- SOLUSDT missing real feature diagnostics

The current multi-symbol result therefore still shows missing real feature diagnostics for ETH/SOL and missing regime features for ETH/SOL. That remains an open issue for ML36 if it cannot be solved by a small safe runner/reporting fix.

## Gate Outcomes

- collapse failed on all symbols
- walk-forward failed on all symbols
- profit-aware failed on BTC/ETH
- baseline edge passed on BTC/ETH but failed on SOL

## Safety

- no traders-core
- no live
- no orders
- no auto activation

`approved_for_live_trading: false`

`approved_for_auto_activation: false`

`orders_enabled: false`

`traders_core_connected: false`

## Next Stage

ML36 — Fix collapse, wire real regime-specific label builder, and improve walk-forward/profit-aware stability.
