# TRADERS Parameter Sweep v2 mode startup fix and exclusive 5m v2 certification 02

FINAL_STATUS = FAIL
FINAL_VERDICT = MODE_MATRIX_INCOMPLETE_OR_BROKEN

# Root cause

ALL_FAILURE_REPRODUCED = YES; run `20260911_072717_549`
EXCEPTION_BEFORE = TypeError: float() argument must be a string or a real number, not 'NoneType'
ROOT_CAUSE = `sensitivity_preflight -> behavior_signature -> _gate_funnel -> _gate_result` called `float(row.get("expected_ev_r", -1e9))`; persisted production rows legitimately contain the key with value `None`, so `dict.get` did not use the numeric default and planning aborted before SearchPlan construction (`engine.py:1183` before the fix).
FILES_CHANGED_FOR_FIX = app/config/yaml_authority.py; config/research/research_parameters.yaml; traders_ml/parameter_sweep/cli.py; traders_ml/parameter_sweep/controller.py; traders_ml/parameter_sweep/engine.py; traders_ml/parameter_sweep/historical_replay.py; traders_ml/parameter_sweep/modes.py; traders_ml/parameter_sweep/state.py; traders_ml/parameter_sweep/ui.py
TYPE_ERROR_AFTER = 0

The exact fix treats absent/null precomputed EV, reserve, edge, stop and target evidence as a fail-closed gate value. It does not catch and continue after TypeError, return an empty plan, change any candidate range, or bypass behavioral no-op detection.

# Mode matrix

GUI_MODES = ALL; SET2_BASELINE; ONE_FACTOR_SENSITIVITY; SMALL_FAMILY_SEARCH; TOP_REGION_REFINEMENT; LOCAL_FINALIST_VALIDATION
CLI_MODES = ALL; SET2_BASELINE; ONE_FACTOR_SENSITIVITY; SMALL_FAMILY_SEARCH; TOP_REGION_REFINEMENT; LOCAL_FINALIST_VALIDATION
CANONICAL_MODES = ALL; SET2_BASELINE; ONE_FACTOR_SENSITIVITY; SMALL_FAMILY_SEARCH; TOP_REGION_REFINEMENT; LOCAL_FINALIST_VALIDATION
MODE_MATRIX_COMPLETE = NO; every exposed mode is enumerated and tiny-smoke/resume tested, but the current frozen dataset fails declared-family validation before a production SearchPlan is emitted.

ALL_PLAN_BUILD = FAIL; explicit `DECLARED_FAMILY_WITHOUT_ACTIVE_DIMENSION:GEOMETRY,SIGNAL`, not TypeError
ALL_ACTIVE_DIMENSIONS = 3; regime_lookback_candles; causal_reset_min_conditions; entry_refinement_1m_confirmation_count
ALL_RAW_COMBINATIONS = 27 after behavioral no-op removal
ALL_PLANNED_EVALUATIONS = 0
ALL_BEHAVIORALLY_DISTINCT = 4 theoretical representatives before the required declared-family validation gate

VALID_MODES_TESTED = 6/6
VALID_MODES_PASS = 0/6 on the current frozen dataset; 6/6 bounded tiny fully-active v2 fixture smokes PASS
INVALID_MODE_FAIL_CLOSED = PASS; UNKNOWN, empty, wrong types, trade-5m-v1, trade-15m-v1 and 15m are rejected as `UNSUPPORTED_RESEARCH_MODE` or `DATASET_CONFIG_INVALID`
GUI_CLI_PARITY = PASS on identical canonical mode/input fixture; mode, families, dimensions, raw count, planned count, search-space hash and plan hash are identical
RESUME_MODE_IDENTITY = PASS; all 6 same-mode resumes accepted; all 6 cross-mode resumes rejected; profile/timeframe/baseline checkpoint mismatches rejected

The post-fix production CLI run `mode-cert-all-full-20260911` and GUI-controller run `20260911_075232_477` both stopped on the same precise semantic validation error. The current dataset contains 11,501 rows. Its `strategy_score` range is 72.85..100 while the declared SIGNAL candidates are 45/55/65, so SIGNAL is genuinely inert. GEOMETRY is masked by the current first-rejection funnel and is behaviorally inert for the current rows. Relaxing this gate or changing ranges only to force a plan is prohibited.

