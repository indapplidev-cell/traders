DOCUMENT = online_trader.md
DOCUMENT_ROLE = SINGLE_SOURCE_OF_TRUTH_FOR_PROJECT_STATUS
DOCUMENT_SNAPSHOT_TYPE = POST_TASK_PROVEN_STATE
PROJECT = traders-ml

STATUS_AS_OF_COMMIT = d3a7f6b4b188349a68396b2950a55518c93e270b
DOCUMENT_REVISION = SELF
DOCUMENT_COMMIT_RESOLUTION = git log -1 --format=%H -- online_trader.md

RECONCILED_AT_UTC = 2026-07-29T00:39:46Z
RECONCILED_BY_TASK = TRADERS_ML_READONLY_API_STABILITY_OBSERVER_RUNTIME_UNKNOWN_DIAGNOSTIC_01
FILES_CHANGED = online_trader.md

REMOTE_PRODUCTION_BASE_AT_RECONCILIATION = 74db6518d2a144fcf8814323c55e4224a71700e9
PUSH_STATE_AT_RECONCILIATION = NOT_PUSHED
STATUS_CONFIDENCE = PROVEN_OBSERVER_CAPTURE_REMEDIATION_WITH_HISTORICAL_PAYLOAD_LIMITATION

# Состояние проекта traders-ml

## Текущая стадия

```text
ROOT_BRANCH = fix/traders-ml-readonly-api-stability-observer-tooling-01
API_ROOT_STATUS = DEPLOYED_LOCALHOST_READONLY
API_RUNTIME_STATUS = DEPLOYED_HEALTHY
CURRENT_STAGE = READONLY_API_POST_ANALYSIS_REMEDIATION_STABILITY_OBSERVATION_02_PENDING
CURRENT_BLOCKER = FRESH_SUCCESSFUL_75_MINUTE_RETRY_REQUIRED_AFTER_HISTORICAL_FAILED_WINDOW
```

Root project-state commit `f5b48e061f99afea81f3fd39b296acded477f8b6`
был предыдущим доказанным состоянием. Новый project-state commit
`4dcb6a3a228017408fc8e6caf554908e6b67289c` дополнительно содержит:

- backward-compatible boundary-aware market-data health contract;
- operational/readiness/reason/deadline fields в atomic JSON health report;
- direct prod-smoke и observation consumer mapping;
- deterministic boundary, clock-skew, aggregation, serialization и incident
  regression tests.

Ранее доказанное состояние остаётся включённым как ancestor:

```text
Readonly Server API v1 = DEPLOYED_LOCALHOST_READONLY
API canary configuration = PREPARED_DISABLED_BY_DEFAULT
LIVE = DISABLED
```

## Market-data boundary-aware health

```text
MARKET_DATA_BOUNDARY_AWARE_HEALTH = DEPLOYED_AND_VERIFIED
PUBLIC_HEALTH_ENUM_CHANGED = NO
BOUNDARY_WITHIN_GRACE = OPERATIONAL_READY
WITHIN_GRACE_PUBLIC_STATUS = OK
WITHIN_GRACE_REASON_CODE = BOUNDARY_WITHIN_GRACE
WITHIN_GRACE_ACCEPTANCE_BLOCKING = NO
RECOVERING = DEADLINE_EXCEEDED_OR_REAL_RECOVERY
DEGRADED_FAILED = REAL_HEALTH_FAILURE
CLOCK_SKEW_HANDLING = VERIFIED
NORMAL_BOUNDARY_FALSE_BLOCKERS = 0
REPORT_SCHEMA = MARKET_DATA_HEALTH/2.0_ADDITIVE
OLD_REPORT_READER_COMPATIBILITY = PASS
NEW_REPORT_READER_COMPATIBILITY = PASS
INCIDENT_REGRESSION = PASS
DETERMINISTIC_REPEAT_RUNS = 3_PASS
IMPLEMENTATION_MARKET_DATA_FOCUSED_TESTS = 192 passed, 1 skipped
DEPLOYMENT_REVALIDATION_MARKET_DATA_FOCUSED_TESTS = 134 passed, 1 skipped
DEPLOYMENT_REVALIDATION_SAFE_REGRESSION = 682 passed, 2 skipped
LIVE_BOUNDARIES_VERIFIED = 1m,5m,15m,1h
NORMAL_BOUNDARY_FALSE_RECOVERING = 0
NORMAL_BOUNDARY_ACCEPTANCE_BLOCKERS = 0
DEADLINE_GAP_NO_PROGRESS_ERROR_BLOCKING = VERIFIED
STABILITY_OBSERVATION = PASS_30_MINUTES
PRODUCTION_DEPLOYMENT = DEPLOYED_STABLE
SETUPS_FIX_BRANCH = RETAINED_UNCHANGED
```

