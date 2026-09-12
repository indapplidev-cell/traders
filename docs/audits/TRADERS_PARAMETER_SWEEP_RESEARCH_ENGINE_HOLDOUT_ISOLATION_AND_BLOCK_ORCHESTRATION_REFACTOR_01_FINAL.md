# TRADERS_PARAMETER_SWEEP_RESEARCH_ENGINE_HOLDOUT_ISOLATION_AND_BLOCK_ORCHESTRATION_REFACTOR_01

```text
FINAL_STATUS = PASS
FINAL_VERDICT = RESEARCH_ENGINE_HOLDOUT_ISOLATED_BEHIND_IMMUTABLE_FINALIST_FREEZE_AND_ZERO_POSITIVE_BLOCK_ORCHESTRATION_REPAIRED

# Scope

FILES_CHANGED = traders_ml/parameter_sweep/artifact_v2.py; traders_ml/parameter_sweep/checkpoint.py; traders_ml/parameter_sweep/cli.py; traders_ml/parameter_sweep/controller.py; traders_ml/parameter_sweep/engine.py; traders_ml/parameter_sweep/integrity.py; traders_ml/parameter_sweep/ranking.py; traders_ml/parameter_sweep/research_protocol.py; traders_ml/parameter_sweep/state.py; traders_ml/parameter_sweep/ui.py; tests/research/test_parameter_sweep_holdout_protocol.py; tests/research/test_parameter_sweep_report_semantics.py; tests/research/test_scalping_v2_parameter_sweep.py; docs/audits/HOLDOUT_ACCESS_INVENTORY.json; docs/audits/FINALIST_FREEZE.example.json; docs/audits/TRADERS_PARAMETER_SWEEP_RESEARCH_ENGINE_HOLDOUT_ISOLATION_AND_BLOCK_ORCHESTRATION_REFACTOR_01_FINAL.md; online_trader.md
PRODUCTION_TRADING_SOURCE_CHANGED = NO
PRODUCTION_YAML_CHANGED = NO
RESEARCH_SEARCH_RANGES_CHANGED = NO
ACTIVE_SET2_CHANGED = NO
DB_SCHEMA_CHANGED = NO
PRODUCTION_DEPLOY = NO
TOOLING_ORCHESTRATION_ONLY = YES
SEARCH_SPACE_CHANGED = NO

# Holdout forensic

PRE_FIX_HOLDOUT_ACCESS_POINTS = 8_PRE_FREEZE_FORBIDDEN_PLUS_1_REPORT_ONLY
PRE_FREEZE_FORBIDDEN_BEFORE = 8
PRE_FREEZE_FORBIDDEN_AFTER = 0
UNKNOWN_HOLDOUT_ACCESS_AFTER = 0
HOLDOUT_ACCESS_INVENTORY = docs/audits/HOLDOUT_ACCESS_INVENTORY.json

# Phase model

RESEARCH_PHASES = CALIBRATION_SEARCH; SEPARABILITY_ANALYSIS; DATA_DRIVEN_RANGE_GENERATION; VALIDATION_RANKING; FINALIST_FREEZE; HOLDOUT_EVALUATION; FINAL_REPORT
PHASE_GUARD = PASS_FAIL_CLOSED_HOLDOUT_ACCESS_BEFORE_FINALIST_FREEZE

# Orchestration

BLOCK1_ZERO_POSITIVE_RESULT = NO_POSITIVE_CONFIG_IN_CURRENT_SPACE
BLOCK2_RUNS_AFTER_ZERO_POSITIVE = PASS_STARTED
BLOCK3_RUNS_AFTER_ZERO_POSITIVE = PASS_STARTED
BLOCK4_REACHABLE = PASS_TRUE

# Winner/loser support

SEPARABILITY_DATASET_SPLITS = CALIBRATION_PLUS_VALIDATION_ONLY
HOLDOUT_ROWS_IN_SEPARABILITY = 0
PRE_ENTRY_FEATURE_CAUSALITY = PASS_FEATURE_TIMESTAMP_LTE_ENTRY_DECISION_TIMESTAMP_UNPROVEN_ROWS_EXCLUDED

# Range support

DATA_DRIVEN_RANGE_ARTIFACT = PASS_DATA_DRIVEN_SEARCH_RANGES_JSON_EXPLICIT_RUN_LOCAL_OVERRIDE_SUPPORTED
RANGE_ARTIFACT_MUTATES_YAML = NO

# Finalist freeze

FINALIST_SELECTION_USES_HOLDOUT = NO
FINALIST_FREEZE_IMPLEMENTED = PASS
FINALIST_FREEZE_IMMUTABLE = PASS
FREEZE_HASH = 44ccbe1a79841406b8e56d8c2bcfc74e1c29d92dff6d560dcedf1b342f5aab31_BOUNDED_ACCEPTANCE_RUN

# Holdout

HOLDOUT_BEFORE_FREEZE = 0
HOLDOUT_NON_FINALISTS = 0
HOLDOUT_ONE_SHOT = PASS_EXACTLY_ONCE_PER_FROZEN_FINALIST
POST_HOLDOUT_RETUNING_ALLOWED = NO

# Resume

RESUME_FREEZE_INTEGRITY = PASS
RESUME_HOLDOUT_STATE_INTEGRITY = PASS_HASHED_AND_POST_OPEN_INCOMPLETE_RESUME_REJECTED

# Regression

ALL_MODE = PASS
MODE_MATRIX = PASS
GUI_CLI_PARITY = PASS
OMITTED_NEWER_ROWS = 0
REPORTING_PARITY = PASS
COVERAGE_ACCOUNTING = PASS
SEED_PROVENANCE = PASS
COUNTERFACTUAL_PARITY = PASS
ARTIFACT_V2 = PASS
INLINE_MARKET_PATHS = 0

# Safety

LIVE_STATE = FALSE
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0

# Delivery

FOCUSED_TESTS = PASS_146_PASSED
COMPILE = PASS
LOCAL_RESEARCH_TOOL_UPDATE = PASS_REPOSITORY_DIRECT_UI_AND_ENGINE_IMPORT_SCHEMA_V4
PROJECT_STATE_COMMITS = b31587ae57652754d8a75237861e63fb998c05bb; 5ccf694b0dcb60d1141acfa4c36f93d66c8868a5
DOCUMENTATION_COMMIT = RESOLVE_WITH_GIT_LOG_PATH
PUSH = PENDING_FINAL_DOCUMENTATION_COMMIT
AHEAD_BEHIND = PENDING_FINAL_PUSH
WORKTREE = PENDING_FINAL_DOCUMENTATION_COMMIT

REMAINING_BLOCKERS = NO_REAL_OPTIMAL_CONFIGURATION_SEARCH_PERFORMED_BY_SCOPE; EXISTING_PROFITABILITY_EVIDENCE_REMAINS_NEGATIVE; NEXT_CAMPAIGN_REQUIRES_AN_UNTOUCHED_HOLDOUT
NEXT_RECOMMENDED_ACTION = START_A_SEPARATE_NEW_CAMPAIGN_AT_BLOCK_2_WINNER_LOSER_SEPARABILITY_THEN_BLOCK_3_DATA_DRIVEN_RANGE_GENERATION_AND_BLOCK_4_EXPANDED_SEARCH; FREEZE_VALIDATION_SELECTED_FINALISTS_BEFORE_ONE_SHOT_HOLDOUT; DO_NOT_REUSE_THIS_TASKS_SYNTHETIC_HOLDOUT_FOR_TUNING
```