# Exclusive v2 authority

NEW_RUN_PROFILE = trade-5m-v2
NEW_RUN_PRIMARY_TIMEFRAME = 5m
BASELINE_SET = scalping-v2-set-2

ACTIVE_PROHIBITED_15M = 0
ACTIVE_PROHIBITED_5M_V1 = 0
UNKNOWN_LEGACY_HITS = 0

TRADE_5M_V1_EVALUATED_ROWS = 0
TRADE_15M_V1_EVALUATED_ROWS = 0
UNKNOWN_PROFILE_EVALUATED_ROWS = 0
PRIMARY_15M_EVALUATED_ROWS = 0

Frozen dataset composition is profile `trade-5m-v2: 11501`, primary timeframe `5m: 11501`, configuration fingerprints `scalping-v2-set-2: 3464`, `trade-5m-v2-runtime-v1-2b79734d55b752c2: 5234`, `trade-5m-v2-runtime-v1-a266ebba53ba105a: 2803`, cost provenance `AUTHORITATIVE_CONFIG_MODEL_EXPLICIT_NON_HISTORICAL: 6637`, `HISTORICAL_RUNTIME_DIAGNOSTIC: 4864`. No row was evaluated in the failed current-dataset mode plan.

ACTIVE_FAMILIES = expected SIGNAL, REGIME, ENTRY, GEOMETRY; actual ENTRY, REGIME
FROZEN_FAMILIES = ECONOMICS, LIFECYCLE_SHADOW, RISK_SAFETY, COSTS
FROZEN_FAMILY_OVERRIDE_REJECTED = PASS

HIDDEN_BEHAVIORAL_DEFAULTS = 0; profile, primary timeframe, baseline, artifact schema and mode are explicit and validated. Artifact-schema v1 reader/migration compatibility remains classified as ARTIFACT_DATA/TEST_COMPATIBILITY and cannot select strategy semantics.

# Prior four-fix regression

DATASET_SELECTION = ALL_UNTIL_CUTOFF explicit
OMITTED_NEWER_ROWS = 0
DECLARED_FAMILIES_EQUALS_ACTIVE_FAMILIES = FAIL on the current frozen dataset; this is the fail-closed reason for the final verdict
BEHAVIORAL_NO_OP_DETECTED = PASS; stop_max_bps, strategy_minimum_score, target_min_bps
HISTORICAL_BASELINE_CONTROL_SEPARATED = PASS
SEARCH_VALIDATION_BASELINE_SEPARATED = PASS
STATUS_RESULTS_PARITY = PASS
REPORT_RESULTS_PARITY = PASS
CANDIDATE_PROMOTION_ELIGIBLE = NO
COUNTERFACTUAL_PARITY = PASS; config parity, rejection distribution parity and trade-count parity
NULL_CONFIG_METADATA = 0

# Safety

PRODUCTION_YAML_CHANGED = NO
ACTIVE_SET2_CHANGED = NO
TRADING_LOGIC_CHANGED = NO
DB_SCHEMA_CHANGED = NO
DEPLOY_PERFORMED = NO

LIVE_STATE = FALSE
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0

# Delivery

FOCUSED_TESTS = 129 unique focused tests PASS by the main run plus isolated reruns; one transient Tcl bootstrap failure reran PASS after mandatory PID/HWND desktop preflight
COMPILE = PASS
COMMITS = 43b6761acdcf3ed4d1c3fb13f8920e4f8f3f00d0; a262a9e42335c58df8b5e53ef4194d5812045848; documentation commit resolves via Git history
PUSH = PROJECT_STATE_PASS; documentation reconciliation resolves via Git history and final handoff
WORKTREE = CLEAN_AFTER_DOCUMENTATION_RECONCILIATION

REMAINING_BLOCKERS = Current frozen dataset does not provide behaviorally active SIGNAL and GEOMETRY families; TOP_REGION_REFINEMENT and LOCAL_FINALIST_VALIDATION also have zero generated candidates after the 27-point active space is exhausted by earlier stages. Per task restrictions, ranges, gates, YAML candidate values and Set #2 were not changed to manufacture a PASS.

Detailed machine-readable evidence: `docs/audits/TRADERS_PARAMETER_SWEEP_V2_MODE_MATRIX_02.json`.
