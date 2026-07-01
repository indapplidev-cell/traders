# ML38.10.29.2 Configs Ranked and Aggregate Diagnostics Cleanup

## Root causes

1. `_compact_fold_feature_summary()` returned `_compact_preview_dict()`, losing detailed counts in `configs_ranked`.
2. The multi-symbol analyzer did not replace `{"_key_count": 0}` placeholders with real `candidate_results` summaries.
3. `FoldFeatureRegimeRepairProbe` counted compact service keys and did not fall back from summary maps to row-level maps.

## Changed files

- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/diagnostics/fold_feature_regime_repair_probe.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `tests/test_ml38_10_29_2_configs_ranked_aggregate_cleanup.py`

## Tests

The required py_compile, targeted pytest, and full pytest are executed before cleanup.

## Runtime expectations

- fast-debug: 32 candidates.
- quick-quality SOLUSDT: 34 candidates.

No new configs were added. lv31/lv32/lv33 remain research-only and are not acceptance eligible.