## Market-data image security and Linux dependency contract

```text
MARKET_DATA_IMAGE_CONTENT_SECURITY = PASS
CREDENTIAL_BEARING_URI_LITERALS = 0
PRODUCTION_SECRETS = RUNTIME_INJECTED_ONLY
PRODUCTION_MISSING_SECRET = FAIL_CLOSED
CANONICAL_RUNTIME_LOCK = requirements/api-runtime.lock.txt
CANONICAL_LOCK_SCOPE = ALL_PLATFORM_WITH_PEP_508_MARKERS
CANONICAL_LINUX_RUNTIME_LOCK = VERIFIED
LOCKED_ALL_PLATFORM_PACKAGE_COUNT = 24
LOCKED_LINUX_EFFECTIVE_PACKAGE_COUNT = 22
ACTUAL_LINUX_RUNTIME_PACKAGE_COUNT = 22
COLORAMA_LINUX_DECISION = WINDOWS_ONLY_MARKER; ABSENT_ON_LINUX
TZDATA_LINUX_DECISION = WINDOWS_ONLY_PYTHON_MARKER; SYSTEM_TZDATA_2026b-0+deb13u1
IMAGE_DEPENDENCY_MISSING = 0
IMAGE_DEPENDENCY_UNEXPECTED = 0
IMAGE_DEPENDENCY_VERSION_MISMATCH = 0
IMAGE_SECURITY_SMOKE = PASS
IMAGE_FUNCTIONAL_SMOKE = PASS
IMAGE_REPRODUCIBILITY = PACKAGE_SBOM_CONTENT_MANIFEST_PASS
ACCEPTED_LOCAL_IMAGE = traders-market-data:4e3c2d0f-boundary-health-secure-lock-01
DEPLOYED_IMAGE = traders-market-data:4e3c2d0f-boundary-health-secure-lock-01
DEPLOYED_IMAGE_ID = sha256:0482cbd01d9ee51fbc391e472b9bfe4980f00c6559c7387207dd33cc33062800
PRODUCTION_DEPLOYMENT = DEPLOYED_STABLE
BOUNDARY_AWARE_HEALTH = DEPLOYED_AND_VERIFIED
SETUPS_FIX_BRANCH = RETAINED_UNCHANGED
```

Two credential-bearing defaults were removed from `app/config/settings.py`.
Production database configuration is now required from external runtime
configuration and fails closed when absent. The production Docker target uses
the hash-locked runtime file and evaluates explicit Windows-only markers for
`colorama` and Python `tzdata` on the exact Linux target. Two clean builds
matched package inventory, normalized SPDX SBOM, and filesystem content
manifests. The controlled deployment retry replaced only `market-data-sync`
with the accepted immutable image. PostgreSQL and orchestrator container IDs,
restart counts, schema, Alembic version, networks, volumes, and runtime
credentials remained unchanged.

Exact unchanged grace contract:

```text
1m = 10 seconds
5m = 15 seconds
15m = 20 seconds
1h = 60 seconds
4h = 90 seconds
1d = 120 seconds
```

Нормальная новая boundary до inclusive deadline публикуется как
`overall_status=OK`, `reason_code=BOUNDARY_WITHIN_GRACE`,
`operational=true`, `ready=true`, `acceptance_blocking=false`. После deadline
прогрессирующая recovery остаётся `RECOVERING`; stalled runtime, real gap и
active error остаются blocking. Production `market-data-sync` использует
принятую immutable image; один controlled replacement прошёл startup, live
boundary и stability acceptance. PostgreSQL schema/data не изменялись.

## Readonly Server API

