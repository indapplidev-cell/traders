# ML38.10.30-BIG — market_regime propagation / regime-aware repair filter

1. Root cause:
   prediction rows did not expose market_regime top-level,
   so SignalGateEvaluator could not pass it to signal_rows.

2. What was changed:
   - DiagnosticsService derives market_regime from features_json regime_* flags.
   - Prediction rows now include market_regime/regime_bucket/active_regime_flags.
   - ProfitAwareEvaluatorV2 blocks by active_regime_flags, not only primary regime.
   - fold_feature_regime_filter_summary now reports regime source/active flags.
   - reporter/analyzer/probe propagate new regime diagnostics.

3. No new configs added.

4. Runtime counts unchanged:
   fast-debug = 32
   quick-quality SOLUSDT = 34

5. Expected runtime proof:
   aggregate_removed_counts_by_regime no longer only {"missing": ...}
   aggregate_missing_feature_counts.market_regime should be 0 or near 0.
