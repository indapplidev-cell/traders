DOCUMENT = online_trader.md
DOCUMENT_ROLE = SINGLE_SOURCE_OF_TRUTH_FOR_PROJECT_STATUS
PROJECT = traders-ml
UPDATED_AT_UTC = 2026-07-22T15:25:19Z
UPDATED_BY_TASK = ONLINE-TRADER-STATUS-AND-AGENTS-SYNC-01
BASE_COMMIT = 74db6518d2a144fcf8814323c55e4224a71700e9
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
observer технически надежен, но пока не имеет принятого и развернутого
semantic monitoring для runs, results, candles, freshness lifecycle
и acceptance-impact incidents.
```

Повторный 72-часовой soak пока не запущен. Заблокированная попытка
`ONLINE-ORCHESTRATOR-FRESHNESS-RETRY-SOAK-02-20260722T094858Z` не считается
активным soak:

```text
SOAK_START_STATUS = BLOCKED
NEW_72H_SOAK_STARTED = NO
```

Текущий этап: `ONLINE-ORCHESTRATOR-SEMANTIC-MONITORING-OBSERVER-01`.

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
| Semantic observer | 15% | Контракт и задача подготовлены; реализация, deployment и canary не завершены |
| Docker/deployment | 90% | Production image развернут, сервисы стабильны, Git checkpoint и remote push завершены |
| PostgreSQL/Alembic | 88% | Production DB стабильна; нормализованные trade-lifecycle tables отсутствуют |
| Тесты и аудит | 85% | Focused tests, full suites, canary и evidence packages существуют |
| 72h production acceptance | 45% | Первый soak выявил freshness incidents и observer gaps; повторный soak ожидает semantic observer |

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

Основные сервисы и orchestration работают. Freshness defect исправлен.

Текущий пробел:

```text
observer подтверждает, что процесс жив,
но semantic observer для доказательства корректности каждого
business window еще не принят и не развернут.
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

Semantic observer еще не реализован, заблокированный SOAK-02 не является
production acceptance, а `engine_trade_plan` и последующие lifecycle-модули не
являются runtime-ready. LIVE execution operationally запрещен.

## Завершенные, текущие и предстоящие этапы

```text
Этап 1. Историческая аналитика                  — завершен
Этап 2. Online market-data и analysis           — почти завершен
Этап 3. Setup → strategy → risk → paper         — реализован
Этап 4. Online orchestrator                     — реализован
Этап 5. Freshness retry hardening               — завершен
Этап 6. Observer process reliability            — завершен технически
Этап 7. Semantic monitoring observer            — текущий этап
Этап 8. Повторный 72h production soak           — ожидает этап 7
Этап 9. Trade-plan/execution/position lifecycle — предстоит
Этап 10. Controlled LIVE rollout                — не разрешен
```

## Ближайшая последовательность

```text
ONLINE-ORCHESTRATOR-SEMANTIC-MONITORING-OBSERVER-01
→ controlled deployment semantic observer
→ production canary
→ новый ONLINE-ORCHESTRATOR-FRESHNESS-RETRY-SOAK-02
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
`ONLINE-ORCHESTRATOR-SEMANTIC-MONITORING-OBSERVER-01`.

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

- Production Git зафиксирован на `74db6518d2a144fcf8814323c55e4224a71700e9` (`74db6518...`).
- Freshness retry и observer reliability deployed.
- Повторный SOAK-02 заблокирован из-за отсутствия semantic monitoring.
- Текущая задача: `ONLINE-ORCHESTRATOR-SEMANTIC-MONITORING-OBSERVER-01`.
