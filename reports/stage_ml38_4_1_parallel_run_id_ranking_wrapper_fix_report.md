# Stage ML38.4.1 — Parallel Run ID, Failed Candidate Ranking and Wrapper Metadata Fix
## Status

technical_status: completed
model_accepted: no
can proceed to ML38.4 rerun: yes
can proceed to ML39: no

### Starting Point

ML38.4 fresh FV3 rerun after ML38.3 gap semantics fix completed wrapper execution, but one ETHUSDT candidate failed with a database runtime error.

The runtime error was:

duplicate key value violates unique constraint "uq_ml_training_runs_run_id"

The failed run id had the form:

train_ml_candle_mlp_v1_2026_06_15_120520

This showed that the training run id was not unique enough for fast or parallel fresh-grid training runs.

A second issue was found in multi-symbol ranking: a FAILED candidate could be selected as the best candidate when its score was 0.0 and rejected candidates had negative scores.

#### Root Cause

The old training run id was derived from the model version and timestamp with second-level precision.

That was unsafe for parallel or near-parallel training runs.

The old ranking logic also treated FAILED candidates as normal candidates, which allowed runtime failures to be selected as best results.

Fixes

Implemented fixes:

training run id now includes safer unique suffix logic;
model version timestamp now includes microseconds;
training_run_id uniqueness is covered by a regression test;
FAILED candidates are excluded from best-candidate selection;
FAILED candidates are pushed down in ranked config output;
all-failed candidate sets no longer produce a false best candidate;
failed-candidate ranking behavior is covered by regression tests.
##### Tests

Passed:

python -m py_compile app/training/training_service.py
python -m pytest tests/test_ml38_4_1_training_run_id_uniqueness.py
python -m pytest tests/test_training_service.py
python -m pytest tests/test_ml38_4_1_failed_candidate_ranking.py
python -m pytest tests/test_multi_symbol_feature_regime_analyzer.py
python -m py_compile app/experiments/multi_symbol_feature_regime_analyzer.py
###### Decision

ML38.4.1 is accepted as a runtime stability and ranking fix.

The project can rerun ML38.4 fresh FV3 tuning after this commit.

The next rerun must confirm:

failed_candidate_count = 0
wrapper_completed_end_to_end = true
manual_archive_assembly_used = false
gap_quality_gate is not blocking due to trailing incomplete current-day range
Next Step

# Next stage:

ML38.4 — Fresh FV3 Tuning Rerun After ML38.4.1 Fix

ML39 is still too early.
