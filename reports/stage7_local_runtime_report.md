# Stage 7 — Local Production-Like Runtime

## Цель этапа

Stage 7 добавляет локальную production-like проверку проекта `traders`.

Цель проверки — убедиться, что проект может быть поднят и проверен локально в режиме, близком к будущему серверному запуску, но без server deploy и без live trading.

Этап проверяет:

* структуру проекта;
* safety guard;
* локальную конфигурацию `.env`, `.env.example`, `docker-compose.yml`, `alembic.ini`;
* Docker PostgreSQL;
* Python settings;
* sync DB health;
* async DB health;
* Alembic migrations;
* terminal demo pipeline;
* fresh DB сценарий с пересозданием Docker volume.

## Что создано

Создан файл:

```text
scripts/local_runtime_check.py
```

Назначение файла:

```text
Локальный production-like runtime-check для проекта traders.
```

Скрипт поддерживает обычный режим:

```powershell
.venv\Scripts\python .\scripts\local_runtime_check.py --symbol BTCUSDT --interval 15m --days 7 --ticks 3 --initial-cash 1000
```

И destructive fresh DB режим:

```powershell
.venv\Scripts\python .\scripts\local_runtime_check.py --fresh-db --symbol BTCUSDT --interval 15m --days 7 --ticks 3 --initial-cash 1000
```

Важно:

```text
--fresh-db удаляет локальный Docker volume PostgreSQL через docker compose down -v.
```

## Что изменено

Изменены файлы:

```text
.env.example
scripts/demo_traders_pipeline.py
```

В `.env.example` добавлен обязательный параметр:

```env
POSTGRES_PASSWORD=local_dev_password
```

Также `.env.example` синхронизирован с локальным PostgreSQL runtime:

```env
DATABASE_URL=postgresql+psycopg://traders:local_dev_password@127.0.0.1:5432/traders
ASYNC_DATABASE_URL=postgresql+asyncpg://traders:local_dev_password@127.0.0.1:5432/traders
```

В `scripts/demo_traders_pipeline.py` исправлен footer: теперь итоговый список демонстрации показывает все реально выполненные этапы.

## Что проверяет local_runtime_check.py

### 1. Контекст проекта

Проверяет наличие ключевых элементов:

```text
app/
alembic/
tests/
reports/
scripts/
.env.example
alembic.ini
docker-compose.yml
pyproject.toml
```

### 2. Safety guard

Проверяет, что runtime остаётся paper-only.

Подтверждения:

```text
Режим: paper-only
Реальные ордера: запрещены
Binance private API: не используется
Server deploy: не выполняется
Daemon: не запускается
```

Также проверяется отсутствие запрещённых переменных окружения:

```text
BINANCE_API_KEY
BINANCE_SECRET_KEY
BINANCE_PRIVATE_API_KEY
BINANCE_PRIVATE_SECRET
```

### 3. Конфигурация

Проверяются:

```text
.env
.env.example
docker-compose.yml
alembic.ini
```

Обязательные параметры:

```text
DATABASE_URL
ASYNC_DATABASE_URL
POSTGRES_PASSWORD
POSTGRES_USER
POSTGRES_DB
sqlalchemy.url
```

Секреты и пароли в выводе маскируются.

### 4. Docker PostgreSQL

Проверяются команды:

```powershell
docker compose config
docker compose up -d postgres
docker compose ps
docker inspect traders_postgres
```

Для fresh DB режима дополнительно выполняется:

```powershell
docker compose down -v
```

### 5. Python settings

Проверяется, что приложение читает корректные настройки:

```text
DATABASE_URL
ASYNC_DATABASE_URL
```

Ожидаемые URL-типы:

```text
postgresql+psycopg://
postgresql+asyncpg://
```

### 6. DB health

Проверяются команды:

```powershell
python -m app.cli.commands health
python -m app.cli.commands async-health
```

### 7. Alembic

Проверяются команды:

```powershell
alembic upgrade head
alembic current
```

Ожидаемый head:

```text
0007_backtest_metrics (head)
```

### 8. Demo pipeline

Проверяется команда:

```powershell
python scripts/demo_traders_pipeline.py --symbol BTCUSDT --interval 15m --days 7 --ticks 3 --initial-cash 1000
```

Ожидаемые признаки успеха:

```text
Статус: УСПЕХ
Live trading не использовался
Реальных ордеров не было
```

## Результаты проверок

### local_runtime_check.py

Обычный режим:

```text
СТАТУС: УСПЕХ
Local production-like runtime проверен.
PostgreSQL работает.
Alembic на head.
Health OK.
Async health OK.
Demo pipeline OK.
Live trading не использовался.
Server deploy не выполнялся.
Daemon не запускался.
```

### local_runtime_check.py --fresh-db

Fresh DB режим:

```text
СТАТУС: УСПЕХ
Local production-like runtime проверен.
PostgreSQL работает.
Alembic на head.
Health OK.
Async health OK.
Demo pipeline OK.
Live trading не использовался.
Daemon не запускался.
```

Fresh DB сценарий успешно выполнил:

```text
docker compose down -v
docker compose up -d postgres
alembic upgrade head
demo pipeline
```

### Alembic

```text
alembic current
0007_backtest_metrics (head)
```

### Pytest

```text
pytest tests/test_local_runtime_check.py
19 passed
```

Полный pytest:

```text
pytest
140 passed
```

### Ruff

```text
ruff check .
All checks passed
```

## Подтверждение запретов

В Stage 7 не добавлялось:

```text
live trading
Binance private API
real Binance API keys
real orders
futures
margin
leverage
short execution
Telegram
FastAPI
GUI
ML
server deploy
systemd daemon
бесконечный runner
```

Server deploy не выполнялся.

VPS не трогался.

Daemon не создавался.

Live trading не использовался.

## Git

Текущая ветка:

```text
stage7-local-runtime
```

Файлы Stage 7:

```text
.env.example
scripts/local_runtime_check.py
tests/test_local_runtime_check.py
reports/stage7_local_runtime_report.md
scripts/demo_traders_pipeline.py
```

Commit hash:

```text
TBD_AFTER_COMMIT
```

Git status after checks:

```text
TBD_AFTER_FINAL_CHECKS
```

## Итог

Stage 7 добавляет локальный production-like runtime-check и подтверждает, что проект `traders` локально запускается в paper-only режиме, поднимает PostgreSQL через Docker Compose, применяет Alembic migrations до актуального head, проходит health/async-health и успешно выполняет полный terminal demo pipeline.

Stage 7 не добавляет live trading и не выполняет server deploy.
