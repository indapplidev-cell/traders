# ML38.10.64 — minimal no-run TypeError fix with synthetic regression tests

## Why this stage follows ML38.10.63

ML38.10.63 confirmed that a compact-pruned dict from `walk_forward_stability_warnings` reached `dict.fromkeys` in downstream report aggregation. It closed as `TYPEERROR_ROOT_CAUSE_CONFIRMED_NO_FIX_NO_RERUN`; ML38.10.64 applies only the minimal analyzer fix and synthetic regression coverage.

## Root cause and exact fix

Fixed file: `app/diagnostics/directional_side_walk_forward_stability.py`.

Fixed function: `DirectionalSideWalkForwardStabilityAnalyzer._candidate_row`.

Before: a compact-pruned dict from `walk_forward_stability_warnings` reached `dict.fromkeys` and raised `TypeError: unhashable type: 'dict'`.

After: `_normalize_walk_forward_warning_sample` normalizes every warning payload to a stable string before `dict.fromkeys`. Existing strings stay unchanged, priority string fields in dicts remain human-readable, and other dict/list/tuple/set payloads become compact stable strings.

- Order preserved: true.
- Deduplication preserved: true.
- Dict payload passed directly to hash-based uniqueness: false.

This changes only the downstream analyzer/report aggregation path. It does not alter the input/output schema beyond ensuring warning samples are strings.

## Synthetic regression tests

`tests/test_ml38_10_64_typeerror_downstream_analyzer_minimal_fix.py` covers the real `_candidate_row` failure path with a synthetic compact-pruned nested dict, equal dict deduplication with order preservation, unchanged string warning behavior, and mixed warning payloads. The tests do not read real artifacts and require no DB.

## No-run and artifact guardrails

There was no wrapper/quick-quality rerun. Clean, fast-debug, sequence, training, and runtime commands were not run. No DB writes and no `ml_labels` or `ml_predictions` writes occurred. There was no real artifact mutation, no new real sidecar, no new ZIP, no archive recovery, and no summary recreation.

There were no labels/gates/model changes and no label builder changes. Cascade/outcome remains blocked. Production-like recompute is blocked; this is not production-like recompute. Tradable edge claim is blocked, and tradable edge is not claimed.

## Tests run

- Targeted `py_compile`: passed.
- ML38.10.64 synthetic regression tests: 4 passed.
- ML38.10.64 report tests: 2 passed.
- ML38.10.63 targeted regression: 4 passed.
- ML38.10.62 targeted regression: 5 passed.
- ML38.10.61 targeted regression: 6 passed.
- `TrainingService` import: passed (`TrainingService`).
- `tests/test_class_weights.py --collect-only`: 1 test collected.
- `git diff --check`: passed.
- Full pytest: 1115 passed, 0 skipped, 1 warning.
- Full pytest exit code: 0.
- Pytest time: 88.62s.
- Full pytest wall time: 92.2188455s.
- Full pytest log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_64_20260707_174426.log`.

## Final decision

`TYPEERROR_MINIMAL_FIX_IMPLEMENTED_NO_RERUN_SYNTHETIC_TESTED`

Next recommended stage: ML38.10.65 — no-run post-fix validation audit / rerun readiness plan.
