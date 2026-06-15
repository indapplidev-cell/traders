# Stage ML38.2.1 Report

## What Was Broken

- ML38.2 wrapper did not complete end-to-end.
- Archive was manually assembled after the wrapper stopped before final packaging.
- `gap_quality_gate` could appear in `failed_gates` even when `gap_severity_for_training=OK` and `gap_training_safe=true`.
- ML38.2 could not be considered technically closed while orchestration and gate reporting diverged.

## What Was Fixed

- Wrapper preflight now runs before any repo runtime artifact is created.
- Wrapper contract now targets end-to-end completion with manifest and archive flags.
- Gap gate normalization is applied consistently at candidate and multi-symbol levels.
- Critical or unsafe gaps now explicitly force `REJECTED`, while OK/safe gaps no longer fail the gate.

## Files Changed

- `app/evaluation/gap_quality_gate_normalizer.py`
- `app/evaluation/model_candidate_selector.py`
- `app/experiments/label_grid_experiment_runner.py`
- `app/experiments/feature_regime_experiment_runner.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/ml38_2_1_wrapper_manifest.py`
- `tests/test_ml38_2_1_gap_gate_reporting_consistency.py`
- `tests/test_ml38_2_1_fresh_grid_wrapper_manifest.py`
- `tests/test_ml38_2_1_multisymbol_gate_consistency.py`
- `tests/test_stage_ml38_2_1_report.py`
- external script updated outside repo: `D:\disk_E\game_projects\traders\run_ml38_2_fv3_tuning_btc_eth_sol.ps1`

## Checks

- `python -m pytest` -> pending final validation
- CLI checks -> pending final validation
- `py_compile` -> pending final validation
- fresh wrapper -> pending final run
- archive path -> pending final run

## Fresh Grid / Archive Result

- archive path: pending
- manifest path: pending
- wrapper_completed_end_to_end: pending
- manual_archive_assembly_used: pending
- manual archive assembly used: pending
- source_mode: pending
- symbols completed: pending
- failed_symbols: pending
- candidate_count: pending
- accepted_candidate_count: pending
- rejected_candidate_count: pending

## Gate Consistency Result

| symbol | best_config | gap_severity_for_training | gap_training_safe | gap_quality_gate_in_failed | gap_quality_gate_in_passed | candidate_status |
|---|---|---:|---:|---:|---:|---|
| pending | pending | pending | pending | pending | pending | pending |

## Decision

- ML38.2.1 technically completed: pending
- fresh wrapper completed end-to-end: pending
- ML38.2 accepted as automation-closed: pending
- model accepted: no
- can proceed to ML38.3: pending
- can proceed to ML39: no
