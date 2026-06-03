# Stage 2 Report

Дата проверки: `2026-06-01`

## Что завершено в этом проходе

- добавлен исторический загрузчик `app/history/historical_loader.py`;
- добавлена CLI-команда `load-history`;
- `backtest` получил DB-режим `--days`;
- состояние backtest вынесено в отдельный модуль `app/backtest/backtest_portfolio.py`;
- `CandleService` получил переиспользуемый `store_candles(...)` и dialect-aware upsert для PostgreSQL/SQLite;
- `BinancePublicClient` получил поддержку `startTime/endTime`;
- `MarketAnalysisService` получил чтение свечей из БД по диапазону времени;
- README переписан в актуальном виде на русском языке;
- добавлены тесты для `load-history` и DB-режима backtest;
- локальные `__pycache__`, `*.pyc` вне `.venv` и `traders.egg-info` удалены.

## Изменённые файлы

- `README.md`
- `app/backtest/backtest_engine.py`
- `app/backtest/backtest_portfolio.py`
- `app/cli/commands.py`
- `app/exchange/binance_public_client.py`
- `app/history/__init__.py`
- `app/history/historical_loader.py`
- `app/market/analysis_service.py`
- `app/market/candle_service.py`
- `reports/stage2_report.md`
- `tests/test_backtest.py`
- `tests/test_cli.py`
- `tests/test_historical_loader.py`

## Миграции

Новых миграций в этом проходе не добавлял.

Для Stage 2 в проекте уже используется миграция:

- `alembic/versions/0003_runner_state.py`

## Добавленные тесты

- `tests/test_historical_loader.py`
- в `tests/test_cli.py` добавлена проверка `load-history --help`
- в `tests/test_backtest.py` добавлена проверка DB-режима `load_candles_from_db(...)`

## Реально выполненные команды

### Тесты и линтер

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
```

Результат:

- `pytest`: `51 passed`
- `ruff check .`: `All checks passed!`

### CLI help

```powershell
.\.venv\Scripts\python -m app.cli.commands --help
.\.venv\Scripts\python -m app.cli.commands load-history --help
.\.venv\Scripts\python -m app.cli.commands backtest --help
.\.venv\Scripts\python -m app.cli.commands paper-runner --help
```

Результат:

- все четыре команды отработали успешно;
- `load-history` присутствует в общем help;
- `backtest` показывает опцию `--days`;
- `paper-runner` help отработал без доступа к `.env` и БД на этапе импорта CLI.

### Docker / PostgreSQL

```powershell
docker --version
docker compose up -d
```

Результат:

- `docker --version`: `Docker version 28.3.2, build 578ccf6`
- `docker compose up -d`: ошибка подключения к Docker daemon

Фактический текст ошибки:

```text
unable to get image 'postgres:16': error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/images/postgres:16/json": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

## Stage 2.5 Follow-up

- `alembic current`: `0003_runner_state`
- local PostgreSQL runtime: `OK`

## Что не подтверждено в этой среде

В рамках Stage 2.5 уже были подтверждены локальные PostgreSQL-проверки. Неподтверждёнными оставались только серверные проверки на VPS.

## Команды для ручной проверки после запуска Docker

```powershell
docker compose up -d
alembic upgrade head
python -m app.cli.commands health
python -m app.cli.commands load-history --symbol BTCUSDT --interval 15m --days 30
python -m app.cli.commands backtest --symbol BTCUSDT --interval 15m --days 30
python -m app.cli.commands paper-step --symbol BTCUSDT --interval 15m
python -m app.cli.commands portfolio
```
