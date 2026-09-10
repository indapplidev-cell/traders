# Active production suite reconciliation — Task C

TASK_STATUS = COMPLETE
FINAL_VERDICT = PASS_ACTIVE_PRODUCTION_AND_RESEARCH_GREEN_LEGACY_REPORTED_SEPARATELY

ACTIVE_PRODUCTION_TESTS = 28244
ACTIVE_PRODUCTION_FAILED = 0
ACTIVE_PRODUCTION_ERRORS = 0

ACTIVE_RESEARCH_TESTS = 68
ACTIVE_RESEARCH_FAILED = 0

LEGACY_COMPAT_TESTS = 8
LEGACY_COMPAT_FAILED = 6

DECOMMISSIONED_TESTS_NOT_RUN = 97_BASELINE_NONPASS_RECORDS
ENVIRONMENT_SETUP = AUTOMATIC_EPHEMERAL_POSTGRES16_CONTAINER_LOOPBACK_TASK_DATABASE_CURRENT_ALEMBIC_HEAD

POSTGRES_VERSION = 16
ALEMBIC_HEAD = 0031_scalping_parameter_sets
NON_SUPERUSER_PRINCIPAL = paper_test_active_scope_NOSUPERUSER_NOCREATEDB_NOCREATEROLE_NOREPLICATION_NOBYPASSRLS

ACTIVE_PRODUCTION_NON_DB = 28200_PASSED_26_SKIPPED
POSTGRES_E2E = 18_PASSED
ACTIVE_RESEARCH = 68_PASSED
LEGACY_COMPAT_STATUS = REPORTED_INDEPENDENTLY_2_PASSED_6_FAILED_FROZEN_15M_V1_EXPECTATIONS

DESKTOP_SUITE = 1509_PASSED_2_SKIPPED_3029_SUBTESTS_PASSED; TWO_TRANSIENT_TCL_FILE_READ_SETUP_FAILURES_RERUN_2_PASSED; CHANGED_FOCUSED_SUITE_43_PASSED; INTERACTIVE_READONLY_ACCEPTANCE_PASS

The hermetic runner starts a unique PostgreSQL 16 container, creates a
loopback-only task database owned by a non-superuser role, and lets the E2E
fixture migrate to current Alembic head. It removes the container in `finally`.
Production data is never addressed.

The six legacy failures explicitly assert retired 15m/v1 defaults or active
runtime availability. They are retained as a separately visible debt report,
not skipped, xfailed, weakened, or counted as current production behavior.

ACTIVE_GATE_COMMAND = pwsh -NoProfile -File scripts/run_active_production_gate.ps1 -Suite ActiveProduction
ACTIVE_RESEARCH_COMMAND = pwsh -NoProfile -File scripts/run_active_production_gate.ps1 -Suite ActiveResearch
LEGACY_COMPAT_COMMAND = pwsh -NoProfile -File scripts/run_active_production_gate.ps1 -Suite LegacyCompat
