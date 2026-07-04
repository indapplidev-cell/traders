# ML38.10.36.2 — compact report aggregation consistency

## Problem

After ML38.10.36.1 archive pruning, the staged
`feature_regime_experiment_summary.json` retained candidate counts but dropped
compact-safe gap, diagnostics, feature-version, and regime integration fields.
The multi-symbol analyzer read only the former top-level verbose fields, treated
their absence as `UNKNOWN`/`False`, and consequently reported missing
diagnostics/regime features plus a synthetic `gap_quality_gate` failure.

## Root cause and fix

- `compact_archive_pruner.py` now writes a bounded canonical `compact_summary`
  containing only aggregation scalars and small diagnostic summaries. It does
  not restore raw rows, predictions, trades, or fold payloads.
- `multi_symbol_feature_regime_analyzer.py` now resolves each aggregation field
  in this order: explicit compact summary, nested summary, candidate-level
  summary, legacy field, and only then an unknown/missing value.
- Zero and `False` are treated as real values rather than absent data.
- Gap safety may be derived from `effective_gap_count_for_training == 0` plus
  severity `OK`/`MINOR`; this prevents a false `gap_quality_gate`.
- Compact-list samples remain readable for bounded candidate fallback.
- The aggregate output now contains `aggregate_report_source_consistency` with
  `compact_summary_source_used`, `missing_fields_after_fallback`,
  `source_priority_used`, and warnings only for fields absent from every source.
- `multi_symbol_feature_regime_reporter.py` includes the consistency audit in
  compact JSON and Markdown output.

## Changed files

- `app/experiments/compact_archive_pruner.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `tests/test_ml38_10_36_2_compact_report_aggregation_consistency.py`
- `tests/test_stage_ml38_10_36_2_report.py`
- `reports/stage_ml38_10_36_2_compact_report_aggregation_consistency_report.md`

`feature_regime_experiment_reporter.py` and `run_fv3_cached_tuning.py` were
inspected but did not require changes.

## Tests and commands

- `python -m py_compile app/experiments/multi_symbol_feature_regime_analyzer.py app/experiments/multi_symbol_feature_regime_reporter.py app/experiments/feature_regime_experiment_reporter.py app/experiments/compact_archive_pruner.py run_fv3_cached_tuning.py` — passed.
- `python -m pytest tests/test_ml38_10_36_2_compact_report_aggregation_consistency.py` — 6 passed.
- `python -m pytest tests/test_stage_ml38_10_36_2_report.py` — 1 passed.
- Related regression set covering ML38.10.36.1 pruning, the multi-symbol
  analyzer/reporter, gap-gate consistency, and top-level propagation — 11 passed.
- Read-only diagnostic against the latest quick-quality ZIP confirmed
  `fv4_book_setup_context`, gap `OK` with effective count `0`, diagnostics and
  regime flags present, no missing fields after fallback, and no synthetic
  `gap_quality_gate`.
- Full `python -m pytest` was not run pending explicit confirmation because the
  repository-wide suite is materially larger than the targeted/related sets.

## Safety confirmation

- runtime training was not run.
- clean/fast/quick/sequence/full were not run.
- model logic, gates, labels, live trading, and auto-activation were not changed.
- No runtime JSON/ZIP artifact was added or committed.
- Compact pruning remains enabled; archive payloads were not expanded back to
  verbose raw data.
