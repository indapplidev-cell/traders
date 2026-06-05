# Stage 9.1 - Strategy Registry Expansion

## Что сделано

- В реестр стратегий добавлены paper-only стратегии `safe_hold`, `ema_cross`, `rsi_reversion`, `breakout_volume`.
- Архитектура `app/strategy` сохранена без изменения публичного контракта `BaseStrategy` и `StrategyDecision`.
- Логика `simple_trend` не менялась.
- Новые стратегии не трогают риск-менеджмент, БД, миграции Alembic, live trading, Binance private API и server deploy.

## Новые стратегии

### safe_hold

- Всегда возвращает `HOLD`.
- Используется как безопасная sandbox-стратегия без торгового сигнала.

### ema_cross

- Использует `ema_20`, `ema_50` и `last_close`.
- Возвращает `HOLD`, если индикаторы отсутствуют или `last_close <= 0`.
- Возвращает `BUY`, если `ema_20 > ema_50`.
- Возвращает `SELL`, если `ema_20 < ema_50`.
- Возвращает `HOLD`, если спред между EMA меньше 0.1% от цены.

### rsi_reversion

- Использует `rsi_14`.
- Возвращает `BUY` в перепроданности.
- Возвращает `SELL` в перекупленности.
- Возвращает `HOLD`, если экстремума нет или индикатор отсутствует.

### breakout_volume

- Использует `last_close`, `last_volume`, `volume_sma_20`, `ema_20`, `ema_50`.
- Требует объём выше средней `volume_sma_20`.
- Возвращает `BUY` при бычьем подтверждении цены и EMA.
- Возвращает `SELL` при медвежьем подтверждении цены и EMA.
- Иначе возвращает `HOLD`.

## Проверки

- `python -m py_compile app/strategy/strategy_registry.py`
- `python -m py_compile app/strategy/safe_hold.py`
- `python -m py_compile app/strategy/ema_cross.py`
- `python -m py_compile app/strategy/rsi_reversion.py`
- `python -m py_compile app/strategy/breakout_volume.py`
- `python -m app.cli.commands strategy-list`
- `python -m app.cli.commands strategy-run --strategy safe_hold --symbol BTCUSDT --interval 15m`
- `python -m app.cli.commands strategy-run --strategy ema_cross --symbol BTCUSDT --interval 15m`
- `python -m app.cli.commands strategy-run --strategy rsi_reversion --symbol BTCUSDT --interval 15m`
- `python -m app.cli.commands strategy-run --strategy breakout_volume --symbol BTCUSDT --interval 15m`
- `pytest tests/test_strategy_registry.py`
- `pytest tests/test_runner_cli.py`
- `pytest`
- `ruff check .`

## Ограничения

- Риск-профили не добавлялись.
- CLI-флаг `--risk-profile` не добавлялся.
- Live trading не затрагивался.
- Server deploy и daemon не затрагивались.
