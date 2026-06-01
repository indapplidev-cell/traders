# Traders

`Traders` — серверное ядро paper-only крипто-MVP на Python. Проект получает публичные свечи Binance, хранит их в PostgreSQL, считает индикаторы, принимает решения `BUY / SELL / HOLD` и выполняет только виртуальные сделки.

Проект намеренно остаётся в рамках:

- public Binance market data;
- PostgreSQL;
- paper trading;
- backtest;
- CLI.

## GitHub setup

Локальный каталог должен быть подключён к репозиторию:

- repository: `indapplidev-cell/traders`
- branch: `main`
- remote: `https://github.com/indapplidev-cell/traders.git`

Если каталог ещё не инициализирован как git-репозиторий:

```powershell
git init -b main
git remote add origin https://github.com/indapplidev-cell/traders.git
```

Если remote уже есть, проверьте:

```powershell
git remote -v
git branch
```

`.env` коммитить нельзя. Для локального security-поиска:

```powershell
Get-ChildItem -Recurse -File -Exclude *.pyc | Select-String "<известный-root-пароль>"
```

Подключение GitHub app к ChatGPT/Codex через UI требует ручного действия пользователя.

## Server deployment

Целевой сервер:

- IP: `185.216.87.26`
- OS: `Ubuntu 22.04`
- project path: `/opt/traders`

Базовая последовательность деплоя:

```bash
mkdir -p /opt/traders
git clone https://github.com/indapplidev-cell/traders.git /opt/traders
cd /opt/traders
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

Если репозиторий приватный, вместо HTTPS нужен deploy key. Скрипты для серверного контура лежат в:

- [scripts/server_bootstrap.sh](scripts/server_bootstrap.sh)
- [scripts/server_update.sh](scripts/server_update.sh)
- [scripts/server_check.sh](scripts/server_check.sh)

## PostgreSQL on VPS

Production compose-файл:

- [docker-compose.server.yml](docker-compose.server.yml)

PostgreSQL запускается только локально на VPS:

- bind: `127.0.0.1:5432:5432`
- container: `traders_postgres`
- db: `traders`
- user: `traders`

Запуск:

```bash
cd /opt/traders
docker compose -f docker-compose.server.yml --env-file .env up -d
docker exec traders_postgres pg_isready -U traders -d traders
```

## Async database connection

В проект добавлен отдельный async-слой:

- [app/db/async_session.py](app/db/async_session.py)

Поддерживаются два варианта:

- явный `ASYNC_DATABASE_URL`;
- автоматическое преобразование sync PostgreSQL URL в `postgresql+asyncpg://...`

CLI-команда проверки:

```bash
python -m app.cli.commands async-health
```

Она создаёт async engine и выполняет `SELECT 1`.

## Server commands

Создание `.env` на сервере:

```bash
cd /opt/traders
openssl rand -base64 32
```

Пример `.env`:

```dotenv
APP_ENV=production
POSTGRES_PASSWORD=REPLACE_WITH_GENERATED_PASSWORD
DATABASE_URL=postgresql+psycopg://traders:REPLACE_WITH_GENERATED_PASSWORD@127.0.0.1:5432/traders
ASYNC_DATABASE_URL=postgresql+asyncpg://traders:REPLACE_WITH_GENERATED_PASSWORD@127.0.0.1:5432/traders
BINANCE_PUBLIC_REST_URL=https://api.binance.com
DEFAULT_SYMBOL=BTCUSDT
DEFAULT_INTERVAL=15m
DEFAULT_CANDLE_LIMIT=300
PAPER_INITIAL_BALANCE_USDT=1000
PAPER_POSITION_SIZE_FRACTION=0.01
PAPER_MAX_OPEN_POSITIONS=1
```

Права:

```bash
chmod 600 .env
```

Основные команды проекта:

```bash
python -m app.cli.commands --help
python -m app.cli.commands health
python -m app.cli.commands async-health
python -m app.cli.commands fetch-candles --symbol BTCUSDT --interval 15m --limit 300
python -m app.cli.commands analyze --symbol BTCUSDT --interval 15m
python -m app.cli.commands paper-step --symbol BTCUSDT --interval 15m
python -m app.cli.commands portfolio
python -m app.cli.commands load-history --symbol BTCUSDT --interval 15m --days 30
python -m app.cli.commands backtest --symbol BTCUSDT --interval 15m --limit 1000
python -m app.cli.commands backtest --symbol BTCUSDT --interval 15m --days 30
python -m app.cli.commands paper-runner --help
```

## Server verification

Локально подтверждено:

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m app.cli.commands --help
.\.venv\Scripts\python -m app.cli.commands async-health --help
.\.venv\Scripts\python -m app.cli.commands load-history --help
.\.venv\Scripts\python -m app.cli.commands backtest --help
.\.venv\Scripts\python -m app.cli.commands paper-runner --help
```

Серверные шаги, которые нужно проверить уже на VPS:

```bash
docker compose -f docker-compose.server.yml --env-file .env up -d
alembic upgrade head
python -m app.cli.commands health
python -m app.cli.commands async-health
python -m app.cli.commands load-history --symbol BTCUSDT --interval 15m --days 30
python -m app.cli.commands backtest --symbol BTCUSDT --interval 15m --days 30
```

Полный фактический статус текущего прохода фиксируется в [reports/server_deploy_report.md](reports/server_deploy_report.md).

## Security notes

- `.env` не коммитить.
- PostgreSQL на VPS должен слушать только `127.0.0.1`.
- Ключи Binance в проект не добавляются.
- Root password нельзя хранить в README, отчётах, `.env.example`, скриптах и git.
- После первичного входа на VPS лучше сменить root password или перейти на SSH key-only.
- Live trading, реальные ордера, futures, margin, leverage, Telegram, GUI и FastAPI в проект не добавляются.