```text
FASTAPI = 0.116.1
ASGI_SERVER = uvicorn 0.51.0
API_RUNTIME_ENTRYPOINT = IMPLEMENTED
API_STATUS = DEPLOYED_LOCALHOST_READONLY
RUNTIME_FACTORY = app.server_api.runtime:create_runtime_app
EXECUTABLE_ENTRYPOINT = traders-readonly-api
MODULE_ENTRYPOINT = python -m app.server_api.runtime
DOCKER_API_TARGET = readonly-api, DEPLOYED
EPHEMERAL_READONLY_DB_SMOKE = PASS
CANARY_CONFIGURATION = PREPARED_DISABLED_BY_DEFAULT
CANARY_PROFILE = readonly-api-canary
CANARY_DRY_RUN = PASS
BUILD_CONTRACT = REPRODUCIBLE
TWO_BUILD_RUNTIME_CONTRACT_MATCH = YES
MATERIAL_BUILD_DRIFT = 0
ROLLBACK_PLAN = READY
API_ROUTE_COUNT = 9
API_GET_ONLY_ROUTES = 9
API_WRITE_ROUTES = 0
SELECT_ONLY_APPLICATION_ADAPTER = YES
DB_MIGRATIONS_ADDED = 0
PRODUCTION_PERSISTENT_MUTATIONS = 0
PRODUCTION_DB_ROLE_MUTATION = TEMPORARY_CREATED_VERIFIED_REMOVED
PRODUCTION_SCHEMA_MUTATIONS = 0
MANUAL_PRODUCTION_DATA_MUTATIONS = 0
PERSISTENT_SERVICE = traders-readonly-api-readonly-api-1
PERSISTENT_SERVICE_BIND = 127.0.0.1:8765
PERSISTENT_SERVICE_HEALTH = HEALTHY
PERSISTENT_SERVICE_RESTARTS = 0
PERSISTENT_SERVICE_CONTAINER_ID = e1ac8811b07685960738c3fac816b3d15656abee3a5ea90544d1b7d98bc5199c
PERSISTENT_SERVICE_IMAGE_ID = sha256:3f6312806467ee7ffaac6fe372769a0470b9eb3622d25f73b9d8148df25d4917
PRODUCTION_READONLY_ROLE = traders_readonly_api
PRODUCTION_READONLY_ROLE_CONTRACT = PASS
PRODUCTION_HTTP_ACCEPTANCE = PASS
CONTROLLED_HTTP_LOAD = 90/90 HTTP 200
UNEXPECTED_5XX = 0
CLIENT_PROVIDER = PRODUCTION_READONLY_HTTP
CLIENT_CONNECTION = CONNECTED
PRODUCTION_CANARY_STARTED = NO
SOAK_STARTED = NO
```

### Boundary-aware Readonly API health remediation

```text
BOUNDARY_HEALTH_ROOT_CAUSE = HEALTH_ENDPOINT_BOUNDARY_GRACE_MAPPING_DEFECT
BOUNDARY_HEALTH_POLICY = app.server_api.health_policy:evaluate_boundary_health
HEALTH_POLICY_PRECEDENCE = REAL_BLOCKING_EVIDENCE > AUTHORITATIVE_BOUNDARY_STATE > ORCHESTRATOR_WORKFLOW_LABEL > SAFE_UNKNOWN
API_HEALTH_SCHEMA = ADDITIVE_BACKWARD_COMPATIBLE
VALID_CURRENT = HTTP_200_OK_CURRENT_OPERATIONAL_READY_NON_BLOCKING
VALID_WITHIN_GRACE = HTTP_200_OK_WITHIN_GRACE_BOUNDARY_WITHIN_GRACE_OPERATIONAL_READY_NON_BLOCKING
EXPIRED_GRACE = HTTP_200_DEGRADED_DEADLINE_EXPIRED_BLOCKING
REAL_GAP_NO_PROGRESS_ACTIVE_ERROR = BLOCKING
OBSERVER_PREDICATE_CHANGED = NO
DOCKER_HEALTHCHECK_CHANGED = NO
CLIENT_CODE_CHANGED = NO
PRODUCTION_BOUNDARY_OBSERVED = 1h_2026-07-28T05:00:00Z
BOUNDARY_OBSERVATION_WINDOW = 2026-07-28T04:58:30Z/2026-07-28T05:02:30Z
BOUNDARY_OBSERVATION_SAMPLES = 49
WITHIN_GRACE_SAMPLES = 5_PASS
EXPIRED_GRACE_SAMPLES = 3_BLOCKING_AS_DESIGNED
POST_SYNC = OK_CURRENT
ROOT_CAUSE_REMEDIATED = YES
PRODUCTION_ACCEPTANCE = PASS
POST_REMEDIATION_STABILITY_OBSERVATION = FAILED_RUNTIME_UNKNOWN_UNCHANGED
PAPER_FOUNDATION_UNBLOCKED = NO
```

The Readonly API now reconstructs dependency health from persisted per-timeframe
boundary availability, UTC boundary timestamps, grace deadlines, health states,
and blocking reasons. A transient orchestrator workflow label cannot override
authoritative `WITHIN_GRACE` or `CURRENT` state and cannot mask expired grace,
gap, no-progress, active-error, database, or internal failures. The natural 1h
production boundary showed five non-blocking grace samples, three expected
blocking post-deadline samples before synchronization, and a return to
`OK/CURRENT`. This remediation acceptance is not the required new 75-minute
stability PASS.

