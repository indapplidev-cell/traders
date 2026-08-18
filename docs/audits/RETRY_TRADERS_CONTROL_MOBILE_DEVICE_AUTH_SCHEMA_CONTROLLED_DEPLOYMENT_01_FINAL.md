# RETRY_TRADERS_CONTROL_MOBILE_DEVICE_AUTH_SCHEMA_CONTROLLED_DEPLOYMENT_01

Captured from production on `2026-08-18`. This retry supersedes the earlier
preflight-blocked attempt and records a successful schema migration followed by
a blocked cross-runtime acceptance.

## Decision

```text
TASK_STATUS = BLOCKED_AFTER_SUCCESSFUL_SCHEMA_DEPLOYMENT
FINAL_VERDICT = BLOCKED_RUNTIME_ACCEPTANCE_AFTER_PASS_0015_TO_0016_SCHEMA_DEPLOYMENT
BLOCKER_CODE = READONLY_PAPER_SCHEMA_EXPECTATION_REMAINS_0015
SECONDARY_BLOCKER = MOBILE_RUNTIME_PRINCIPAL_HAS_NO_0016_TABLE_PRIVILEGES
STOP_CONDITION = SCHEMA_DEPLOYED_BUT_EXISTING_READINESS_PROJECTION_FAILS_CLOSED
NEXT_ACTION = TRADERS_CONTROL_MOBILE_DEVICE_AUTH_SCHEMA_COMPATIBILITY_AND_RUNTIME_PRIVILEGE_REMEDIATION_01
PROJECT_STATE_AUDIT_COMMIT = SELF
PROJECT_STATE_AUDIT_COMMIT_RESOLUTION = git log -1 --format=%H -- docs/audits/RETRY_TRADERS_CONTROL_MOBILE_DEVICE_AUTH_SCHEMA_CONTROLLED_DEPLOYMENT_01_FINAL.md
```

## Baseline and recovery gate

```text
SERVER_HEAD_BEFORE = 50d7a19ac35039c6c07e18a38358a3aec5e76462
SERVER_TREE_BEFORE = 116627408e45aa64ee57b11576aef99a10132e14
SERVER_ROOT_CLEAN_BEFORE = YES
DESKTOP_HEAD_BEFORE = 96b79a2631466ad5a4af7cc6677ef99f60d112cb
DESKTOP_ROOT_CLEAN_BEFORE = YES
MOBILE_HEAD_BEFORE = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
MOBILE_ROOT_CLEAN_BEFORE = YES

WAL_READY_BEFORE = true
PITR_READY_BEFORE = true
LINEAGE_VALID_BEFORE = true
CONTIGUOUS_DURATION_SECONDS_BEFORE = 624430
PHYSICAL_WAL_GAP_BEFORE = false
ACTIVE_UNRESOLVED_FAILURES_BEFORE = 0
EXPORT_BACKLOG_BEFORE = 0
PENDING_ARCHIVE_STATUS_BEFORE = 0
POSTGRESQL_HEALTH_BEFORE = healthy
PRODUCTION_ALEMBIC_BEFORE = 0015_trading_universe_activation
MOBILE_TABLE_COUNT_BEFORE = 0
```

Readonly core health was `OK`; Analysis and Markets returned HTTP 200. Control
was `ARMED`, generation 6, `HEALTHY`, audit `PASS`; the existing canary was
`WAITING_FOR_ELIGIBLE_APPROVAL` with zero commands and zero positions. LIVE was
forbidden.

## Exact migration

```text
SOURCE_ALEMBIC_HEAD_COUNT = 1
SOURCE_ALEMBIC_HEAD = 0017_parallel_trade_profiles
DEPLOYMENT_TARGET = 0016_control_mobile_device_security
MIGRATION_DOWN_REVISION = 0015_trading_universe_activation
MIGRATION_SHA256 = C520125983EE9638F812FC2D7EFED38328669A5B54E6BACFFF487B3D5B5BF8DC
MIGRATION_IMAGE = sha256:27a7b350ab0166037c3a62ab07b254d25aa4f74d829f25e6cbf4f288fc206232
MIGRATION_STARTED_AT_UTC = 2026-08-18T13:31:46.6980602Z
MIGRATION_COMPLETED_AT_UTC = 2026-08-18T13:32:02.5405253Z
MIGRATION_RESULT = PASS_TRANSACTIONAL_DDL
PRODUCTION_ALEMBIC_AFTER = 0016_control_mobile_device_security
0017_APPLIED = NO
```

