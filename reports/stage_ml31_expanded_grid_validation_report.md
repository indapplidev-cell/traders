# Stage ML31 - Expanded Grid Validation

Stage ML31 completed.

ML30 improvements were validated through an expanded grid run with gap-aware tooling, anti-collapse controls, feature-quality diagnostics, and centralized candidate thresholds. The real validation run used:

- experiment_id: `real_grid_ml31_3_BTCUSDT_15m_20250101_20260612_130501`
- symbol: `BTCUSDT`
- interval: `15m`
- config_count: `3`
- configs:
  - `lv2_h08_thr04_tp10_sl10`
  - `lv2_h08_thr05_tp15_sl10`
  - `lv2_h12_thr05_tp15_sl10`

Expanded grid result:

- experiment_status: `COMPLETED_NO_ACCEPTED_CANDIDATE`
- accepted_candidate_count: `0`
- rejected_candidate_count: `3`
- best_candidate_config_id: `lv2_h12_thr05_tp15_sl10`
- best_candidate_score: `-6.372101`
- best_candidate_status: `CANDIDATE_REJECTED`

What improved:

- the best ML31 candidate did beat the baseline edge threshold with `accuracy_edge = 0.0170`
- the expanded grid successfully exercised the new ML30 gap-aware and anti-collapse research controls

What did not improve:

- no research candidate was accepted
- comparison against the previous best rejected baseline is degraded because the previous baseline summary is unavailable in the current repository state
- collapse_gate is still the top failed gate
- gap-aware validation still reports `gap_severity = HIGH`
- profit-aware behavior is still negative for the best candidate
- walk-forward remains unstable

Current failing gates across the best candidate:

- `collapse_gate`
- `gap_quality_gate`
- `profit_aware_gate`
- `walk_forward_gate`

How to run ML31 analysis:

```powershell
python -m app.cli.commands ml31-grid-improvement-analyze `
  --current-experiment-dir "reports\label_grid_experiments\real_grid_ml31_3_BTCUSDT_15m_20250101_20260612_130501"

python -m app.cli.commands ml31-grid-improvement-analyze --latest
```

Why traders-core is still not connected:

- there is no accepted candidate
- collapse and walk-forward issues remain
- gap-aware data quality is still not clean enough

Safety remains unchanged:

- no traders-core
- no live
- no orders
- no auto activation

Next stage:

- ML32 - feature engineering and regime-specific labels

