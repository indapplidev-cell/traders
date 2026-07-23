DOCUMENT = online_trader.md
DOCUMENT_ROLE = SINGLE_SOURCE_OF_TRUTH_FOR_PROJECT_STATUS
DOCUMENT_SNAPSHOT_TYPE = POST_TASK_PROVEN_STATE
PROJECT = traders-ml

STATUS_AS_OF_COMMIT = f9d2819ba203d8f5a38ccab57bd727b5b887475c
DOCUMENT_REVISION = SELF
DOCUMENT_COMMIT_RESOLUTION = git log -1 --format=%H -- online_trader.md

RECONCILED_AT_UTC = 2026-07-23T17:21:13Z
RECONCILED_BY_TASK = CONTROLLED-DEPLOYMENT-FAILED-BOUNDARY-PROMPT-RETRY-FIX-01
FILES_CHANGED = online_trader.md

REMOTE_PRODUCTION_BASE_AT_RECONCILIATION = 74db6518d2a144fcf8814323c55e4224a71700e9
PUSH_STATE_AT_RECONCILIATION = NOT_PUSHED
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

Текущий production-hardening статус:

```text
Bounded failed-boundary prompt retry интегрирован exact project-state commit
`f9d2819ba203d8f5a38ccab57bd727b5b887475c`, deployed только в
`market-data-sync` immutable image
`traders-ml:controlled-failed-boundary-prompt-retry-fix-01-f9d2819` и принят
4570-секундным production canary. PostgreSQL и online-orchestrator не
перезапускались; Alembic остался на `0008_engine_orchestrator_freshness_retry`.
```

Повторный 72-часовой soak пока не запущен. Заблокированная попытка
`ONLINE-ORCHESTRATOR-FRESHNESS-RETRY-SOAK-02-20260722T094858Z` не считается
активным soak:

```text
SOAK_START_STATUS = AUTHORIZED_NOT_STARTED
NEW_72H_SOAK_STARTED = NO
SOAK_02_STATUS = AUTHORIZED_NOT_STARTED
```

```text
CURRENT_STAGE = ONLINE-ORCHESTRATOR-FRESHNESS-RETRY-SOAK-02
CURRENT_BLOCKER = NONE_FOR_SOAK_START
```

Production canary пересек две новые 1h boundaries и завершил 15/15 due windows
exactly once: 77 semantic, 76 pair-health, 76 retry samples, 537 heartbeats,
0 blocking incidents и все safety counters 0. Естественного failed-boundary
prompt-retry event не произошло, поэтому production path честно имеет статус
`NO_NATURAL_RETRY_EVENT`; это не утверждение о natural-event PASS.
SOAK-02 разрешен на основании принятого deterministic retry evidence и
production stability canary, но в этой задаче не запускался.

## Общая инженерная оценка

```text
Онлайн-аналитик + paper-контур:      ≈ 82%
Production reliability/acceptance:  ≈ 70%
Полный автономный LIVE-бот:         ≈ 58%
```

Проценты отражают совокупность реализации, интеграции, тестирования,
deployment, production validation и операционной надежности. Они не равны test
coverage, количеству файлов или строк кода.

## Готовность по основным модулям

| Модуль | Готовность | Состояние |
|---|---:|---|
| `engine_market_data` | 96% | REST/WebSocket, closed candles, PostgreSQL, gap recovery, recovered health reset и bounded failed-boundary prompt retry deployed/canary validated; natural production retry event не наблюдался |
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
| Docker/deployment | 91% | Immutable prompt-retry image deployed только в `market-data-sync`; PostgreSQL и orchestrator не перезапускались, remote push не выполнялся |
| PostgreSQL/Alembic | 88% | Production DB стабильна; нормализованные trade-lifecycle tables отсутствуют |
| Тесты и аудит | 87% | Retry focused `31`, combined `286 passed, 2 skipped`, full suite `565 passed, 2 skipped`, compile/import и 4570-секундный production canary PASS |
| 72h production acceptance | 45% | SOAK-02 разрешен, но еще не запущен; canary не является 72h acceptance |

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

### Production reliability — 70%

Основные сервисы и orchestration работают. Retry lifecycle и recovered pair
health reset исправлены. Bounded failed-boundary prompt retry с identity
`(symbol,timeframe,closed_until_ms)`, delays `5/10/20/40`, horizon `170` и
max attempts `4` deployed и production-canary validated.

Оставшийся acceptance gap:

```text
Во время production canary естественного REST exhaustion и failed-boundary
prompt-retry event не произошло. Production stability доказана, deterministic
retry path принят, но natural production event не заявляется как observed.
Следующий этап — новый 72h SOAK-02 с уникальным anchor и полным settlement.
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

Semantic observer, recovered pair health reset и failed-boundary prompt retry
production-deployed и canary-validated. Новый SOAK-02 разрешен, но не запущен и
не является уже пройденным production acceptance.
`engine_trade_plan` и последующие lifecycle-модули не являются runtime-ready.
LIVE execution operationally запрещен.

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
Этап 7c. Recovered pair health reset fix          — реализован и validated
Этап 7d. Controlled deployment + semantic canary  — завершен; PASS
Этап 7e. Failed-boundary prompt retry fix         — реализован и протестирован
Этап 7f. Controlled retry deployment + canary    — завершен; PASS
Этап 8. Повторный 72h production soak           — разрешен; не запущен
Этап 9. Trade-plan/execution/position lifecycle — предстоит
Этап 10. Controlled LIVE rollout                — не разрешен
```

## Ближайшая последовательность

```text
ONLINE-ORCHESTRATOR-FRESHNESS-RETRY-SOAK-02
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
`ONLINE-ORCHESTRATOR-FRESHNESS-RETRY-SOAK-02`.

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
  `74db6518d2a144fcf8814323c55e4224a71700e9`; push в рамках этой задачи не
  выполнялся.
- Freshness retry и observer reliability deployed.
- Semantic observer реализован, интегрирован поверх documentation commit и прошел source validation: focused `26`, combined `65`, orchestrator `57`, full suite `520 passed, 2 skipped`.
- Host-side semantic observer production deployment принят: canary `3783.406 s`, 64/64 samples, 447 heartbeat records, controlled stop, 0 corrupt lines, duplicate identities и false incidents.
- 51/51 blocking incidents независимо подтверждены SQL как истинные `FRESHNESS_DEADLINE_EXCEEDED`; все окна указывают `waiting_timeframes = ["1h"]`.
- Root cause подтвержден: `ContinuousSyncDaemon.sync_expected` не очищает `_pair_errors` после успешной reconciliation, из-за чего 1h остается `DEGRADED` при полной coverage; 45/51 финальных gate snapshots были status-only blockers, первые 6 дополнительно застали позднюю candle.
- Boundary floor, UTC/inclusive semantics, fresh retry reads, strict runtime policy и 180s deadline проверены и не являются дефектом.
- Failed-boundary prompt retry реализован exact project-state commit
  `f9d2819ba203d8f5a38ccab57bd727b5b887475c`: one daemon owner, identity
  `(symbol,timeframe,closed_until_ms)`, delays `5/10/20/40`, horizon `170`,
  max attempts `4`, closed-only guard, startup reconciliation и supersession.
- Full gate повторно принят: focused `31`, continuous-sync `82 passed, 1 skipped`,
  market-data `140 passed, 2 skipped`, orchestrator `81`, observer `65`,
  combined `286 passed, 2 skipped`, full suite `565 passed, 2 skipped`,
  compile/import PASS.
- Immutable image
  `traders-ml:controlled-failed-boundary-prompt-retry-fix-01-f9d2819`
  (`sha256:0bbac2b3982d7c11d2cda0666c944117cfe608879ea05be9ade7a37b445abce5`)
  deployed только в `market-data-sync`; PostgreSQL и orchestrator сохранили
  container identity и restart count 0.
- Production canary принят: `4570.062 s`, 77 semantic samples, 76 pair-health
  samples, 76 retry samples, 537 heartbeats, две 1h boundaries, 15/15 due
  windows completed exactly once и все safety counters 0; controlled stop PASS.
- `PRODUCTION_PROMPT_RETRY_PATH_STATUS = NO_NATURAL_RETRY_EVENT`; artificial
  failure не создавался.
- `SOAK_02_STATUS = AUTHORIZED_NOT_STARTED`; новый 72h soak не запускался.
- `ENGINE-MARKET-DATA-RECOVERED-PAIR-HEALTH-RESET-FIX-01` реализован в isolated
  branch, затем exact runtime/test patch интегрирован project-state commit
  `4c6d779558a6f67056c5c2d7f57b606f3a87b6af`; full suite
  `534 passed, 2 skipped`.
- Immutable image
  `traders-ml:controlled-recovered-pair-health-reset-fix-01-4c6d779`
  deployed только в `market-data-sync`. PostgreSQL и orchestrator сохранили
  container identity и restart count 0.
- Production canary принят: semantic runtime `3723.359 s`, 63/63 successful
  samples, 438 heartbeats; pair-health runtime `3725.954 s`, 368 samples;
  15/15 due windows completed exactly once; 0 skipped/failed/missing,
  false OK, cross-pair clears, hidden errors/gaps, corrupt lines и incidents.
- `PRODUCTION_RECOVERY_PATH_STATUS = NO_NATURAL_RECOVERY_EVENT`; artificial
  failure не создавался.
- Текущий этап: `ONLINE-ORCHESTRATOR-FRESHNESS-RETRY-SOAK-02`.