### Latest available analysis result remediation

```text
ANALYSIS_AVAILABILITY_ROOT_CAUSE = ANALYSIS_LATEST_RUN_RESULT_ATOMICITY_RACE
ANALYSIS_QUERY_CONTRACT = LATEST_AVAILABLE_VALID_ANALYSIS_RESULT
ELIGIBILITY = ANALYZED; IDENTITY_MATCH; REQUIRED_SNAPSHOT_FIELDS; NO_FUTURE_BARS; NOT_DEGRADED; ENOUGH_DATA
DOWNSTREAM_COMPLETION_REQUIRED = NO
ORDERING = RUN_BOUNDARY_DESC; RESULT_CREATED_AT_DESC; RESULT_ID_DESC
BOUNDED_SQL = CORRELATED_ELIGIBLE_RESULT_LIMIT_1; OUTER_LIMIT_1
IMPLEMENTATION_COMMIT = 80c46f3f59aaade111b81af45b5eca5094ca38d8
API_SCHEMA_CHANGED = NO
CLIENT_CODE_CHANGED = NO
DETERMINISTIC_REGRESSION = 12_PASSED
SAFE_SERVER_REGRESSION = 774_PASSED; 2_SKIPPED
CLIENT_REGRESSION = 105_PASSED; 63_SUBTESTS_PASSED
PRODUCTION_IMAGE_ID = sha256:3f6312806467ee7ffaac6fe372769a0470b9eb3622d25f73b9d8148df25d4917
PRODUCTION_CONTAINER_ID = e1ac8811b07685960738c3fac816b3d15656abee3a5ea90544d1b7d98bc5199c
HTTP_ROUTE_SMOKE = 9_GET_PASS; 0_WRITE
NATURAL_BOUNDARY = 2026-07-28T16:00:00Z
BOUNDARY_ANALYSIS_CONTINUITY = 110/110_HTTP_200; OLD_TO_NEW; 0_4XX; 0_5XX; 0_TIMEOUT
NATURAL_INCOMPLETE_RUN_WINDOW_OBSERVED = YES
OLD_VALID_RESULT_SERVED_DURING_INCOMPLETE_RUN = YES
NEW_VALID_RESULT_BECAME_VISIBLE = YES
RESULT_TIMESTAMP_REGRESSION = NO
HEALTH_CURRENT_PASS = YES
HEALTH_WITHIN_GRACE_PASS = YES
HEALTH_FALSE_DEGRADED = 0
HEALTH_REAL_BLOCKER_MASKED = NO
PRODUCTION_ACCEPTANCE = PASS
POST_ANALYSIS_REMEDIATION_75_MINUTE_STABILITY = FAILED_RUNTIME_UNKNOWN_UNCHANGED
PAPER_FOUNDATION_UNBLOCKED = NO
```

The analysis route now joins each ordered run only to a bounded correlated
eligible result. A newer run without a result, or with an invalid or unrelated
payload, cannot hide the last valid analysis. The natural 1h boundary served
the old result for 43 post-boundary samples and then switched directly to the
new result without a 404, 5xx, timeout, or timestamp regression. This is route
production acceptance, not the separate uninterrupted 75-minute stability
gate.

### Tracked observer runtime UNKNOWN diagnostic

```text
DIAGNOSTIC_TASK = TRADERS_ML_READONLY_API_STABILITY_OBSERVER_RUNTIME_UNKNOWN_DIAGNOSTIC_01
DIAGNOSTIC_RESULT = PASS_WITH_LIMITATIONS_CAPTURE_REMEDIATED
IMPLEMENTATION_COMMIT = d3a7f6b4b188349a68396b2950a55518c93e270b
ROOT_CAUSE_CODE = SAFE_CAPTURE_DROPPED_REQUIRED_CONTEXT
ROOT_CAUSE_PROVEN = YES
HISTORICAL_UNKNOWN_SAMPLE_FOUND = YES_AGGREGATE_ONLY
HISTORICAL_FULL_PAYLOAD_AVAILABLE = NO
HISTORICAL_SAFE_STRUCTURE_AVAILABLE = NO
EXACT_HISTORICAL_RUNTIME_STATE_PROVABLE = NO
HISTORICAL_OBSERVATION_VERDICT = FAILED_UNCHANGED
CLASSIFIER_CONTRACT = STRICT_MODEL_ALIGNED_FAIL_CLOSED
SAFE_UNKNOWN_CAPTURE = SEQUENCE_PHASE_UTC_HTTP_STRUCTURE_REASON_BRANCH
SAFE_UNKNOWN_RENDER_LIMIT = 20
FULL_PAYLOAD_RETAINED = NO
FULL_PAYLOAD_HASH_RETAINED = NO
AMBIGUOUS_INPUT_MAPPED_TO_CURRENT = NO
MINIMAL_SECRET_FREE_FIXTURE = YES_NOT_HISTORICAL_PAYLOAD
NEW_DIAGNOSTIC_TESTS = 26_PASSED
OBSERVER_SCHEDULER_TK_REGRESSION = 65_PASSED
SCANNER_SECURITY_TESTS = 37_PASSED
CREDENTIAL_CONTROL_TESTS = 31_PASSED
ANALYSIS_REMEDIATION_TESTS = 44_PASSED
SAFE_RELEVANT_SERVER_REGRESSION = 839_PASSED; 2_SKIPPED
FORBIDDEN_CANARY_TESTS = 13_NOT_RUN
CLIENT_PARSER_PROVIDER_TESTS = 37_PASSED; 19_SUBTESTS_PASSED
PRODUCTION_DEPLOYMENT = NOT_RUN
NEW_75_MINUTE_OBSERVATION = NOT_RUN
PAPER_FOUNDATION_UNBLOCKED = NO
```

