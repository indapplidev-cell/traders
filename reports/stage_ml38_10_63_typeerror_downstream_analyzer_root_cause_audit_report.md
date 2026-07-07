# ML38.10.63 — TypeError root cause diagnostic / downstream analyzer fail-closed audit

## Why this stage follows ML38.10.62

ML38.10.62 produced 45 valid SOLUSDT sidecar sets and a valid archive, but the wrapper and child returned `1 / 1`. The stage therefore closed as `WRAPPER_EXECUTION_FAILED` on `TypeError: unhashable type: 'dict'`. ML38.10.63 diagnoses that failure without another run or artifact mutation.

## Scope and evidence

This was a read-only/no-run source and evidence audit. Evidence sources were the external log and completion marker for `solusdt_quick_quality_20260707_065819`, the ML38.10.62 stage report and planning snapshot, the generated compact experiment summary, and the implicated source files. No wrapper, quick-quality, training, runtime, cascade, outcome, or DB-mutating command was run.

## Traceback evidence

The full traceback was found in the external log. Short sanitized excerpt:

```text
app/cli/commands.py:4879 in multi_symbol_feature_regime_analyze_command
app/cli/commands.py:3556 in analyze_multi_symbol_feature_regime
app/experiments/multi_symbol_feature_regime_analyzer.py:536 in analyze
app/diagnostics/directional_side_walk_forward_stability.py:16 in analyze
app/diagnostics/directional_side_walk_forward_stability.py:299 in _candidate_row
TypeError: unhashable type: 'dict'
```

First project frame: `app/cli/commands.py`, `multi_symbol_feature_regime_analyze_command`, line 4879. Failing frame: `app/diagnostics/directional_side_walk_forward_stability.py`, `DirectionalSideWalkForwardStabilityAnalyzer._candidate_row`, line 299 (region 298–303).

## Exact root cause

The failing operation is `list(dict.fromkeys(...))`, used to deduplicate the combined `walk_forward_stability_warnings` and derived verdict warnings. Compact archive pruning changed the warning list for SOLUSDT candidate `lv19_h12_tts_thr065_sqmask060` into this payload shape:

```json
{"_compact_pruned": true, "original_type": "list", "original_len": 6, "sample": ["walk_forward_has_zero_signal_folds", "walk_forward_has_low_signal_folds", "walk_forward_min_fold_signal_count_too_low"]}
```

The local `DirectionalSideWalkForwardStabilityAnalyzer._as_list` handles lists, tuples, and sets, but not the compact-pruned dict contract. It wraps the dict as `[dict]`. `dict.fromkeys` then hashes each member as a dict key, and the mutable dict is unhashable.

Root-cause classification: `ROOT_CAUSE_CONFIRMED_NESTED_WARNING_PAYLOAD_NOT_NORMALIZED`. Confidence: `HIGH`. The concrete lower-level mechanism is a dict used as a dict key during uniqueness processing.

## Failure phase and artifact status

Phase: `DURING_MULTI_SYMBOL_ANALYSIS_FOR_SINGLE_SOLUSDT`. The wrapper calls the named multi-symbol analyzer even for this SOLUSDT-only run.

Sidecar export and per-symbol artifact generation completed before the failure. The timeline is precise: analysis failed at 10:39:14; failure-path staging/pruning then ran; the ZIP was finalized and created at 10:40:12. Thus the failure was after sidecar generation but before ZIP creation, while the valid ZIP was safely produced after the error by failure handling. It blocked downstream analysis/report aggregation and wrapper success, not the already-written sidecar bytes.

Safely produced artifacts remain: 45 sidecar sets; latest sidecar `EXACT_BYTE_VALID` and `LF_ONLY_VALID`; schema `ml38.10.58` valid; summary contract, runtime truth, and completion evidence valid; archive valid with sidecars; no label substitution detected.

## Fail-closed decision

Valid artifacts do not override nonzero wrapper/child exits. Cascade/outcome remains blocked. Production-like recompute is not claimed and remains blocked. Tradable edge is not claimed. The TypeError was not fixed; wrapper/quick-quality was not rerun; artifacts were not mutated; no DB, `ml_labels`, or `ml_predictions` writes occurred; labels, builders, gates, and model logic were unchanged.

## Minimal fix plan (not applied)

In ML38.10.64, restrict changes to `app/diagnostics/directional_side_walk_forward_stability.py`: decode the existing compact-pruned list placeholder into its string `sample` before warning uniqueness processing, and add a synthetic compact-pruned dict warning regression test. No label, gate, builder, or model change is required. Any real rerun requires separate approval.

## Tests run

- Diagnostic module `py_compile`: passed.
- ML38.10.63 diagnostic tests: 4 passed.
- ML38.10.63 report tests: 2 passed.
- ML38.10.62 regression tests: 5 passed.
- ML38.10.61 regression tests: 6 passed.
- ML38.10.60 regression tests: 4 passed.
- `TrainingService` import: passed.
- `tests/test_class_weights.py --collect-only`: 1 test collected.
- `git diff --check`: passed.
- Full pytest: 1109 passed, 0 skipped, 1 warning.
- Full pytest exit code: 0.
- Pytest time: 82.05s.
- Full pytest wall time: 85.093s.
- Full pytest log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_63_20260707_113455.log`.

## Final decision

`TYPEERROR_ROOT_CAUSE_CONFIRMED_NO_FIX_NO_RERUN`

Confirmed root cause: `DirectionalSideWalkForwardStabilityAnalyzer._candidate_row`; `dict.fromkeys()`; compact-pruned dict from `walk_forward_stability_warnings`.

Classification: `ROOT_CAUSE_CONFIRMED_NESTED_WARNING_PAYLOAD_NOT_NORMALIZED`.

Phase: `DURING_MULTI_SYMBOL_ANALYSIS_FOR_SINGLE_SOLUSDT`.

Fix status: TypeError not fixed. Rerun status: wrapper/quick-quality not rerun. Cascade/outcome is blocked; production-like recompute is blocked; tradable edge claim is blocked.

Next recommended stage: ML38.10.64 — minimal no-run TypeError fix implementation with synthetic regression tests.
