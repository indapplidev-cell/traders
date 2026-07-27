DOCUMENT = online_trader.md
DOCUMENT_ROLE = SINGLE_SOURCE_OF_TRUTH_FOR_PROJECT_STATUS
DOCUMENT_SNAPSHOT_TYPE = POST_TASK_PROVEN_STATE
PROJECT = traders-ml

STATUS_AS_OF_COMMIT = 4e3c2d0fdb5222576169ac2655847715238df3c8
DOCUMENT_REVISION = SELF
DOCUMENT_COMMIT_RESOLUTION = git log -1 --format=%H -- online_trader.md

RECONCILED_AT_UTC = 2026-07-27T16:23:25Z
RECONCILED_BY_TASK = TRADERS-ML-MARKET-DATA-BOUNDARY-AWARE-HEALTH-CONTROLLED-DEPLOYMENT-RETRY-01
FILES_CHANGED = online_trader.md

REMOTE_PRODUCTION_BASE_AT_RECONCILIATION = 74db6518d2a144fcf8814323c55e4224a71700e9
PUSH_STATE_AT_RECONCILIATION = NOT_PUSHED
STATUS_CONFIDENCE = PROVEN_PRODUCTION_BOUNDARY_AWARE_MARKET_DATA_DEPLOYED_STABLE

# Состояние проекта traders-ml

## Текущая стадия

```text
ROOT_BRANCH = feature/engine-platform
API_ROOT_STATUS = PREPARED_NOT_DEPLOYED
API_RUNTIME_STATUS = PREPARED_NOT_DEPLOYED
CURRENT_STAGE = MARKET_DATA_BOUNDARY_AWARE_HEALTH_DEPLOYED_STABLE
CURRENT_BLOCKER = NONE
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
Readonly Server API v1 = PREPARED_NOT_DEPLOYED
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
API_STATUS = PREPARED_NOT_DEPLOYED
RUNTIME_FACTORY = app.server_api.runtime:create_runtime_app
EXECUTABLE_ENTRYPOINT = traders-readonly-api
MODULE_ENTRYPOINT = python -m app.server_api.runtime
DOCKER_API_TARGET = readonly-api, IMPLEMENTED_NOT_DEPLOYED
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
PRODUCTION_MUTATIONS = 0
PRODUCTION_DB_MUTATIONS = 0
PRODUCTION_CANARY_STARTED = NO
SOAK_STARTED = NO
```

Library factory `create_app()` остаётся inert. Новый runtime factory явно
создаёт один SQLAlchemy engine/session factory и передаёт существующий
SELECT-only adapter. Import и `--help` не открывают DB connection или socket.
Startup проверяет PostgreSQL read-only mode, а lifespan shutdown освобождает
engine. Этот runtime contract реализован и image-smoke подтверждён, но не
deployed и не является production acceptance.

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

## Production boundary

В рамках этой задачи:

```text
API_DEPLOYED = NO
MARKET_DATA_DEPLOYED = YES
MARKET_DATA_DEPLOYMENT_REPLACEMENTS = 1
MARKET_DATA_RUNTIME_STATUS = RUNNING_HEALTHY
PRODUCTION_RUNTIME_CHANGED = MARKET_DATA_ONLY
POSTGRESQL_CHANGED = NO
ALEMBIC_RUN = NO
PRODUCTION_COMPOSE_APPLIED = MARKET_DATA_ONLY
SERVICES_RESTARTED = market-data-sync only
POSTGRESQL_RESTARTS_BY_TASK = 0
ORCHESTRATOR_RESTARTS_BY_TASK = 0
UNRELATED_SERVICE_MUTATIONS = 0
PRODUCTION_CANARY_STARTED = NO
NEW_SOAK_STARTED = NO
PRIVATE_BINANCE_API_USED = NO
LIVE_ORDERS = 0
PUSHED = NO
```

Market-data boundary-aware health deployment принят после live `1m`, `5m`,
`15m`, `1h` boundaries и 30-минутного stability observation. Readonly API
canary и soak не запускались. PostgreSQL, orchestrator и существующие soak
artifacts не изменялись. Market-data deployment не повышает API deployment
status.

## Готовность основных контуров

| Контур | Готовность | Доказанное состояние |
|---|---:|---|
| Online analytics/paper pipeline | ≈82% | Интегрирован ранее; эта задача runtime не меняла |
| Production reliability/acceptance | ≈70% | API integration не является production acceptance |
| Readonly Server API | 75% | Reproducible build contract and disabled-by-default hardened canary configuration passed a task-owned ephemeral DB dry-run; production canary not started |
| Market-data health contract | Deployed and verified | Accepted immutable image passed live 1m/5m/15m/1h boundaries, blocking probes, consumer compatibility, candle integrity, and 30-minute stability observation |
| Полный автономный LIVE-бот | ≈58% engineering / 0% operational | `LIVE = DISABLED` |

Проценты отражают implementation, integration, tests, deployment и acceptance,
а не количество файлов или coverage.

## Следующий этап

```text
RECOMMENDED_NEXT_TASK =
NONE_AUTOMATIC
NEXT_TASK_REQUIRES_SEPARATE_OPERATOR_AUTHORIZATION = YES
```

Readonly API canary и `setups` production acceptance остаются отдельными
задачами, требующими отдельного операторского разрешения и свежей проверки
production gates. Эта задача не запускает их автоматически. Market-data health
contract остаётся `DEPLOYED_STABLE`; API остаётся `PREPARED_NOT_DEPLOYED`.

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
