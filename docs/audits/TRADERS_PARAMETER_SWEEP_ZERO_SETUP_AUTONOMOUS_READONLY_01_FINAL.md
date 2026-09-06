# TRADERS Parameter Sweep zero-setup autonomous readonly 01

`RECONCILED_AT_UTC = 2026-09-06T23:27:48Z`

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS

PARAMETER_SWEEP_MODULE = app.research.scalping_v2_parameter_sweep
OPERATOR_COMMAND = python -m app.research.scalping_v2_parameter_sweep --config config/research/scalping_v2_parameter_sweep.yaml --run-id <manual-run-id>

ZERO_SETUP = PASS
MANUAL_DATABASE_URL_REQUIRED = NO
PROJECT_DB_BINDING = PASS_PROJECT_PROTECTED_BINDING_READONLY_ROLE_WITH_EXISTING_HOST_ENDPOINT
DATABASE_RESOLUTION_ORDER = EXPLICIT_CLI_DEV_TEST_ADMIN_THEN_PROJECT_PROTECTED_BINDING_THEN_DATABASE_URL_COMPATIBILITY_THEN_FAIL_CLOSED
DATABASE_SESSION_READ_ONLY = PASS_POSTGRES_TRANSACTION_READ_ONLY_ON
WRITE_GUARD = PASS_APPLICATION_SELECT_ONLY_AND_POSTGRES_INSERT_UPDATE_DELETE_DDL_REJECTED
PRODUCTION_MUTATIONS = 0

PREFLIGHT = PASS_ALL_REQUIRED_CHECKS
PREFLIGHT_SECRET_OUTPUT = 0
SCHEMA_HEAD = 0030_paper_recovery_close
PROFILE = trade-5m-v2
DATASET_SOURCE = PRODUCTION_PAPER_READONLY
DATASET_ROWS = 53

SEARCH_SPACE = VALID_SCHEMA2_RUNTIME_POLICY_DIMENSIONS_BOUNDED_QUERY_MAX5000
BOUNDED_SMOKE_CONFIGS = 2
BOUNDED_SMOKE_REPORT = artifacts/scalping_v2_parameter_sweep/codex-zero-setup-smoke/REPORT.md

RUN_CONFIG_ARTIFACT = artifacts/scalping_v2_parameter_sweep/codex-zero-setup-smoke/RUN_CONFIG.yaml
PREFLIGHT_ARTIFACT = artifacts/scalping_v2_parameter_sweep/codex-zero-setup-smoke/PREFLIGHT.json
RESULTS_CSV = artifacts/scalping_v2_parameter_sweep/codex-zero-setup-smoke/RESULTS.csv
RESULTS_JSON = artifacts/scalping_v2_parameter_sweep/codex-zero-setup-smoke/RESULTS.json
TOP_CONFIGS = artifacts/scalping_v2_parameter_sweep/codex-zero-setup-smoke/TOP_CONFIGS.json
REJECTED_CONFIGS = artifacts/scalping_v2_parameter_sweep/codex-zero-setup-smoke/REJECTED_CONFIGS.json
REPORT_MD = artifacts/scalping_v2_parameter_sweep/codex-zero-setup-smoke/REPORT.md

FULL_SWEEP_RUN_BY_CODEX = NO

FOCUSED_TESTS = PASS_21_TESTS_RESEARCH_PARAMETER_SWEEP
REGRESSION = PASS_48_TESTS_RESEARCH_AND_PRODUCTION_DB_READONLY_CREDENTIAL_CONTROLS

SERVER_HEAD = 5c1216ecfd8894ce8e78de9e72dbd6a35dad66a0
SERVER_REMOTE_HEAD = 5c1216ecfd8894ce8e78de9e72dbd6a35dad66a0
WORKTREE = TASK_FILES_CLEAN_UNRELATED_PREEXISTING_AUDIT_MODIFICATION_PRESERVED

LIVE_STATE_AFTER = DISABLED
REAL_BINANCE_ORDER_API_CALLS = 0
SECRET_OUTPUT = 0

REMAINING_BLOCKERS = FULL_MANUAL_SWEEP_NOT_RUN; HISTORICAL_TIMESTAMPED_TIME_STOP_COST_EVIDENCE_REMAINS_INSUFFICIENT_FOR_PARAMETER_ACCEPTANCE; NO_PARAMETER_PROMOTION
NEXT_MANUAL_ACTION = RUN_THE_DOCUMENTED_ONE_COMMAND_FULL_SWEEP_AND_REVIEW_VALIDATION_HOLDOUT_WITHOUT_AUTOMATIC_PROMOTION
```

The bounded smoke was launched from the standard project root without setting
`DATABASE_URL`. The protected binding resolved the dedicated
`traders_readonly_api` role and the existing host endpoint. Preflight observed
PostgreSQL transaction read-only mode and independently attempted safe zero-row
INSERT, UPDATE, and DELETE statements plus transactional temporary DDL; all four
were rejected by PostgreSQL. The application adapter also rejects non-SELECT
statements before execution.

The sweep has no database write method and no approval, selector, command,
order, fill, position, production-config, LIVE, or Binance order integration.
Natural global PAPER counters are not used as sole mutation evidence. The
session guarantee, rejected probes, task code-path inspection, and zero task
markers establish `PRODUCTION_MUTATIONS_BY_SWEEP = 0`.
