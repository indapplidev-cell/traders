# Stage ML2 Historical Loader Report

## Created Files

- `app/data/__init__.py`
- `app/data/binance_client.py`
- `app/data/historical_loader.py`
- `app/data/candle_gap_checker.py`
- `app/data/candle_normalizer.py`
- `app/db/repositories/candle_repository.py`
- `tests/test_candle_normalizer.py`
- `tests/test_candle_gap_checker.py`
- `tests/test_candle_repository.py`
- `tests/test_historical_loader.py`
- `reports/stage_ml2_historical_loader_report.md`

## Changed Files

- `app/cli/commands.py`
- `app/db/repositories/__init__.py`
- `pyproject.toml`

## How Loading Works

- Команда `load-candles` принимает `symbol`, `interval`, `start-date`, `end-date`.
- Даты переводятся в UTC-диапазон:
  - `start-date` -> `00:00:00+00:00`
  - `end-date` -> следующий день `00:00:00+00:00`
- `BinanceClient` запрашивает публичные Binance klines без API key через `https://data-api.binance.vision/api/v3/klines`.
- Загрузка идёт постранично с лимитом `1000` свечей на запрос.
- `CandleNormalizer` преобразует raw Binance kline в внутренний формат `market_candles`.
- `HistoricalLoader` передаёт нормализованные свечи в `CandleRepository`.
- `CandleRepository.upsert_many()` выполняет upsert по `unique(symbol, interval, open_time)` и сохраняет свечи в PostgreSQL.
- CLI печатает summary в JSON:
  - `symbol`
  - `interval`
  - `start_at`
  - `end_at`
  - `loaded`
  - `inserted_or_updated`
  - `first_open_time`
  - `last_open_time`

## How Gap Checking Works

- Команда `check-candle-gaps` читает свечи из PostgreSQL через `CandleRepository.get_range()`.
- `CandleGapChecker` строит ожидаемую временную сетку по `interval` и диапазону дат.
- Затем проверяет:
  - есть ли пропущенные `open_time`
  - есть ли дубли `open_time`
  - выровнены ли `open_time` по интервалу
- Результат возвращается как JSON со сводкой:
  - `checked`
  - `unique_open_times`
  - `duplicate_count`
  - `gap_count`
  - `misaligned_count`
  - `is_valid`
  - списки `duplicates`, `missing_open_times`, `misaligned_open_times`

## Verification Commands

- `python -m pytest`
- `python -m app.cli.commands load-candles --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-01-02`
- `python -m app.cli.commands check-candle-gaps --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-01-02`

## Verification Results

- `python -m pytest`
  - `10 passed`
- `python -m app.cli.commands load-candles --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-01-02`
  - `loaded: 192`
  - `inserted_or_updated: 192`
  - `first_open_time: 2025-01-01T00:00:00+00:00`
  - `last_open_time: 2025-01-02T23:45:00+00:00`
- `python -m app.cli.commands check-candle-gaps --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-01-02`
  - `checked: 192`
  - `duplicate_count: 0`
  - `gap_count: 0`
  - `misaligned_count: 0`
  - `is_valid: true`