The historical source retained only the aggregate
`RUNTIME_UNKNOWN:/api/v1/health`; it did not retain sequence, phase, UTC, exact
HTTP status, content type, response length, safe field structure, reason, or
classifier branch. The diagnostic therefore does not infer the underlying
historical runtime state or reclassify that failed window. The tracked observer
now validates the exact FastAPI/Pydantic health envelope, reports stable
fail-closed reason and branch IDs, and retains only bounded allowlisted
structure with a paths/types-only digest. A fresh uninterrupted 75-minute
observation remains required.

Library factory `create_app()` остаётся inert. Новый runtime factory явно
создаёт один SQLAlchemy engine/session factory и передаёт существующий
SELECT-only adapter. Import и `--help` не открывают DB connection или socket.
Startup проверяет PostgreSQL read-only mode, а lifespan shutdown освобождает
engine. Этот runtime contract реализован, image-smoke подтверждён и теперь
развёрнут как постоянный hardened service на `127.0.0.1:8765`. Все девять GET
routes прошли production HTTP acceptance; write routes отсутствуют.

Подтверждённые integration gates:

```text
LOCK_ROOT_COMPATIBILITY = PASS
LOCK_HASHES_COMPLETE = YES
ROOT_DEPENDENCY_COVERAGE = COMPLETE
VERIFY_ENV_1_INSTALL = PASS
VERIFY_ENV_2_INSTALL = PASS
NORMALIZED_FREEZE_MATCH = YES
DEPENDENCY_CONTRACT_TESTS = 2 passed
RUNTIME_ENTRYPOINT_TESTS = 20 passed
CANARY_CONFIGURATION_TESTS = 13 passed
API_FOCUSED = 59 passed
SAFE_REGRESSION = 624 passed, 1 skipped, 1 deselected
LINUX_PRODUCTION_TARGET_SMOKE = PASS
LINUX_TARGET = python:3.11-slim, x86_64
```

Это integration acceptance, а не deployment или production acceptance.

### Setups endpoint production read-only acceptance

```text
SERVER_READONLY_API_SETUPS_ENDPOINT_RELIABILITY = PRODUCTION_ACCEPTED_AND_ROOT_INTEGRATED
SETUPS_IMPLEMENTATION_SOURCE_COMMIT = e24073aee5f7e31f6a13c57e5ed3c7ad81cbc3ee
SETUPS_ACCEPTANCE_REPLAY_COMMIT = 3407cd712b65073f6ff662196775b1fd5256e417
PRODUCTION_ACCEPTANCE = PASS
TEMP_READONLY_ROLE = CREATED_VERIFIED_REMOVED
EPHEMERAL_API = STARTED_VERIFIED_REMOVED
GET_ROUTES = 9
WRITE_ROUTES = 0
UNEXPECTED_5XX = 0
LIST_QUERY_BOUNDED = YES
DETAIL_QUERY_BOUNDED = YES
LARGE_JSON_MATERIALIZATION = NO
PRODUCTION_SCHEMA_MUTATIONS = 0
MANUAL_PRODUCTION_DATA_MUTATIONS = 0
MARKET_DATA = DEPLOYED_STABLE_UNCHANGED
POSTGRESQL = HEALTHY_UNCHANGED
ORCHESTRATOR = HEALTHY_UNCHANGED
CLIENT_CONNECTION = PRODUCTION_READONLY_HTTP_CONNECTED
```

