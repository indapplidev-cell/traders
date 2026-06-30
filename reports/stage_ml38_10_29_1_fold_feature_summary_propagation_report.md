# ML38.10.29.1 Fold Feature Summary Propagation

## Root cause

The evaluator and training pipeline report contained the fold feature/regime filter summary, but `WalkForwardProfitDiagnostics._gate_snapshot()` and downstream quality/candidate payload propagation dropped it.

## What changed

- `walk_forward_profit_diagnostics`: preserves repair summaries and metadata in the best-gate snapshot and top-level diagnostics.
- `training_pipeline_runner`: selects the matching gate summary and attaches it to every required quality payload location.
- `label_grid_experiment_runner`: reads summaries through the top-level diagnostics, nested summary, and best-gate fallback chain.
- `feature_regime_experiment_runner`: verified existing post-processing preserves non-empty nested summaries.
- `feature_regime_experiment_reporter`: propagates compact summaries from top-level diagnostics and best-gate fallbacks.
- `multi_symbol_feature_regime_analyzer`: merges full candidate diagnostics and sends full candidate payloads to the repair probe.
- `fold_feature_regime_repair_probe`: reads nested best-gate summaries and aggregates actual removal counts.
- `multi_symbol_feature_regime_reporter`: reports readiness, candidate counts, aggregate counts, and the best probe removal count.
- Tests cover gate snapshot preservation, training payload attachment, nested candidate fallbacks, and probe readiness.

## Candidate counts

No new configs were added, so candidate counts remain unchanged.

## Tests

Required py_compile, targeted pytest, and full pytest are executed before cleanup.

## Runtime expectations

- fast-debug: 32 candidates.
- quick-quality SOLUSDT: 34 candidates.
