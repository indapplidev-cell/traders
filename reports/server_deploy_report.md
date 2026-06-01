# Server Deploy Report

## Статус
Частично готово

## GitHub
- Repo: `indapplidev-cell/traders`
- Branch: `main`
- Remote: `https://github.com/indapplidev-cell/traders.git`
- Push result: успешно, `main -> origin/main`
- Codex GitHub connection: требует ручного подтверждения пользователя через UI

## Server
- IP: `185.216.87.26`
- OS: `Ubuntu 22.04`
- Project path: `/opt/traders`
- SSH status: сервер отвечает, но вход не завершён в этой сессии из-за требования ручной аутентификации

## PostgreSQL
- Deployment method: подготовлен `docker-compose.server.yml`
- Container: `traders_postgres`
- Port binding: `127.0.0.1:5432:5432`
- Health: не проверен на VPS
- Database: `traders`
- User: `traders`
- External port exposed: no, настроено только локальное bind-подключение

## Async DB
- ASYNC_DATABASE_URL configured: не подтверждено на сервере; поддержка добавлена в код и `.env.example`
- async-health result: runtime-проверка не выполнена без живого PostgreSQL

## Alembic
Команда:

```bash
alembic upgrade head
```

Результат:

Не проверено на VPS, потому что PostgreSQL на сервере не был поднят в этой сессии.

## Runtime checks

### pytest
Команда:

```powershell
.\.venv\Scripts\python -m pytest
```

Результат:

`46 passed in 9.40s`

### ruff
Команда:

```powershell
.\.venv\Scripts\python -m ruff check .
```

Результат:

`All checks passed!`

### health
Команда:

```powershell
.\.venv\Scripts\python -m app.cli.commands health
```

Результат:

Не запускалось против живого PostgreSQL.

### async-health
Команда:

```powershell
.\.venv\Scripts\python -m app.cli.commands async-health
```

Результат:

Не запускалось против живого PostgreSQL.

Дополнительно проверено:

```powershell
.\.venv\Scripts\python -m app.cli.commands async-health --help
```

Результат:

Help отработал успешно.

### fetch-candles
Команда:

```powershell
.\.venv\Scripts\python -m app.cli.commands fetch-candles --symbol BTCUSDT --interval 15m --limit 300
```

Результат:

Не проверено без доступной PostgreSQL runtime-среды.

### analyze
Команда:

```powershell
.\.venv\Scripts\python -m app.cli.commands analyze --symbol BTCUSDT --interval 15m
```

Результат:

Не проверено без доступной PostgreSQL runtime-среды.

### paper-step
Команда:

```powershell
.\.venv\Scripts\python -m app.cli.commands paper-step --symbol BTCUSDT --interval 15m
```

Результат:

Не проверено без доступной PostgreSQL runtime-среды.

### portfolio
Команда:

```powershell
.\.venv\Scripts\python -m app.cli.commands portfolio
```

Результат:

Не проверено без доступной PostgreSQL runtime-среды.

### load-history
Команда:

```powershell
.\.venv\Scripts\python -m app.cli.commands load-history --symbol BTCUSDT --interval 15m --days 30
```

Результат:

Не проверено без доступной PostgreSQL runtime-среды.

### backtest limit
Команда:

```powershell
.\.venv\Scripts\python -m app.cli.commands backtest --symbol BTCUSDT --interval 15m --limit 1000
```

Результат:

Не проверено без доступной PostgreSQL runtime-среды.

### backtest days
Команда:

```powershell
.\.venv\Scripts\python -m app.cli.commands backtest --symbol BTCUSDT --interval 15m --days 30
```

Результат:

Не проверено без доступной PostgreSQL runtime-среды.

## Что не удалось проверить

- Подключение Codex/GitHub через UI environment-экран
- SSH-вход на VPS без ручного ввода пароля или заранее настроенного ключа
- Обновление пакетов на VPS
- Установка Docker на VPS
- Подъём PostgreSQL на VPS
- Создание серверного `.env`
- `alembic upgrade head` на VPS
- Полный runtime-контур CLI на VPS

Фактически проверено по SSH:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@185.216.87.26 "pwd"
```

Результат:

`Permission denied (publickey,password).`

## Безопасность
Подтверждаю:

- `.env` не закоммичен
- root password не сохранён в файлах
- ключи Binance не добавлены
- live trading не добавлен
- real orders не добавлены
- futures не добавлены
- margin не добавлен
- leverage не добавлен
- Telegram не добавлен
- GUI не добавлен
- PostgreSQL в production compose настроен без внешнего открытия порта

## Риски и замечания

- Локальный каталог изначально не был git-репозиторием; репозиторий и ветка `main` инициализированы в этой сессии.
- История git сейчас начинается с локального root commit `08cc04a`.
- Серверные скрипты созданы, но не исполнялись на VPS.
- Для завершения серверной части нужен ручной SSH-вход пользователя и фактическое выполнение команд на Ubuntu 22.04.
