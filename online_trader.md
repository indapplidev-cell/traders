DOCUMENT = online_trader.md
DOCUMENT_ROLE = SINGLE_SOURCE_OF_TRUTH_FOR_PROJECT_STATUS
DOCUMENT_SNAPSHOT_TYPE = POST_TASK_PROVEN_STATE
PROJECT = traders-ml

STATUS_AS_OF_COMMIT = 4dcb6a3a228017408fc8e6caf554908e6b67289c
DOCUMENT_REVISION = SELF
DOCUMENT_COMMIT_RESOLUTION = git log -1 --format=%H -- online_trader.md

RECONCILED_AT_UTC = 2026-07-27T11:23:29Z
RECONCILED_BY_TASK = TRADERS-ML-MARKET-DATA-BOUNDARY-AWARE-HEALTH-SEMANTICS-01
FILES_CHANGED = app/engine_market_data/continuous_sync_daemon.py; app/engine_market_data/freshness_monitor.py; app/engine_market_data/operational/prod_smoke.py; app/engine_observation/observation_runner.py; docs/operations/market_data_boundary_health.md; tests/test_engine_market_data_04_boundary_aware_health.py; tests/test_engine_market_data_04_freshness_monitor.py; tests/test_engine_market_data_04_health_consumers.py; online_trader.md

REMOTE_PRODUCTION_BASE_AT_RECONCILIATION = 74db6518d2a144fcf8814323c55e4224a71700e9
PUSH_STATE_AT_RECONCILIATION = NOT_PUSHED
STATUS_CONFIDENCE = PROVEN_LOCAL_BOUNDARY_HEALTH_IMPLEMENTATION_NOT_DEPLOYED

# Состояние проекта traders-ml

## Текущая стадия

```text
ROOT_BRANCH = feature/engine-platform
API_ROOT_STATUS = PREPARED_NOT_DEPLOYED
API_RUNTIME_STATUS = PREPARED_NOT_DEPLOYED
CURRENT_STAGE = AWAITING_SEPARATELY_AUTHORIZED_CONTROLLED_DEPLOYMENT_SELECTION
CURRENT_BLOCKER = NONE_FOR_LOCAL_IMPLEMENTATION; PRODUCTION_DEPLOYMENT_NOT_AUTHORIZED
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
MARKET_DATA_BOUNDARY_AWARE_HEALTH = IMPLEMENTED
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
MARKET_DATA_FOCUSED_TESTS = 192 passed, 1 skipped
SAFE_REGRESSION = 676 passed, 2 skipped
PRODUCTION_DEPLOYMENT = NOT_PERFORMED
SETUPS_FIX_BRANCH = RETAINED_UNCHANGED
```

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
active error остаются blocking. Production code не deployed, сервисы не
перезапускались, PostgreSQL schema/data не изменялись.

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
PRODUCTION_RUNTIME_CHANGED = NO
POSTGRESQL_CHANGED = NO
ALEMBIC_RUN = NO
PRODUCTION_COMPOSE_APPLIED = NO
TASK_OWNED_CANARY_COMPOSE_DRY_RUN = PASS
SERVICES_RESTARTED = NO
PRODUCTION_CANARY_STARTED = NO
NEW_SOAK_STARTED = NO
PRIVATE_BINANCE_API_USED = NO
LIVE_ORDERS = 0
PUSHED = NO
```

Canary preparation интегрирован, но production canary не запускался. Production
runtime, PostgreSQL, существующие сервисы и существующие soak artifacts этой
задачей не изменялись и не принимались повторно. Ранее доказанный engine
deployment status не повышается до API deployment status.

## Готовность основных контуров

| Контур | Готовность | Доказанное состояние |
|---|---:|---|
| Online analytics/paper pipeline | ≈82% | Интегрирован ранее; эта задача runtime не меняла |
| Production reliability/acceptance | ≈70% | API integration не является production acceptance |
| Readonly Server API | 75% | Reproducible build contract and disabled-by-default hardened canary configuration passed a task-owned ephemeral DB dry-run; production canary not started |
| Market-data health contract | Implemented/tested, not deployed | Boundary grace operational readiness and real-failure blocking passed deterministic and full regression gates |
| Полный автономный LIVE-бот | ≈58% engineering / 0% operational | `LIVE = DISABLED` |

Проценты отражают implementation, integration, tests, deployment и acceptance,
а не количество файлов или coverage.

## Следующий этап

```text
RECOMMENDED_NEXT_TASK =
NONE_AUTOMATIC
NEXT_TASK_REQUIRES_SEPARATE_OPERATOR_AUTHORIZATION = YES
```

Возможные будущие controlled deployment market-data health и Readonly API
canary/setup acceptance являются отдельными задачами. Обе требуют отдельного
операторского разрешения и свежей проверки production gates. Эта задача не
выбирает и не запускает ни одну из них. До отдельного решения новый health
contract и API остаются `NOT_DEPLOYED` / `PREPARED_NOT_DEPLOYED`.

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