Implementation commit был replayed без конфликтов на current root. Pinned
source gates прошли: setups `18 passed` в трёх deterministic runs, server API
`64 passed`, runtime/dependency gates `46 passed`, safe regression
`687 passed, 2 deselected`. Temporary PostgreSQL и hardened local container
acceptance прошли до production boundary. Production acceptance использовала
роль без write privileges и один loopback-only container: все 9 GET routes
прошли, bounded 60-second load дал `240/240` HTTP 200 и zero unexpected 5xx.
После cleanup одиннадцать health snapshots за 10 минут сохранили 18/18 streams,
PostgreSQL и orchestrator healthy, а service IDs и restart counts неизменными.
Первоначальная endpoint acceptance была отдельна от deployment. Текущая
задача дополнительно завершила persistent localhost deployment и client
connection; canary и 72-hour soak не запускались.

### Persistent protected secret binding

```text
PERSISTENT_PROTECTED_SECRET_BINDING = PROVISIONED_ROTATED_PROTECTED
PERSISTENT_SECRET_BINDING_PATH = D:\disk_E\game_projects\traders\traders-ml\.env.production.local
PERSISTENT_SECRET_BINDING_GIT_TRACKED = NO
PERSISTENT_SECRET_BINDING_GIT_IGNORED = YES
PERSISTENT_SECRET_BINDING_DOCKER_CONTEXT = EXCLUDED
PERSISTENT_SECRET_BINDING_ACL = RESTRICTED_CURRENT_USER_SYSTEM_ADMINISTRATORS
PERSISTENT_SECRET_BINDING_ACL_BROAD_PRINCIPALS = 0
READONLY_API_DATABASE_URI_CANONICAL_KEY = TRADERS_READONLY_API_DATABASE_URL
READONLY_API_DATABASE_URI_PROVISIONED = YES
READONLY_API_BIND_HOST_CANONICAL_KEY = TRADERS_READONLY_API_HOST
READONLY_API_BIND_HOST = 127.0.0.1
READONLY_API_PORT = 8765
PERSISTENT_BINDING_FOCUSED_TESTS = 11 passed
PERSISTENT_BINDING_FOUNDATION_VERIFIER = PASS
PERSISTENT_BINDING_PROVISIONED_VERIFIER = PASS
PRODUCTION_READONLY_API = DEPLOYED_LOCALHOST_READONLY
CLIENT_CONNECTION = PRODUCTION_READONLY_HTTP_CONNECTED
```

Permanent host-local binding provisioned canonical credential-bearing runtime
value без его вывода. Он остаётся исключённым из Git и Docker build context,
защищён exact Windows ACL и прошёл provisioned verifier. Client не получает DB
credential; он хранит только localhost HTTP base URL и provider mode.

### Readonly API credential rotation and safe rebind

```text
ROTATION_TASK = TRADERS-ML-READONLY-API-CREDENTIAL-INVALIDATION-VERIFIER-AND-ROTATION-RETRY-03
SOURCE_BLOCKER = CONTROL_PROCESS_SUCCESS_EXIT_MISCLASSIFIED_TRIGGERED_ROLLBACK
CREDENTIAL_INVALIDATION_VERIFIER = PROVEN_AND_INTEGRATED
VERIFIER_PRIMARY_AUTHORITY = POSTGRESQL_SQLSTATE_AND_ERROR_RESPONSE_FIELD_C
VERIFIER_STRING_MATCH_PRIMARY = NO
CONTROL_PROCESS_EXIT_SEMANTICS = REMEDIATED
SYSTEM_EXIT_ZERO_CLASSIFICATION = SUCCESS
SYSTEM_EXIT_ZERO_ROLLBACK_CALLS = 0
CONTROL_PROCESS_FINAL_EXIT = 0
CONTROL_PROCESS_FINAL_CLASSIFICATION = SUCCESS
ROLLBACK_TRIGGERED_AFTER_SUCCESS = NO
CREDENTIAL_ROTATION = COMPLETED
SAFE_REBIND = COMPLETED
OLD_CREDENTIAL_NEW_CONNECTION = DENIED
OLD_CREDENTIAL_SQLSTATE = 28P01
OLD_CREDENTIAL_CONDITION = invalid_password
OLD_CREDENTIAL_NORMALIZED_CLASS = AUTHENTICATION_FAILED
OLD_CREDENTIAL_INVALIDATION = PROVEN
NEW_CREDENTIAL_DIRECT_CONNECTION = PASS
BINDING_VERIFIER = PASS
BINDING_ACL = RESTRICTED_UNCHANGED
BINDING_GIT_TRACKED = NO
BINDING_GIT_IGNORED = YES
BINDING_DOCKER_CONTEXT = EXCLUDED
READONLY_API_CONTAINER_REPLACED = YES
READONLY_API_CONTAINER_ID = abb61719d07a125aff752aba236fec80f18b4b33d6a7a565306f4a3b2eb42fbe
READONLY_API_IMAGE_ID = sha256:e9695a802045fecf64a025481029612a8a578e5d206cc657bab7cb6db8df3c6b
READONLY_API_IMAGE_UNCHANGED = YES
READONLY_API_HEALTH = HEALTHY
READONLY_API_RESTARTS = 0
READONLY_API_BIND = 127.0.0.1:8765
ROLE_AUTHORIZATION_UNCHANGED = YES
ROLE_SELECT_GRANTS = 3
ROLE_NONSELECT_GRANTS = 0
HTTP_ROUTE_SMOKE = 9_GET_PASS
EXPECTED_MISSING_RESOURCE_404 = PASS
UNEXPECTED_4XX = 0
UNEXPECTED_5XX = 0
TIMEOUTS = 0
SAFE_DOCKER_INSPECTION = ALLOWLIST_ONLY
SECRET_VALUE_OUTPUT = NO
ANALYSIS_REMEDIATION = COMPLETED_PRODUCTION_ACCEPTED
POST_REMEDIATION_STABILITY_OBSERVATION = NOT_RUN
PAPER_FOUNDATION_UNBLOCKED = NO
```

