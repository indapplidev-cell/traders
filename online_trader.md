DOCUMENT = online_trader.md
DOCUMENT_ROLE = SINGLE_SOURCE_OF_TRUTH_FOR_PROJECT_STATUS
DOCUMENT_SNAPSHOT_TYPE = POST_TASK_PROVEN_STATE
PROJECT = traders-ml

STATUS_AS_OF_COMMIT = f5b48e061f99afea81f3fd39b296acded477f8b6
DOCUMENT_REVISION = SELF
DOCUMENT_COMMIT_RESOLUTION = git log -1 --format=%H -- online_trader.md

RECONCILED_AT_UTC = 2026-07-26T18:43:37Z
RECONCILED_BY_TASK = TRADERS-ML-SERVER-READONLY-API-POST-INTEGRATION-BUILD-CANARY-PREPARATION-01-RERUN
FILES_CHANGED = ops/canary/readonly-api/**; scripts/verify_readonly_api_canary_contract.py; tests/server_api/test_canary_configuration.py; online_trader.md

REMOTE_PRODUCTION_BASE_AT_RECONCILIATION = 74db6518d2a144fcf8814323c55e4224a71700e9
PUSH_STATE_AT_RECONCILIATION = NOT_PUSHED
STATUS_CONFIDENCE = PROVEN_CANARY_PREPARATION_STATE

# Состояние проекта traders-ml

## Текущая стадия

```text
ROOT_BRANCH = feature/engine-platform
API_ROOT_STATUS = PREPARED_NOT_DEPLOYED
API_RUNTIME_STATUS = PREPARED_NOT_DEPLOYED
CURRENT_STAGE = TRADERS-ML-SERVER-READONLY-API-CONTROLLED-CANARY-DEPLOYMENT-01
CURRENT_BLOCKER = SEPARATE_OPERATOR_AUTHORIZATION_REQUIRED
```

Root project-state commit `f5b48e061f99afea81f3fd39b296acded477f8b6`
содержит:

- ранее интегрированный online engine pipeline;
- Readonly Server API v1;
- hash-locked runtime/dev dependency contract;
- cross-platform LF contract для lock-файлов и hash-checked OpenAPI snapshot;
- API, dependency-contract и root regression tests;
- disabled-by-default hardened canary configuration, verifier, runbook and
  rollback plan.

Перенесены только implementation commits:

```text
c3c8e8a3e539b29f3faa23f8fe0c700af514d36c
0041cc3ec15d2e11fa44b345c74bca11d2a585c4
```

Старые status commits
`3f3444fb0691854c89a47c7e20816d92daedff6e` и
`c20d0ecc50c22f44a610355e2472098fd074b49e` не интегрированы.

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
| Полный автономный LIVE-бот | ≈58% engineering / 0% operational | `LIVE = DISABLED` |

Проценты отражают implementation, integration, tests, deployment и acceptance,
а не количество файлов или coverage.

## Следующий этап

```text
RECOMMENDED_NEXT_TASK =
TRADERS-ML-SERVER-READONLY-API-CONTROLLED-CANARY-DEPLOYMENT-01
NEXT_TASK_REQUIRES_SEPARATE_OPERATOR_AUTHORIZATION = YES
```

Следующая задача может запускать production canary только после отдельного
операторского разрешения и свежей проверки production gates. Подготовительный
dry-run не является deployment authorization или production acceptance. До
отдельного решения API остаётся `PREPARED_NOT_DEPLOYED`.

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
