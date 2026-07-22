DOCUMENT = online_trader.md
DOCUMENT_ROLE = SINGLE_SOURCE_OF_TRUTH_FOR_PROJECT_STATUS
PROJECT = traders-ml
UPDATED_AT_UTC = 2026-07-22T18:00:00Z
UPDATED_BY_TASK = ENGINE-MARKET-DATA-1H-FRESHNESS-DEADLINE-ROOT-CAUSE-02
BASE_COMMIT = 56486039167b0278633f0ef90f05787023807315
STATUS_CONFIDENCE = ENGINEERING_ESTIMATE

# Состояние проекта traders-ml

## Текущая стадия

Проект находится на стадии `production-hardening онлайн-аналитического контура`.

Рабочая online pipeline:

```text
engine_market_data
→ engine_analysis
→ engine_setup
→ engine_strategy
→ engine_risk
→ engine_paper
```

Pipeline запускается через `engine_orchestrator`.

Главный текущий blocker:

```text
Root-cause 51 истинного `FRESHNESS_DEADLINE_EXCEEDED` доказан. После transient
public-REST timeout `ContinuousSyncDaemon.sync_expected` не удаляет восстановленную
ошибку из `_pair_errors`: успешные 1h sync с `missing_count = 0` и lag 0 продолжают
публиковать `DEGRADED`. Strict freshness gate поэтому сохраняет
`waiting_timeframes = ["1h"]` до authoritative deadline. Первые 6 окон также
застали позднюю 1h candle; остальные 45 имели required boundary и блокировались
только ложным sticky `DEGRADED`.
```

Повторный 72-часовой soak пока не запущен. Заблокированная попытка
`ONLINE-ORCHESTRATOR-FRESHNESS-RETRY-SOAK-02-20260722T094858Z` не считается
активным soak:

```text
SOAK_START_STATUS = BLOCKED
NEW_72H_SOAK_STARTED = NO
SOAK_02_AUTHORIZATION_STATUS = BLOCKED_PENDING_MARKET_DATA_HEALTH_FIX_AND_CANARY
```

Текущий этап: root cause подтвержден; controlled fix ожидает отдельной авторизации.
Новый SOAK-02 не разрешен и не запущен.

## Общая инженерная оценка

```text
Онлайн-аналитик + paper-контур:      ≈ 82%
Production reliability/acceptance:  ≈ 68%
Полный автономный LIVE-бот:         ≈ 58%
```

Проценты отражают совокупность реализации, интеграции, тестирования,
deployment, production validation и операционной надежности. Они не равны test
coverage, количеству файлов или строк кода.

## Готовность по основным модулям

| Модуль | Готовность | Состояние |
|---|---:|---|
| `engine_market_data` | 95% | REST/WebSocket, closed candles, PostgreSQL, gap recovery, daemon, health и синхронизация `1m–1d` реализованы |
| `engine_analysis` | 92% | Рыночная структура, regime, impulse, entry quality, diagnostics и online runner работают |
| `engine_setup` | 87% | Setup families, diagnostics, quality scoring и historical discovery реализованы |
| `engine_strategy` | 82% | APPROVED/REJECTED решения и safety reasons реализованы; нужна дальнейшая production-калибровка |
| `engine_risk` | 75% | Предварительное risk approval работает; account-aware sizing еще не завершен |
| `engine_paper` | 70% | Гипотетические entry/stop/target планы и TP/SL/EXPIRED результаты; не полноценный fill/account simulator |
| `engine_orchestrator` | 90% | Online pipeline, dedupe, freshness gate, retry, WAITING→READY и result persistence работают |
| Freshness retry | 97% | Исправление принято, deployed, canary пройден, exact patch equivalence подтверждена |
| `engine_safety` | 65% | Safety gates встроены в orchestrator; самостоятельный полный модуль не завершен |
| Технический observer | 90% | PID, lock, heartbeat, monotonic scheduler, JSONL, restart/resume и controlled stop работают |
| Semantic observer | 90% | Реализован, exact patch-equivalent, host-side deployed и принят 63-минутным production canary: 64 samples, 447 heartbeats, 0 corrupt/duplicate/false incidents; controlled stop прошел |
| Docker/deployment | 90% | Production image развернут, сервисы стабильны, Git checkpoint и remote push завершены |
| PostgreSQL/Alembic | 88% | Production DB стабильна; нормализованные trade-lifecycle tables отсутствуют |
| Тесты и аудит | 85% | Focused tests, full suites, canary и evidence packages существуют |
| 72h production acceptance | 45% | Первый soak выявил freshness incidents и observer gaps; повторный soak заблокирован 51 подтвержденным 1h freshness deadline skip |