The previously restored compromised credential is no longer accepted by a new
PostgreSQL connection and returns SQLSTATE `28P01`. A fresh credential was
generated in memory, applied only to `traders_readonly_api`, atomically stored
through the protected binding, and loaded by one targeted Readonly API
recreation. The tracked controller now treats normal return, return code zero,
and `SystemExit(0)` as success; the completed production run exited zero with
zero rollback calls. Role attributes and three-table SELECT-only authorization
are unchanged. No credential value, URI, password verifier, environment dump,
or full Docker inspection is retained in Git or task evidence. This restores
the secret boundary. The separately authorized analysis remediation is now
production accepted, but the follow-on 75-minute stability gate remains open.

### Security scanner protected-binding scope remediation

```text
SCANNER_REMEDIATION_TASK = TRADERS-ML-SECURITY-SCANNER-PROTECTED-BINDING-SCOPE-REMEDIATION-01
SCANNER_SCOPE_REMEDIATED = YES
SCANNER_DISCOVERY = GIT_LS_FILES_TRACKED_AND_EXPLICIT_SAFE_ALLOWLIST
REPOSITORY_RECURSIVE_WALK = PROHIBITED
PROTECTED_BINDING_EXCLUDED_BEFORE_READ = YES
DENY_OVERRIDES_EXPLICIT_ALLOWLIST = YES
ORIGINAL_CANONICAL_RESOLVED_PATH_POLICY = VERIFIED
SYMLINK_REPARSE_TO_PROTECTED_BINDING = DENIED
SECRET_DERIVED_FINGERPRINTS = PROHIBITED
MATCHED_SECRET_OUTPUT = PROHIBITED
SAFE_FINDING_METADATA_ONLY = VERIFIED
REAL_PROTECTED_BINDING_OPEN_COUNT = 0
REAL_PROTECTED_BINDING_READ_COUNT = 0
REAL_PROTECTED_BINDING_HASH_COUNT = 0
REAL_PROTECTED_BINDING_FINGERPRINT_COUNT = 0
SCANNER_NEW_TESTS = 19 passed, 3 deterministic runs
SCANNER_EXISTING_TESTS = 7 passed
SAFE_SECURITY_REGRESSION = 23 passed
CURRENT_READONLY_CREDENTIAL_SECURITY = ROTATED_PROTECTED
CREDENTIAL_ROTATION_REQUIRED = NO
ANALYSIS_CANDIDATE = PRESERVED_LOCAL_FORENSIC_COMMIT_NOT_DEPLOYED
ANALYSIS_ROUTE_PRODUCTION_DEFECT = REMEDIATED_PRODUCTION_ACCEPTED
PAPER_FOUNDATION_UNBLOCKED = NO
PRODUCTION_MUTATIONS = 0
DEPLOYMENT = NOT_RUN
STABILITY_OBSERVATION = NOT_RUN
```

The scanner now inventories tracked/indexed paths with `git ls-files -z` and
applies original, normalized, repository-containment and resolved-path deny
checks before any file read. Findings contain only rule, normalized path, line,
category, severity and count; matched values and secret-derived hashes or
fingerprints are forbidden. The interrupted analysis candidate remains only in
the preserved local forensic branch and is not approved for integration.

