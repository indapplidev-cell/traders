# Parameter Sweep v2 ALL full fix, local GUI acceptance, commit and push 01

FINAL_STATUS = PASS
FINAL_VERDICT = ALL_MODE_PLANNING_FIXED_LOCAL_GUI_ACCEPTED_COMMITTED_AND_PUSHED

## Before

HEAD_BEFORE = 8d44a419d1dcf4805ccba0ae261b931e1900c669
ALL_FAILURE_REPRODUCED = YES
PRE_FIX_RUN_ID = 20260911_193819_347
PRE_FIX_FAILURE_CODE = DECLARED_FAMILY_WITHOUT_ACTIVE_DIMENSION:GEOMETRY,SIGNAL
PRE_FIX_SEARCH_DIMENSIONS = []
PRE_FIX_PLANNED_CONFIGS = 0
PRE_FIX_COMPLETED_CONFIGS = 0
PRE_FIX_ERROR_CONFIGS = 1
PRE_FIX_TRACEBACK = artifacts/scalping_v2_parameter_sweep/20260911_193819_347/ERROR.20260911T164130.345161Z.12028.3708.log

## Root cause

ROOT_CAUSE = The shared planner's dataset-sensitive no-op signature used only the sequential `_gate_funnel` aggregate. Early frozen economics rejections therefore masked later GEOMETRY predicates even though the current row-level stop/target distributions cross their research ranges. Independently, the research-only SIGNAL range `[45,55,65]` was entirely below the frozen dataset's observed strategy-score minimum `72.85`, so it was genuinely inert. The fail-closed family coverage gate correctly rejected the resulting incomplete registry.
ROOT_CAUSE_FILE = traders_ml/parameter_sweep/engine.py; config/research/research_parameters.yaml
ROOT_CAUSE_LINE = pre-fix engine behavior_signature at 2017-2021; pre-fix research YAML strategy_minimum_score at 101
ROOT_CAUSE_FUNCTION = _run_impl.behavior_signature -> sensitivity_preflight
ROOT_CAUSE_EXPLANATION = GEOMETRY was a false no-op caused by upstream-gate masking; SIGNAL was a true current-dataset no-op caused by a stale research candidate range. Neither defect was in production strategy logic or Set #2.

DECLARED_FAMILIES_BEFORE = SIGNAL,REGIME,ENTRY,GEOMETRY
ACTIVE_FAMILIES_BEFORE = REGIME,ENTRY
DIMENSIONS_BEFORE_FILTER = 29 YAML search-space dimensions
DIMENSIONS_AFTER_FILTER = strategy_minimum_score,regime_lookback_candles,stop_max_bps,target_min_bps,causal_reset_min_conditions,entry_refinement_1m_confirmation_count
DIMENSIONS_REMOVED = strategy_minimum_score,stop_max_bps,target_min_bps
REMOVAL_REASONS = BEHAVIORAL_NO_OP after aggregate sequential-funnel signature; SIGNAL candidate range did not cross the observed score band

PLANNING_SNAPSHOT_1_DECLARED = SIGNAL,REGIME,ENTRY,GEOMETRY
PLANNING_SNAPSHOT_2_REGISTRY_BEFORE_FILTER = 29 dimensions recorded in post-fix PARAMETER_REGISTRY.json
PLANNING_SNAPSHOT_3_AFTER_MODE_FAMILY_FILTER = 6 targeted dimensions
PLANNING_SNAPSHOT_4_AFTER_ACTIVATION_PREDICATES = 6
PLANNING_SNAPSHOT_5_AFTER_BASELINE_CANDIDATE_RESOLUTION = 6
PLANNING_SNAPSHOT_6_AFTER_NO_OP = 6
PLANNING_SNAPSHOT_7_AFTER_BEHAVIORAL_DEDUP = 6 dimensions; 126 distinct planned configurations
PLANNING_SNAPSHOT_8_FINAL_GROUPED = SIGNAL:1; REGIME:1; ENTRY:2; GEOMETRY:2

## Fix

FIX_SCOPE = Add independent row-level signatures for the six researched policy predicates while retaining the sequential funnel, update only the research SIGNAL candidate range to `[55,75,85]`, and persist complete registry/filter/no-op provenance.
FILES_CHANGED = config/research/research_parameters.yaml; traders_ml/parameter_sweep/engine.py; traders_ml/parameter_sweep/targeted.py; tests/research/test_parameter_sweep_targeted.py; tests/research/test_scalping_v2_parameter_sweep.py; docs/audits/TRADERS_PARAMETER_SWEEP_ALL_MODE_FULL_FIX_LOCAL_UPDATE_GUI_ACCEPTANCE_COMMIT_PUSH_01_FINAL.md; online_trader.md
RESEARCH_YAML_CHANGED = YES; research-only strategy_minimum_score candidates
PRODUCTION_YAML_CHANGED = NO
ACTIVE_SET2_CHANGED = NO
TRADING_LOGIC_CHANGED = NO

## Mode certification

GUI_MODES = ALL; SET2_BASELINE; ONE_FACTOR_SENSITIVITY; SMALL_FAMILY_SEARCH; TOP_REGION_REFINEMENT; LOCAL_FINALIST_VALIDATION
CLI_MODES = ALL; SET2_BASELINE; ONE_FACTOR_SENSITIVITY; SMALL_FAMILY_SEARCH; TOP_REGION_REFINEMENT; LOCAL_FINALIST_VALIDATION
CANONICAL_MODES = ALL; SET2_BASELINE; ONE_FACTOR_SENSITIVITY; SMALL_FAMILY_SEARCH; TOP_REGION_REFINEMENT; LOCAL_FINALIST_VALIDATION
MODE_MATRIX_COMPLETE = YES

