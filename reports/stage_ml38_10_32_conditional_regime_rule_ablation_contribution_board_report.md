# ML38.10.32 - Conditional regime rule ablation and per-regime contribution board

## Root cause

ML38.10.31 proved that conditional regime-risk filtering is better than hard regime blocking,
but the diagnostics did not explain rule-level contribution and per-regime R impact.

## Changes

- Added conditional rule eligible/pass/block counts.
- Added metric failure counts by rule.
- Added removed/passed outcome contribution estimates by rule.
- Added removed/passed outcome contribution estimates by primary regime and active regime flag.
- Added conditional_regime_ablation_board.
- Added per_regime_contribution_board.
- Propagated new diagnostics through reporter/analyzer/probe.
- Runtime configs unchanged.

## Safety

No model activation.
No live trading.
lv31/lv32/lv33/lv34 remain research-only.
No runtime commands executed in this stage.

## Tests

- py_compile
- targeted pytest
- full pytest

## Expected next runtime counts

fast-debug = 36
quick-quality SOLUSDT = 38