The first host-Alembic invocation never connected because the protected URL
uses Docker DNS name `postgres`; production remained unchanged. The successful
attempt used a task-named current-source image on the existing private Docker
network and the protected env-file. No credential value was printed or hashed.

PostgreSQL created `control_mobile_devices`,
`control_mobile_replay_nonces`, the composite replay primary key, device foreign
key with `ON DELETE RESTRICT`, all declared checks, and the expiry index. The
metadata exactly matches migration `0016`; both tables contain zero rows.

```text
PRODUCTION_SCHEMA_MIGRATIONS_BY_TASK = 1
PRODUCTION_BUSINESS_DATA_MUTATIONS_BY_TASK = 0
DEVICE_ENROLLMENT_BY_TASK = 0
REPLAY_CLAIMS_BY_TASK = 0
PRODUCTION_ROLE_OR_GRANT_MUTATIONS_BY_TASK = 0
TLS_CERTIFICATE_OR_KEY_PROVISIONED_BY_TASK = NO
MOBILE_TLS_RUNTIME_STARTED_BY_TASK = NO
CONTROL_LAN_LISTENER_OR_FIREWALL_MUTATION_BY_TASK = NO
ALEMBIC_STAMP_BY_TASK = NO
AUTOMATIC_DOWNGRADE_BY_TASK = NO
```

## Postflight and blocker

```text
POSTGRESQL_RESTART_DELTA = 0
MARKET_DATA_RESTART_DELTA = 0
ORCHESTRATOR_RESTART_DELTA = 0
READONLY_RESTART_DELTA = 0
CONTROL_RESTART_DELTA = 0
READONLY_CORE_HEALTH_AFTER = OK
READONLY_ANALYSIS_AFTER = HTTP200
READONLY_MARKETS_AFTER = HTTP200
CONTROL_AFTER = ARMED_GENERATION6_HEALTHY_AUDIT_PASS
CANARY_AFTER = WAITING_COMMAND0_POSITION0
LIVE_AFTER = DISABLED
TRADE_15M_AFTER = 2026-08-18T13:30:00Z_10_OF_10_COMPLETED
MARKET_DATA_AFTER = OPERATIONAL_READY_OVERALL_OK

WAL_ARCHIVE_AFTER = PASS
WAL_READY_AFTER = true
PITR_READY_AFTER = true
LINEAGE_VALID_AFTER = true
CONTIGUOUS_DURATION_SECONDS_AFTER = 624434
PHYSICAL_WAL_GAP_AFTER = false
ACTIVE_UNRESOLVED_FAILURES_AFTER = 0
EXPORT_BACKLOG_AFTER = 0
PENDING_ARCHIVE_STATUS_AFTER = 0
```

The additive schema did not interrupt the 15m search: the boundary closed at
`13:30:00Z` completed for all ten symbols with zero trading mutations. All five
production services retained restart count zero.

Full runtime acceptance is not PASS. The deployed Readonly source declares
`PAPER_SCHEMA_EXPECTED = 0015_trading_universe_activation`; after the exact
migration it reports `paper_schema_ready=false` and
`PAPER_SCHEMA_NOT_DEPLOYED`. This safely blocks continuation eligibility while
leaving core GET endpoints and Control status healthy. In addition,
`traders_paper_runtime` has no SELECT/INSERT/UPDATE/DELETE privileges on either
new table because role/grant mutation was outside the authorized schema-only
scope. No automatic downgrade, stamp, grant expansion, runtime rebuild, or
restart was performed.

## Validation

```text
FOCUSED_SUITE = tests/control_mobile_security
FIRST_RUN = 24_PASSED_1_FAILED
FIRST_FAILURE = FIXED_2026-08-17T12:00Z_CERTIFICATE_EXPIRED_AFTER_24_HOURS
TEST_ONLY_REMEDIATION = TLS_CERTIFICATE_VALIDITY_ANCHORED_TO_RUNTIME_UTC
DETERMINISTIC_REQUEST_SIGNING_CLOCK = UNCHANGED
FINAL_RUN = 25_PASSED
PY_COMPILE = PASS
GIT_DIFF_CHECK = PASS
```

The time-bomb fix changes no runtime code or security policy. It keeps request
signature tests deterministic and makes only the ephemeral certificate validity
track the wall clock required by the real TLS verifier.
