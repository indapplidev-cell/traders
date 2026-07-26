DOCUMENT = online_trader.md
DOCUMENT_ROLE = SINGLE_SOURCE_OF_TRUTH_FOR_PROJECT_STATUS
DOCUMENT_SNAPSHOT_TYPE = POST_TASK_PROVEN_STATE
PROJECT = traders-ml

STATUS_AS_OF_COMMIT = 92816732fe91ce8834e76856e6c74795fd8b76d0
DOCUMENT_REVISION = SELF
DOCUMENT_COMMIT_RESOLUTION = git log -1 --format=%H -- online_trader.md

RECONCILED_AT_UTC = 2026-07-26T17:27:14Z
RECONCILED_BY_TASK = TRADERS-ML-SERVER-READONLY-API-RUNTIME-ENTRYPOINT-AND-LOCK-CONTRACT-01
FILES_CHANGED = online_trader.md

REMOTE_PRODUCTION_BASE_AT_RECONCILIATION = 74db6518d2a144fcf8814323c55e4224a71700e9
PUSH_STATE_AT_RECONCILIATION = NOT_PUSHED
STATUS_CONFIDENCE = PROVEN_INTEGRATION_STATE

# Состояние проекта traders-ml

## Текущая стадия

```text
ROOT_BRANCH = feature/engine-platform
API_ROOT_STATUS = INTEGRATED_NOT_DEPLOYED
API_RUNTIME_STATUS = ENTRYPOINT_IMPLEMENTED_NOT_DEPLOYED
CURRENT_STAGE = TRADERS-ML-SERVER-READONLY-API-POST-INTEGRATION-BUILD-CANARY-PREPARATION-01-RERUN
CURRENT_BLOCKER = NONE_FOR_POST_INTEGRATION_PREPARATION_RERUN
```

Root project-state commit `d7887845e79b4db9c87c8ee707184093fcc66643`
содержит:

- ранее интегрированный online engine pipeline;
- Readonly Server API v1;
- hash-locked runtime/dev dependency contract;
- cross-platform LF contract для lock-файлов и hash-checked OpenAPI snapshot;
- API, dependency-contract и root regression tests.

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
RUNTIME_FACTORY = app.server_api.runtime:create_runtime_app
EXECUTABLE_ENTRYPOINT = traders-readonly-api
MODULE_ENTRYPOINT = python -m app.server_api.runtime
DOCKER_API_TARGET = readonly-api, IMPLEMENTED_NOT_DEPLOYED
EPHEMERAL_READONLY_DB_SMOKE = PASS
API_ROUTE_COUNT = 9
API_GET_ONLY_ROUTES = 9
API_WRITE_ROUTES = 0
SELECT_ONLY_APPLICATION_ADAPTER = YES
DB_MIGRATIONS_ADDED = 0
PRODUCTION_MUTATIONS = 0
CANARY_STARTED = NO
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
API_FOCUSED = 46 passed
SAFE_REGRESSION = 611 passed, 2 deselected
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
COMPOSE_APPLIED = NO
SERVICES_RESTARTED = NO
CANARY_STARTED = NO
NEW_SOAK_STARTED = NO
PRIVATE_BINANCE_API_USED = NO
LIVE_ORDERS = 0
PUSHED = NO
```

Connection-preparation не интегрирован. Production runtime, PostgreSQL,
существующие сервисы и существующие soak artifacts этой задачей не изменялись
и не принимались повторно. Ранее доказанный engine deployment status не
повышается до API deployment status.

## Готовность основных контуров

| Контур | Готовность | Доказанное состояние |
|---|---:|---|
| Online analytics/paper pipeline | ≈82% | Интегрирован ранее; эта задача runtime не меняла |
| Production reliability/acceptance | ≈70% | API integration не является production acceptance |
| Readonly Server API | 75% | Root-integrated runtime entrypoint, exact ASGI lock, `readonly-api` image target and ephemeral read-only DB smoke proven; not deployed |
| Полный автономный LIVE-бот | ≈58% engineering / 0% operational | `LIVE = DISABLED` |

Проценты отражают implementation, integration, tests, deployment и acceptance,
а не количество файлов или coverage.

## Следующий этап

```text
RECOMMENDED_NEXT_TASK =
TRADERS-ML-SERVER-READONLY-API-POST-INTEGRATION-BUILD-CANARY-PREPARATION-01-RERUN
```

Следующая задача должна подготовить отдельно контролируемые build/canary gates.
Она не должна автоматически считаться deployment authorization. До отдельного
решения API остаётся `INTEGRATED_NOT_DEPLOYED`.

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
