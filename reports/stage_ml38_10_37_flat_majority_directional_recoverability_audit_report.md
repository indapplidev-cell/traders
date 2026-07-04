# ML38.10.37 — FLAT-majority label imbalance and directional recoverability audit

## Problem and scope

The latest SOLUSDT 15m quick-quality result has FLAT ≈ 92%, with only about 8% combined UP/DOWN labels. This stage is diagnostic-only: it explains label distribution, directional sample size, baseline pressure, recoverability evidence, and gate blockers. It does not accept, activate, or trade a candidate and does not prescribe a label change.

## Diagnostic blocks added

- `flat_majority_directional_recoverability_audit`
- `baseline_edge_gate_explanation`
- `top_candidate_gate_blocker_board`
- `directional_recoverability_decision`

The audit computes directional percentage and the FLAT-to-directional ratio, uses class-count and compact-report fallbacks, separates positive profit/walk-forward evidence from gate passage, and marks research-only candidates as non-tradable.

## Files changed

- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`

The existing label builders, feature pipeline, evaluator, fold repair probe, per-symbol reporter, and wrapper were inspected but not modified.

## Tests added

- `tests/test_ml38_10_37_flat_majority_directional_recoverability_audit.py`
- `tests/test_stage_ml38_10_37_report.py`

## Verification

- `python -m py_compile`: passed (6 requested Python files).
- `python -m pytest tests/test_ml38_10_37_flat_majority_directional_recoverability_audit.py`: passed, 5 tests.
- `python -m pytest tests/test_stage_ml38_10_37_report.py`: passed, 1 test.
- Full pytest: not run; user approval is required after targeted tests.

## Prohibition and safety confirmation

- runtime training was not run.
- clean/fast/quick/sequence/full were not run.
- `clean_traders_ml.py`, cleanup-commit-only, quick-quality, fast-debug, `run_clean_fast_quick_sequence.py`, and runtime/full training were not run.
- labels, label builder behavior, gates, and model logic were not changed.
- `baseline_edge_gate` was not softened.
- no lv37 runtime or training config was added.
- live trading and auto-activation were not changed.
- no runtime JSON, ZIP, or log artifact was created or staged.
