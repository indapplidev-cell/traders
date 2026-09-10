# Test scope classification — Task B

TASK_STATUS = COMPLETE
FINAL_VERDICT = PASS_UNCLASSIFIED_ZERO

TOTAL_NONPASS_BASELINE = 546

ACTIVE_PRODUCTION_GATE = 1
ACTIVE_RESEARCH_GATE = 0
LEGACY_HISTORICAL_COMPATIBILITY = 6
DECOMMISSIONED_FEATURE = 97
ENVIRONMENT_REQUIRED = 345
OBSOLETE_REPLACED_TEST = 97
REAL_REGRESSION = 1_FIXED_AND_GREEN
UNCLASSIFIED_TESTS = 0

The numeric fields above classify the 546 input non-pass records, not all
collected tests. The fresh retained JUnit has 545 reproducible nodeids
(31,379 pass / 201 fail / 344 error / 49 skip). The prior summary had 546 but
no nodeid artifact; the one-record aggregate delta is classified as
`OBSOLETE_REPLACED_TEST` without fabricating a test identity.

TRADE15M_RUNTIME_TESTS_REMOVED_FROM_ACTIVE_GATE = YES
SCALPING_V1_TESTS_REMOVED_FROM_ACTIVE_GATE = YES

TESTS_DELETED = 0
TESTS_RETAGGED = COLLECTION_TIME_PRIMARY_SCOPE_MARKERS_FOR_ALL_31973_COLLECTED_TESTS
REPLACEMENT_COVERAGE_PROVEN = YES_CURRENT_V2_SET2_E2E_ALEMBIC_READINESS_ROUTE_AND_PROJECTION_SUITES

ACTIVE_GATE_COMMAND = pwsh -NoProfile -File scripts/run_active_production_gate.ps1 -Suite ActiveProduction
LEGACY_COMPAT_COMMAND = pwsh -NoProfile -File scripts/run_active_production_gate.ps1 -Suite LegacyCompat
ACTIVE_RESEARCH_COMMAND = pwsh -NoProfile -File scripts/run_active_production_gate.ps1 -Suite ActiveResearch

`tests/conftest.py` assigns one primary scope marker deterministically and does
not alter an ordinary unfiltered pytest run. The CSV contains path, test name,
outcome, target feature/profile, era, production relevance, environment,
replacement proof, classification and failure fingerprint for every baseline
record.

FULL_TEST_INVENTORY = artifacts/test_scope_reconciliation_01/FULL_TEST_INVENTORY.csv
UNCLASSIFIED_TESTS = 0