## Торговый lifecycle после risk

| Модуль | Готовность | Состояние |
|---|---:|---|
| `engine_trade_plan` | 20% | Документальный контракт готов; runtime-модуль не интегрирован |
| `engine_execution` | 35% | Есть intents, acknowledgements, modes и local gateways; нет production Binance private adapter и полной DB-интеграции |
| `engine_paper_execution` | 15% | Контракт спроектирован; полноценные paper fills не реализованы |
| `engine_paper_account` | 15% | Контракт готов; balance, equity, reserved funds и account ledger не реализованы |
| `engine_position` | 30% | Standalone lifecycle, fills, mark, fees и PnL; нет production persistence и orchestration |
| `engine_exit` | 15% | Skeleton; полноценное управление выходами не реализовано |
| `engine_journal` | 15% | Skeleton; нет нормализованного журнала decisions/orders/fills/PnL |
| LIVE Binance adapter | 5% | Намеренно отсутствует; private Binance API разрешен только будущему `engine_execution` |
| Реальная торговля | 0% operationally | `LIVE = DISABLED`; реальные ордера не отправляются |

## Реализованный функционал и архитектурная готовность

### Получение и подготовка рынка — 95%

```text
Binance public data
→ closed candles
→ PostgreSQL
→ gap recovery
→ health/freshness
```

### Рыночный анализ — 90%

```text
candles
→ structure/regime
→ impulse
→ entry quality
→ diagnostics
```

### Формирование торгового решения — 80%

```text
analysis
→ setup
→ strategy
→ risk approval
```

### Paper trading — 60–70%

Текущее состояние: `hypothetical trade-plan evaluation`.

Не хватает:

```text
fills;
partial fills;
slippage;
account balance;
reserved funds;
position ledger;
exit execution;
journal.
```

### Production reliability — 68%

Основные сервисы и orchestration работают. Retry lifecycle исправлен, но дефект
сброса восстановленного market-data health еще не исправлен.

Текущий пробел:

```text
`app/engine_market_data/continuous_sync_daemon.py::ContinuousSyncDaemon.sync_expected`
сохраняет historical `_pair_errors` после успешного восстановления и продолжает
публиковать `DEGRADED`. Strict orchestrator gate корректно блокирует такой статус.
Fix, deployment и production acceptance отсутствуют.
```

### LIVE execution

```text
архитектурно: около 20%
operationally: 0%
```

Пока отсутствуют:

```text
private Binance adapter;
production order persistence;
exchange reconciliation;
position recovery;
live safety approval;
controlled LIVE rollout.
```

`LIVE = DISABLED`.

## Ограничения и пробелы

Основной оставшийся объем относительно полноценного безопасного автономного
Binance-бота:

```text
semantic production monitoring;
повторный 72h acceptance;
trade-plan normalization;
execution;
paper fills;
account ledger;
position lifecycle;
exit management;
journal;
reconciliation;
account safety;
controlled LIVE rollout.
```

Semantic observer production-deployed и canary-validated, но новый SOAK-02
заблокирован 51 независимо подтвержденным true freshness deadline skip и не является
production acceptance. `engine_trade_plan` и последующие lifecycle-модули не
являются runtime-ready. LIVE execution operationally запрещен.

## Завершенные, текущие и предстоящие этапы

```text
Этап 1. Историческая аналитика                  — завершен
Этап 2. Online market-data и analysis           — почти завершен
Этап 3. Setup → strategy → risk → paper         — реализован
Этап 4. Online orchestrator                     — реализован
Этап 5. Freshness retry hardening               — завершен
Этап 6. Observer process reliability            — завершен технически
Этап 7. Semantic monitoring observer            — deployed и production canary validated
Этап 7b. Root-cause 1h freshness deadline skips — завершен; причина подтверждена
Этап 7c. Recovered pair health reset fix          — текущий этап; не авторизован
Этап 8. Повторный 72h production soak           — заблокирован; не запущен
Этап 9. Trade-plan/execution/position lifecycle — предстоит
Этап 10. Controlled LIVE rollout                — не разрешен
```

