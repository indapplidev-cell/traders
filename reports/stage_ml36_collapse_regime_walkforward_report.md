# Stage ML36

## Why ML36 Was Needed After ML35

ML35 confirmed that `fv2` and gap-training-safe logic were working across `BTCUSDT`, `ETHUSDT`, and `SOLUSDT`, but accepted candidates still stayed at zero.

The top failed gate after ML35 was `collapse_gate`, while `walk-forward` also failed across BTCUSDT / ETHUSDT / SOLUSDT. ML35 also showed that ETHUSDT and SOLUSDT were missing real diagnostics and regime features in the final summaries.

## What ML36 Added

- Added `collapse_diagnostics_v2` with dominant-class, FLAT underprediction, confidence, and margin diagnostics.
- Added a real `regime label builder` integration path for training and runtime diagnostics.
- Added walk-forward/profit diagnostics with fold-level best/worst fold detection.
- Added runtime fallback rows so real diagnostics can use runtime context instead of stopping at `dataset_rows_unavailable`.

## Regime Label Builder

ML36 wires the regime label builder into the real training pipeline and reports whether the builder is actually used in training.

If regime features are present and runtime label rows are built, the regime label builder can report `regime_label_builder_used_in_training: true`. If requirements are missing, the reason stays explicit in JSON summaries and reports.

## Real Diagnostics

ML35 left ETHUSDT and SOLUSDT with missing real diagnostics. ML36 adds runtime-context fallback so non-BTC symbols can still produce real diagnostics when rows exist in runtime flow.

This report explicitly tracks:

- BTCUSDT real diagnostics
- ETHUSDT real diagnostics
- SOLUSDT real diagnostics
- whether regime features were attached

## Walk-Forward And Profit-Aware Stability

ML36 adds compact diagnostics for:

- walk-forward profit factor
- walk-forward total R
- profitable vs unprofitable folds
- worst fold and best fold
- profit-aware threshold selection

That gives a direct explanation for continued `walk-forward` or profit-aware failures after positive baseline edge.

## Safety

- no traders-core
- no live
- no orders
- no auto activation

The project remains a standalone ML analytics service only. No traders-core integration, no live trading, no order placement, and no automatic model activation were added.

## Next Stage

ML37 - run real BTC/ETH/SOL grid after collapse/regime/walk-forward fixes.
