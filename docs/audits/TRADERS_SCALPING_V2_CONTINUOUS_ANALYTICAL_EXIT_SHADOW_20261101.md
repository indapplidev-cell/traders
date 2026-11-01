# Scalping v2 — continuous analytical exit SHADOW

Дата: 2026-11-01. Ветка: `feature/engine-platform`.

## Вердикт

`IMPLEMENTED_DEPLOYED_SHADOW / PAPER_PROMOTION_PENDING_EVIDENCE`.

Для открытых Scalping v2 PAPER-позиций реализован причинный анализ каждой закрытой 1m-свечи с последним закрытым 5m-контекстом. Контур развёрнут только в режиме `SHADOW`: он не получает права закрывать позицию до прохождения заданных offline/natural gates.

На момент deployment открытых позиций и новых PAPER-команд нет, поэтому сохранение естественного `ExitEvidenceV2` на реальной позиции и задержка `EXIT → close command` пока `UNPROVEN`.

## Реализовано

- Полный OHLCV-контракт вместо прежнего `volume=0`: base/quote volume, trades count, source и causal boundaries.
- Отдельные серии 96 закрытых 1m и 96 закрытых 5m свечей; gaps, дубликаты, незакрытые и будущие свечи fail closed.
- Повторный canonical engine analysis: Altunina, Schwager, Nison, EMA, MACD, RSI, SMA, ATR, ADX, Bollinger, VWAP, regime, impulse и volume context.
- Версионированный `exit-evidence-v2` с component scores 35/35/20/10, continuation/exit score, MFE/MAE, расстоянием до stop/target, target progress и modeled gross/net PnL.
- Решения `HOLD`, `AT_RISK`, `EXIT_CONFIRMATION_PENDING`, `ANALYTICAL_EXIT`, `STRONG_REVERSAL_EXIT`, `PROFIT_PROTECTION_EXIT`, `DATA_UNAVAILABLE`, `ERROR`.
- Обычный analytical exit требует двух последовательных границ ≥70; strong reversal требует structure+regime и score ≥80.
- Один индикатор не может самостоятельно достичь exit threshold.
- Evidence сохраняется идемпотентно в существующем `scalping_position_hold_decisions.evidence`; новая таблица и migration не потребовались.
- PostgreSQL `LISTEN/NOTIFY` связывает commit закрытой 1m-свечи с немедленным wakeup lifecycle; fallback polling — 5 секунд.
- Notifier fail-open к polling recovery и не отменяет уже сохранённую свечу.
- Будущий режим `PAPER` поддержан контрактом, но текущий authoritative config/default остаётся `SHADOW`.

## Проверки

- Focused regression: `190 passed`.
- Финальные analytical/lifecycle tests: `24 passed` и `11 passed` после event integration.
- Docker build: market-data WebSocket PASS; operator-control API PASS.
- Runtime `LISTEN traders_closed_candle_1m`: active.
- Естественная граница `2026-11-01 04:09 UTC`: operator получил wakeup для всех 20 символов.
- Operator API: healthy; runtime revision `7ab9fe5`.
- WebSocket runtime revision `8146341`; emitter code соответствует deployed event contract.
- PAPER control: `CONTINUOUS_ARMED`, generation 20, commands used 0.
- Open/CLOSING positions: 0; commands since deployment: 0.
- LIVE не включался; Binance order authority не добавлялась.

Два старых теста runtime config epoch остаются baseline failures из-за уже существующей логики parameter-set override и не вызваны analytical exit.

## Незавершённые acceptance gates

Следующие пункты нельзя честно объявить PASS без естественной выборки:

1. Не менее 100 holdout-сделок и пяти UTC-дней.
2. Win Rate >50%, Profit Factor ≥1.20, expectancy/net PnL >0.
3. Не менее 30 естественных SHADOW PAPER-позиций и семи дней наблюдения.
4. Положительный net PnL delta относительно действующего выхода.
5. Измеренный p95 полного пути closed candle → shadow decision ≤5 секунд и максимум ≤8 секунд на открытых позициях.
6. После прохождения всех ворот — отдельное переключение `SHADOW → PAPER`; LIVE остаётся запрещённым.

До выполнения этих условий автоматическая авторитетная активация намеренно заблокирована.

## Safety

- Стартовый PAPER-капитал остаётся 1000 USDT.
- Вход, position sizing, stop, target и риск-политика не менялись.
- Stop-Loss/Take-Profit и system safety сохраняют приоритет.
- Миграции и рестарт PostgreSQL не выполнялись.
- Существующие пользовательские удаления артефактов, изменение `online_trader.md` и forensic-файлы не включены в implementation commits.
