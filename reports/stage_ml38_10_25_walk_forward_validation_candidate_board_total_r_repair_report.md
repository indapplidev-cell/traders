# ML38.10.25 — Walk-forward validation candidate board and total-R failure repair

## Goal

Add explicit walk-forward validation candidate-board diagnostics for no-gate folds, expose total-R failure repair evidence, and keep every total-R repair probe research-only.

## Implemented

- Extended `GateSelector` to report failed-gate deficits, `primary_blocker`, `repair_hint`, distance-to-pass ranking, and `validation_total_r_failure_board`.
- Added `walk_forward_validation_candidate_board` and propagated its summary through walk-forward diagnostics, directional-side diagnostics, multi-symbol analysis, and reporters.
- Added `lv30_*` total-R repair probe configs and the research-only acceptance block via `research_only_validation_total_r_repair_gate`.
- Expanded runtime shortlist metadata so fast-debug starts with `lv30_h08_*` and quick-quality starts with the two `lv30_h12_*` probes.

## Safety

- `lv30_*` configs are research-only and cannot become `ACCEPTED`.
- `research_only_validation_total_r_repair_gate` is appended to failed gates whenever total-R repair probe mode is enabled.
- The stage only exposes repair evidence; it does not promote relaxed total-R validation to live acceptance.

## Runtime counts expected

- `fast-debug`: `2` symbols x `10` configs = `20` candidates
- `quick-quality --quick-quality-symbol SOLUSDT`: `1` symbol x `21` configs = `21` candidates

## Validation

- `python -m py_compile` for gate selector, diagnostics, grid/runners/reporters, analyzer, matrix, and `run_fv3_cached_tuning.py`
- targeted `pytest` for ML38.10.25 candidate-board coverage plus ML38.10.24/23/22 regression checks
- full `python -m pytest -q`