## Ближайшая последовательность

```text
ENGINE-MARKET-DATA-RECOVERED-PAIR-HEALTH-RESET-FIX-01
→ controlled fix и production canary
→ повторное решение об ONLINE-ORCHESTRATOR-FRESHNESS-RETRY-SOAK-02
→ 72h + settlement
→ final audit
→ production reliability checkpoint
→ engine_trade_plan
→ engine_paper_execution
→ engine_paper_account
→ engine_position integration
→ engine_exit
→ engine_journal
→ подготовка engine_execution для controlled LIVE
```

Следующая рекомендуемая задача:
`ENGINE-MARKET-DATA-RECOVERED-PAIR-HEALTH-RESET-FIX-01`.

## Общая оценка

Относительно полноценного безопасного автономного Binance-бота общая
инженерная оценка составляет `≈ 58%`. Operational LIVE readiness остается `0%`.

## Правила актуализации

- Файл обновляется при каждом доказанном изменении состояния проекта.
- Проценты меняются только при наличии фактических доказательств.
- Design/contract не считать implementation.
- Implementation не считать integration.
- Integration не считать deployment.
- Deployment не считать production acceptance.
- Canary не считать 72h soak.
- Blocked soak не считать active soak.
- Local commit не считать remote production state.
- Planned module не считать runtime-ready.
- Старое состояние заменять актуальным, не оставляя противоречий.
- Значимые изменения кратко добавлять в changelog.

### Шкала процентов

```text
0–10%   — идея, skeleton или placeholder;
11–25%  — design/contract готов, runtime почти отсутствует;
26–45%  — частичная standalone implementation;
46–65%  — основной функционал реализован, integration/validation неполны;
66–80%  — интегрирован и протестирован, production acceptance не завершен;
81–90%  — deployed и canary validated, остаются hardening gaps;
91–97%  — почти завершен, прошел длительную проверку;
98–100% — полностью завершен в принятом scope, deployed и accepted.
```

Ограничения шкалы:

- 100% использовать крайне редко.
- Skeleton не может быть выше 25%.
- Standalone module без orchestration обычно не выше 45%.
- Deployed без длительного acceptance обычно не выше 90%.
- LIVE module при `LIVE = DISABLED` не считать operationally ready.

## Последние значимые изменения

- Remote production baseline остается `74db6518d2a144fcf8814323c55e4224a71700e9`; local production перед root-cause audit находился на clean descendant `56486039167b0278633f0ef90f05787023807315` (ahead 5, behind 0).
- Freshness retry и observer reliability deployed.
- Semantic observer реализован, интегрирован поверх documentation commit и прошел source validation: focused `26`, combined `65`, orchestrator `57`, full suite `520 passed, 2 skipped`.
- Host-side semantic observer production deployment принят: canary `3783.406 s`, 64/64 samples, 447 heartbeat records, controlled stop, 0 corrupt lines, duplicate identities и false incidents.
- 51/51 blocking incidents независимо подтверждены SQL как истинные `FRESHNESS_DEADLINE_EXCEEDED`; все окна указывают `waiting_timeframes = ["1h"]`.
- Root cause подтвержден: `ContinuousSyncDaemon.sync_expected` не очищает `_pair_errors` после успешной reconciliation, из-за чего 1h остается `DEGRADED` при полной coverage; 45/51 финальных gate snapshots были status-only blockers, первые 6 дополнительно застали позднюю candle.
- Boundary floor, UTC/inclusive semantics, fresh retry reads, strict runtime policy и 180s deadline проверены и не являются дефектом.
- Повторный SOAK-02 заблокирован и не запущен.
- Текущий этап: отдельная авторизация и реализация `ENGINE-MARKET-DATA-RECOVERED-PAIR-HEALTH-RESET-FIX-01`; fix/deploy/canary еще не выполнены.
