DOCUMENT = online_trader.md
DOCUMENT_ROLE = SINGLE_SOURCE_OF_TRUTH_FOR_PROJECT_STATUS
DOCUMENT_SNAPSHOT_TYPE = POST_TASK_PROVEN_STATE
PROJECT = traders-ml

STATUS_AS_OF_COMMIT = d7887845e79b4db9c87c8ee707184093fcc66643
DOCUMENT_REVISION = SELF
DOCUMENT_COMMIT_RESOLUTION = git log -1 --format=%H -- online_trader.md

RECONCILED_AT_UTC = 2026-07-26T11:30:00Z
RECONCILED_BY_TASK = TRADERS-ML-SERVER-READONLY-API-ROOT-INTEGRATION-01
FILES_CHANGED = online_trader.md

REMOTE_PRODUCTION_BASE_AT_RECONCILIATION = 74db6518d2a144fcf8814323c55e4224a71700e9
PUSH_STATE_AT_RECONCILIATION = NOT_PUSHED
STATUS_CONFIDENCE = PROVEN_INTEGRATION_STATE

# Состояние проекта traders-ml

## Текущая стадия

```text
ROOT_BRANCH = feature/engine-platform
API_ROOT_STATUS = INTEGRATED_NOT_DEPLOYED
CURRENT_STAGE = TRADERS-ML-SERVER-READONLY-API-POST-INTEGRATION-BUILD-CANARY-PREPARATION-01
CURRENT_BLOCKER = NONE_FOR_POST_INTEGRATION_PREPARATION
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
API_ROUTE_COUNT = 9
API_GET_ONLY_ROUTES = 9
API_WRITE_ROUTES = 0
SELECT_ONLY_APPLICATION_ADAPTER = YES
DB_MIGRATIONS_ADDED = 0
```

API импортируется и создаёт inert FastAPI application без подключения к БД,
открытия socket или запуска background work. Production repositories должны
передаваться явно.

Подтверждённые integration gates:

```text
LOCK_ROOT_COMPATIBILITY = PASS
LOCK_HASHES_COMPLETE = YES
ROOT_DEPENDENCY_COVERAGE = COMPLETE
VERIFY_ENV_1_INSTALL = PASS
VERIFY_ENV_2_INSTALL = PASS
NORMALIZED_FREEZE_MATCH = YES
DEPENDENCY_CONTRACT_TESTS = 2 passed
API_FOCUSED = 26 passed
SAFE_REGRESSION = 553 passed, 2 deselected
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
| Readonly Server API | 75% | Root-integrated, locked и Linux-smoke validated; не deployed |
| Полный автономный LIVE-бот | ≈58% engineering / 0% operational | `LIVE = DISABLED` |

Проценты отражают implementation, integration, tests, deployment и acceptance,
а не количество файлов или coverage.

## Следующий этап

```text
RECOMMENDED_NEXT_TASK =
TRADERS-ML-SERVER-READONLY-API-POST-INTEGRATION-BUILD-CANARY-PREPARATION-01
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