## Acceptance evidence

The full research suite completed with `146 passed in 96.10s`; affected
packages and research tests compiled successfully. The bounded Tk/controller
fixture (repository source, no production UI or service action) produced:

```text
RUN = 20260912_073616_580
INTEGRITY = PASS
BLOCK1 = NO_POSITIVE_CONFIG_IN_CURRENT_SPACE
BLOCK2 = STARTED
BLOCK3 = STARTED
BLOCK4_REACHABLE = true
WINNER_LOSER_ROWS = 4
HOLDOUT_ROWS_IN_WINNER_LOSER = 0
CAUSALITY_VIOLATIONS = 0
FINALISTS_FROZEN = 2
HOLDOUT_RESULT_ROWS = 2
NON_FINALIST_HOLDOUT_EVALUATIONS = 0
RANGE_ARTIFACT_MUTATES_YAML = false
```

The fixture is bounded synthetic acceptance only. It is not an optimal-config
search, it creates no authoritative research range, and its holdout results
must not be used for future tuning.

## Architecture decision

Search evaluators now reject a split map containing HOLDOUT. Calibration,
sensitivity, behavioral dedup, validation ranking, Pareto, performance class,
winner/loser extraction, and range generation operate without holdout outcome
metrics. Pre-freeze result rows expose holdout fields as `NOT_EVALUATED`, never
zero.

Validation-only ranking creates an immutable `FINALIST_FREEZE.json` containing
campaign, dataset, split, baseline, search-space, selection-rule, finalist and
validation-snapshot identities. The guard then grants HOLDOUT only to those
IDs and records one row per finalist in `HOLDOUT_RESULTS.jsonl`. Candidate,
range or phase changes after opening holdout fail closed. A crash after opening
but before durable completion requires a new campaign rather than replaying the
same holdout.

`DATA_DRIVEN_SEARCH_RANGES.json` is non-authoritative and run-local. It is
consumed only through the explicit `--range-override` CLI option and never
modifies YAML.

## Production isolation

No file under `config/trading`, `config/runtime`, `config/system`,
`config/research`, production trading code, database models or Alembic changed.
No service was rebuilt, restarted or deployed. Read-only runtime inspection
showed the existing Readonly and Operator Control containers healthy with zero
restarts; the host readiness request timed out and made no mutation. The latest
proved project snapshot remains authoritative for `LIVE=false`; this task made
no execution/API mutation and no Binance order call.
