DOCUMENT = online_trader.md
DOCUMENT_ROLE = SINGLE_SOURCE_OF_TRUTH_FOR_PROJECT_STATUS
DOCUMENT_SNAPSHOT_TYPE = POST_TASK_PROVEN_STATE
PROJECT = traders-ml

STATUS_AS_OF_COMMIT = e1b5ecb341ad26277a8f3f76b4a1dd8c9fa06ec6
DOCUMENT_REVISION = SELF
DOCUMENT_COMMIT_RESOLUTION = git log -1 --format=%H -- online_trader.md

RECONCILED_AT_UTC = 2026-07-23T03:32:30Z
RECONCILED_BY_TASK = ONLINE-TRADER-SELF-REFERENCE-SAFE-STATUS-FIX-01

REMOTE_PRODUCTION_BASE_AT_RECONCILIATION = 74db6518d2a144fcf8814323c55e4224a71700e9
PUSH_STATE_AT_RECONCILIATION = PRODUCTION_BRANCH_AHEAD_6_BEHIND_0; RECOVERED_PAIR_FIX_LOCAL_ONLY; PUSHED_NO
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
Root cause sticky `_pair_errors` доказан audit commit
`e1b5ecb341ad26277a8f3f76b4a1dd8c9fa06ec6` и исправлен локально в отдельной
ветке commit `0e58513d84d093f699832baef18d53550dac29b2`. Fix имеет PASS regression,
full-suite и local canary evidence, но не интегрирован в production branch,
не deployed и не принят production semantic canary.
```

Повторный 72-часовой soak пока не запущен. Заблокированная попытка
`ONLINE-ORCHESTRATOR-FRESHNESS-RETRY-SOAK-02-20260722T094858Z` не считается
активным soak:

```text
SOAK_START_STATUS = BLOCKED
NEW_72H_SOAK_STARTED = NO
SOAK_02 = BLOCKED_PENDING_FIX_DEPLOYMENT_AND_PRODUCTION_CANARY
```

```text
CURRENT_STAGE = CONTROLLED-DEPLOYMENT-RECOVERED-PAIR-HEALTH-RESET-FIX-01
CURRENT_BLOCKER = fix implemented locally but not production deployed/canary accepted
```

Локальный fix завершен с PASS, но production deployment и production canary не
выполнены. Новый SOAK-02 не разрешен и не запущен.

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
| Docker/deployment | 90% | Текущий production image развернут и сервисы стабильны; recovered-pair fix существует только локально, не pushed и не deployed |
| PostgreSQL/Alembic | 88% | Production DB стабильна; нормализованные trade-lifecycle tables отсутствуют |
| Тесты и аудит | 85% | Focused tests, full suites, canary и evidence packages существуют |
| 72h production acceptance | 45% | Первый soak выявил freshness incidents и observer gaps; повторный soak заблокирован до deployment и production canary локального recovered-pair fix |

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

Основные сервисы и orchestration работают. Retry lifecycle исправлен. Дефект
сброса восстановленного market-data health исправлен и validated локально, но
production deployment и production canary еще не выполнены.

Текущий пробел:

```text
Production branch все еще содержит доказанный sticky `_pair_errors` root cause.
Локальный commit `0e58513d84d093f699832baef18d53550dac29b2` исправляет pair-scoped reset и
имеет PASS tests/local canary evidence, но не является remote production state.
Deployment и production acceptance отсутствуют.
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
Этап 7c. Recovered pair health reset fix          — локально реализован и validated
Этап 7d. Controlled deployment + semantic canary  — текущий этап; не выполнен
Этап 8. Повторный 72h production soak           — заблокирован; не запущен
Этап 9. Trade-plan/execution/position lifecycle — предстоит
Этап 10. Controlled LIVE rollout                — не разрешен
```

## Ближайшая последовательность

```text
CONTROLLED-DEPLOYMENT-RECOVERED-PAIR-HEALTH-RESET-FIX-01
→ production semantic canary без blocking incidents
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
`CONTROLLED-DEPLOYMENT-RECOVERED-PAIR-HEALTH-RESET-FIX-01`.

## Общая оценка

Относительно полноценного безопасного автономного Binance-бота общая
инженерная оценка составляет `≈ 58%`. Operational LIVE readiness остается `0%`.

## Правила актуализации

- Документ является `POST_TASK_PROVEN_STATE`, а не pre-task plan.
- Текущая задача становится completed только после доказанного PASS.
- `CURRENT_STAGE` всегда указывает на следующий фактический этап.
- `STATUS_AS_OF_COMMIT` не является собственным commit документа.
- Фактическая revision документа разрешается командой
  `git log -1 --format=%H -- online_trader.md`.
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

- Введена self-reference-safe status model: `STATUS_AS_OF_COMMIT` описывает
  доказанное состояние проекта, `DOCUMENT_REVISION = SELF`, а фактический commit
  документа определяется через Git.
- `online_trader.md` теперь обновляется последним как post-task snapshot.
- Runtime/project-state commit и documentation reconciliation commit разделены.
- На момент reconciliation remote production base остается
  `74db6518d2a144fcf8814323c55e4224a71700e9`; production branch находится на
  `e1b5ecb341ad26277a8f3f76b4a1dd8c9fa06ec6`, локально ahead 6 / behind 0,
  push в рамках этой задачи не выполнялся.
- Freshness retry и observer reliability deployed.
- Semantic observer реализован, интегрирован поверх documentation commit и прошел source validation: focused `26`, combined `65`, orchestrator `57`, full suite `520 passed, 2 skipped`.
- Host-side semantic observer production deployment принят: canary `3783.406 s`, 64/64 samples, 447 heartbeat records, controlled stop, 0 corrupt lines, duplicate identities и false incidents.
- 51/51 blocking incidents независимо подтверждены SQL как истинные `FRESHNESS_DEADLINE_EXCEEDED`; все окна указывают `waiting_timeframes = ["1h"]`.
- Root cause подтвержден: `ContinuousSyncDaemon.sync_expected` не очищает `_pair_errors` после успешной reconciliation, из-за чего 1h остается `DEGRADED` при полной coverage; 45/51 финальных gate snapshots были status-only blockers, первые 6 дополнительно застали позднюю candle.
- Boundary floor, UTC/inclusive semantics, fresh retry reads, strict runtime policy и 180s deadline проверены и не являются дефектом.
- Повторный SOAK-02 заблокирован и не запущен.
- `ENGINE-MARKET-DATA-RECOVERED-PAIR-HEALTH-RESET-FIX-01` реализован в isolated
  branch: commit `0e58513d84d093f699832baef18d53550dac29b2`, full suite
  `534 passed, 2 skipped` и local canary PASS. Fix не integrated, не pushed,
  не deployed и не принят production canary.
- Текущий этап: `CONTROLLED-DEPLOYMENT-RECOVERED-PAIR-HEALTH-RESET-FIX-01`.
