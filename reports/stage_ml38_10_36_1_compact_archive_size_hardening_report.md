# ML38.10.36.1 — compact archive size hardening after threshold/flat-bias diagnostics

## Problem

quick-quality completed training but failed during compact archive staging:
COMPACT_PER_SYMBOL_STAGE_SIZE_CAP_EXCEEDED after_size_mb=375.52 cap_mb=350.00.

## Root cause

ML38.10.36 threshold/flat-bias diagnostics increased nested report sizes.
Large duplicated label_grid_runtime/**/training_pipeline_report.json files remained in compact archive.

## Fix

- Added compact_archive_pruner helper.
- Compact nested training_pipeline_report.json files.
- Preserve essential candidate/profit/walk-forward/flat-bias summaries.
- Prune heavy row/event/prediction lists into compact markers.
- Add compact_archive_pruning_summary.json.
- Keep acceptance gates unchanged.
- Keep candidate configs unchanged.

## Safety

- No model logic changes.
- No gates softened.
- No lv37 added.
- No live trading changes.
- No auto-activation changes.

## Validation

- py_compile: passed
- targeted pytest: 5 passed
- related pytest: 16 passed
- stage report pytest: 1 passed
- full pytest: 830 passed
