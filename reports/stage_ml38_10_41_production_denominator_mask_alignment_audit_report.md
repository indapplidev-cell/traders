# ML38.10.41 — Production Denominator and Mask Alignment Audit

## Why this stage follows ML38.10.40

ML38.10.40 established that production-label parity was not proven. Production quick-quality reported about 7.61% directional labels (74 rows), while the ML38.10.39 read-only recompute reported roughly 90.68–99.37% directional labels. The ML38.10.39 sensitivity board is therefore not actionable: its denominator, mask cascade, threshold units, and timeout semantics are not aligned with production.

ML38.10.41 does not recompute or change production labels. It adds a diagnostic-only contract for identifying the row population and evidence required before a production-like parity recompute can be considered valid.

## Denominator and mask gaps

- Candles to features: 7282 to 6481, leaving 801 rows to explain by a read-only timestamp join and feature-builder eligibility evidence.
- Feature rows to dataset splits: 4536 training + 972 validation + 973 test = 6481, so the supplied counts establish `SPLIT_PARITY_OK`.
- Production label count: `label_row_count` is absent, so the production denominator remains unresolved.
- Production directional count versus recompute: 74 versus approximately 6900+ rows is not comparable until identical row identities and masks are used.
- Per-row mask evidence is incomplete for `sqmask060`, effective `epq070/071`, and `sp045`.
- Regime-specific context, recovery guard inputs, and timeout-to-FLAT behavior remain prerequisites.
- `long_bad_dates_exit45_probe` is research-only and must be excluded from tradable parity.

## Diagnostic blocks added

- `production_denominator_mask_alignment_audit`
- `mask_cascade_board`
- `denominator_gap_board`
- `production_like_recompute_prerequisite_checklist`
- `ml38_10_41_alignment_decision`

The builders accept counts, config mapping, production/recompute evidence, and per-row mask evidence. Unknown counts remain explicit rather than being inferred. Decisions are derived from missing denominator evidence, per-row availability, mapping completeness, timeout semantics, and supplied sensitivity-board actionability.

## Files changed

- `app/diagnostics/label_grid_sensitivity_recompute.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/compact_archive_pruner.py`

No production label-builder, evaluator gate, or model-logic file was changed.

## Tests added

- `tests/test_ml38_10_41_production_denominator_mask_alignment_audit.py`
- `tests/test_stage_ml38_10_41_report.py`

## Verification

The allowed checks for this stage are:

- `python -m py_compile app/diagnostics/label_grid_sensitivity_recompute.py app/experiments/multi_symbol_feature_regime_analyzer.py app/experiments/multi_symbol_feature_regime_reporter.py app/experiments/feature_regime_experiment_reporter.py app/experiments/compact_archive_pruner.py run_fv3_cached_tuning.py`
- `python -m pytest tests/test_ml38_10_41_production_denominator_mask_alignment_audit.py`
- `python -m pytest tests/test_stage_ml38_10_41_report.py`

Results:

- `py_compile`: passed (6 files).
- alignment audit targeted pytest: 7 passed.
- stage report targeted pytest: 1 passed.

Full pytest was not run and requires explicit user approval after targeted tests.

## Scope and prohibition confirmation

- runtime training was not run.
- clean/fast/quick/sequence/full were not run.
- database writes were not performed.
- ml_labels were not written.
- labels, label builders, gates, and model logic were not changed.
- live trading and auto-activation were not changed.
- No runtime JSON, ZIP, or log artifact was created or added.
- Only this stage report was added under `reports/` as source material.