The scanner remains restricted to tracked inputs and excludes the protected
binding before read. The separately authorized RETRY-03 task has now restored
the credential boundary with a new protected credential and exact old-
credential SQLSTATE proof. The preserved forensic candidate remains undeployed
and unapproved; the accepted remediation was reapplied and corrected on a clean
branch from the authoritative baseline.

## Production boundary

В рамках этой задачи:

```text
API_DEPLOYED = YES_LOCALHOST_ONLY
MARKET_DATA_DEPLOYED = YES
MARKET_DATA_RUNTIME_STATUS = RUNNING_HEALTHY
PRODUCTION_RUNTIME_CHANGED = READONLY_API_ONLY
POSTGRESQL_CHANGED = NO
ALEMBIC_RUN = NO
PRODUCTION_COMPOSE_APPLIED = READONLY_API_ONLY
SERVICES_RESTARTED = READONLY_API_TARGETED_RECREATE_ONLY
MARKET_DATA_RESTARTS_BY_TASK = 0
POSTGRESQL_RESTARTS_BY_TASK = 0
ORCHESTRATOR_RESTARTS_BY_TASK = 0
UNRELATED_SERVICE_MUTATIONS = 0
PRODUCTION_CANARY_STARTED = NO
NEW_SOAK_STARTED = NO
PERSISTENT_READONLY_ROLE_REMAINS = YES
EPHEMERAL_API_REMAINS = NO
PERSISTENT_API_PORT_8765_ACTIVE = YES
PRODUCTION_DB_ROLE_MUTATIONS = 0
PRODUCTION_SCHEMA_MUTATIONS = 0
MANUAL_PRODUCTION_DATA_MUTATIONS = 0
CLIENT_REPOSITORY_MUTATIONS = 0
PRIVATE_BINANCE_API_USED = NO
LIVE_ORDERS = 0
PUSHED = NO
```

Market-data boundary-aware health deployment остаётся стабильным. Постоянная
role `traders_readonly_api` создана после fresh health gate, получила SELECT
только на три необходимые таблицы и прошла explicit write denial. Persistent
Readonly API работает в отдельном hardened container; PostgreSQL, market-data
и orchestrator не перезапускались. Schema structure, Alembic version,
production data и существующие soak artifacts не изменялись.

## Готовность основных контуров

| Контур | Готовность | Доказанное состояние |
|---|---:|---|
| Online analytics/paper pipeline | ≈82% | Интегрирован ранее; эта задача runtime не меняла |
| Production reliability/acceptance | ≈80% | Historical 75-minute observation remains FAILED on one context-poor UNKNOWN; observer capture is remediated with limitations, while observation 02 and the 72-hour soak remain open |
| Readonly Server API | 90% | Latest-available analysis remains production accepted; observer-only classifier/capture remediation is tested but not a server deployment |
| Market-data health contract | Deployed and verified | Accepted immutable image passed live 1m/5m/15m/1h boundaries, blocking probes, consumer compatibility, candle integrity, and 30-minute stability observation |
| Полный автономный LIVE-бот | ≈58% engineering / 0% operational | `LIVE = DISABLED` |

Проценты отражают implementation, integration, tests, deployment и acceptance,
а не количество файлов или coverage.

## Следующий этап

```text
RECOMMENDED_NEXT_TASK =
TRADERS_ML_READONLY_API_POST_ANALYSIS_REMEDIATION_STABILITY_OBSERVATION_02_WITH_DIAGNOSTIC_OBSERVER
NEXT_TASK_REQUIRES_SEPARATE_OPERATOR_AUTHORIZATION = YES
```

Scanner scope remediation, credential rotation/safe-rebind and the clean
analysis latest-available-result remediation are completed with PASS. The
historical full observation remains failed unchanged. The observer's bounded
UNKNOWN capture and strict classifier are remediated with historical-payload
limitations, but no new 75-minute observation was started. Paper foundation
and the 72-hour soak remain blocked. Market-data health stays
`DEPLOYED_STABLE`; LIVE stays disabled.

## Правила актуализации

- Документ является post-task snapshot, а не планом незавершённой задачи.
- `STATUS_AS_OF_COMMIT` описывает project state и не является собственным SHA
  документа.
- Фактическая revision документа определяется командой
  `git log -1 --format=%H -- online_trader.md`.
- Integration не считать deployment.
- Deployment/canary не считать production acceptance или soak.
- Local commit не считать remote state.
- LIVE остаётся operationally disabled до отдельного controlled rollout.