MODE_MATRIX = ALL PASS raw-stage-hypotheses144 planned126; SET2_BASELINE PASS 1/1; ONE_FACTOR_SENSITIVITY PASS 10/8; SMALL_FAMILY_SEARCH PASS 60/60; TOP_REGION_REFINEMENT PASS 40/40; LOCAL_FINALIST_VALIDATION PASS 33/33; TYPE_ERROR0 for every mode
MODE_MATRIX_SHARED_DATASET = run 20260911_195409_637 frozen snapshot; search_space_hash 8bf667bb576fb7cc900e52a7e548bc07d28d43da518ad059e9a59e5adc1f732a
GUI_CLI_PLAN_PARITY = PASS; shared canonical mode/parser/planner and focused identity comparison
RESUME_MODE_IDENTITY = PASS; same mode PASS, cross mode/profile/timeframe/baseline mismatches REJECT

## ALL after

POST_FIX_RUN_ID = 20260911_195409_637
ALL_PLAN_BUILD = PASS
ALL_ACTIVE_FAMILIES = SIGNAL,REGIME,ENTRY,GEOMETRY
ALL_ACTIVE_DIMENSIONS = 6; strategy_minimum_score; regime_lookback_candles; causal_reset_min_conditions; entry_refinement_1m_confirmation_count; stop_max_bps; target_min_bps
ALL_RAW_COMBINATIONS = 1296
ALL_PLANNED_EVALUATIONS = 126
ALL_COMPLETED_CONFIGS = 1
ALL_ERROR_CONFIGS = 0
POST_FIX_STATE = CANCELLED_AFTER_REQUESTED_BOUNDED_STOP_WITH_RESUME_AVAILABLE
POST_FIX_FAILURE_CODE = NONE
POST_FIX_STATUS = artifacts/scalping_v2_parameter_sweep/20260911_195409_637/STATUS.json
POST_FIX_GUI_CAPTURE_SHA256 = AB421BAFE931C07FEF1152C15784477654160E432B5E532023826F2F0ADBEFA9

## Legacy purity

ACTIVE_15M_DEPENDENCIES = 0
ACTIVE_5M_V1_DEPENDENCIES = 0
TRADE_15M_V1_EVALUATED_ROWS = 0
TRADE_5M_V1_EVALUATED_ROWS = 0
UNKNOWN_PROFILE_EVALUATED_ROWS = 0
PRIMARY_15M_EVALUATED_ROWS = 0
DATASET_PROFILE_COMPOSITION = trade-5m-v2:12139
DATASET_TIMEFRAME_COMPOSITION = 5m:12139

## Previous fixes

DATASET_SELECTION = explicit ALL_UNTIL_CUTOFF; loaded12139/eligible12139
OMITTED_NEWER_ROWS = 0
STATUS_RESULTS_PARITY = PASS; completed1 equals RESULTS.jsonl rows1
REPORT_RESULTS_PARITY = PASS; focused regression
COUNTERFACTUAL_PARITY = PASS; focused regression
NULL_CONFIG_METADATA = 0
BEHAVIORAL_NO_OP_DETECTION = ENABLED
BEHAVIORAL_DUPLICATE_INFLATION = PREVENTED; 144 stage hypotheses reduced to 126 distinct evaluations

## Local update

LOCAL_RESEARCH_GUI_SOURCE = D:/disk_E/game_projects/traders/traders-ml/traders_ml/parameter_sweep
LOCAL_RESEARCH_GUI_ENV = C:/Program Files/Python311/python.exe
LOCAL_RESEARCH_GUI_LAUNCHER = python -m traders_ml.parameter_sweep
LOCAL_RESEARCH_GUI_UPDATE = PASS; restarted PID 18936 imports repository engine.py and the fixed commit
PRODUCTION_DEPLOY = NO

## Safety

DB_SCHEMA_CHANGED = NO
PRODUCTION_SERVICES_RESTARTED = NO; orchestrator5m/collector/readonly/postgres restart count0
LIVE_STATE = FALSE; fresh `/api/v1/paper/runtime/status` reports mode PAPER and live_allowed false
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0
ACTIVE_SET2_FRESH = scalping-v2-set-2; resolved hash 49d89364e72d53aed0f59aa7ff9e7ce5335933049b3ff68f1221e1ba36496edf

## Delivery

FOCUSED_TESTS = PASS; 99 passed in 104.93s plus earlier isolated reruns PASS
COMPILE = PASS; python -m compileall -q traders_ml/parameter_sweep app/research/scalping_v2_parameter_sweep.py app/config/yaml_authority.py
IMPLEMENTATION_COMMIT = 0dd5f0aa6c3c5d0a0ae3aea752b694af384a67cb
TEST_COMMIT = 0dd5f0aa6c3c5d0a0ae3aea752b694af384a67cb
DOCUMENTATION_COMMIT = SELF; resolve with `git log -1 --format=%H -- docs/audits/TRADERS_PARAMETER_SWEEP_ALL_MODE_FULL_FIX_LOCAL_UPDATE_GUI_ACCEPTANCE_COMMIT_PUSH_01_FINAL.md`
PUSH = PASS for implementation commit; documentation reconciliation is pushed after its commit
AHEAD_BEHIND = 0/0 after implementation push
WORKTREE = CLEAN after documentation reconciliation commit and push

REMAINING_BLOCKERS = Parameter Sweep ALL launch bug: NONE. Project-wide blockers remain natural eligible PAPER approval not observed and clean 72h soak not mature; LIVE promotion remains prohibited.
