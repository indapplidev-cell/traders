# Traders full-cycle Binance → CLOSED PAPER trade latency remediation 01

`FINAL_STATUS = PARTIAL`

`FINAL_VERDICT = PASS` для исправлений wall-clock deadline, bounded readiness/funnel, безопасной конкурентной обработки и детерминированного PostgreSQL lifecycle; `NOT_YET_PROVEN` для post-deploy natural selected→command→OPEN→CLOSED cohort и для снижения полной 20-symbol cycle p50. Поэтому общий аудит не повышен до полного PASS.

Срез: 2026-09-27, production PAPER. Новые 4h/12h funnel не собирались. LIVE не включался. Торговая логика, universe, selector ranking, commission, RR, target, stop, exit policy, TTL и entry window не менялись.

## A. Full lifecycle

Проверенный путь:

```text
Binance public REST
→ continuous market-data ingest
→ 20-symbol 5m analysis
→ selector
→ bounded readiness
→ 1m refinement
→ PAPER command
→ entry fill
→ OPEN
→ position monitor / exit evaluator
→ exit decision
→ close fill
→ CLOSED + net PnL
→ scalping_outcome_diagnostics
```

PostgreSQL E2E на изолированной loopback DB `paper_test_v2`: `4 passed` для `TARGET`, `STOP`, `TIME_EXIT`, `NET_PNL_PROTECTION`. Каждый сценарий проходит command → entry fill → OPEN → evaluation → close fill → CLOSED, сохраняет fees/net PnL и повторно проигрывается exact-once. Load/contention повтор: те же `4 passed` одновременно с 24 production readonly requests, 24/24 HTTP 200.

Production natural smoke не форсировал сделку. После deploy наблюдались полные 20/20 analysis cycles, но нового natural selected winner до command/OPEN/CLOSED в коротком smoke не было. Это основной acceptance gap.

## B. Binance I/O

- Production market-data path — Binance public REST; production WebSocket path отсутствует, поэтому stream lag `NOT_APPLICABLE`.
- Persistent `httpx.Client` и connection reuse уже присутствовали.
- Прямой `/api/v3/time`, один reused client, n=20: p50 `304.4 ms`, p95 `343.5 ms`, max `697.6 ms` (первый TLS/connect sample).
- Market sync изменён с serial due-task execution на bounded pool (`max_workers=4`) при независимых `(symbol,timeframe)` identities.
- После deploy health: 20 symbols, 6 timeframes, 120/120 snapshots `OK`, 0 `last_error`.
- В логах affected services после deploy: 0 HTTP 429, 0 HTTP 5xx, 0 traceback. Rate limit не доказан как bottleneck.

```text
BINANCE_STREAM_LAG_P50_MS = NOT_APPLICABLE_NO_PRODUCTION_STREAM_PATH
BINANCE_STREAM_LAG_P95_MS = NOT_APPLICABLE_NO_PRODUCTION_STREAM_PATH
BINANCE_REST_RTT_P50_MS = 304.4
BINANCE_REST_RTT_P95_MS = 343.5
BINANCE_REST_RTT_MAX_MS = 697.6
```

## C. Entry latency

Production SQL cohort до deploy:

- decision pipeline (`boundary_to_plan_ms`, n=67): p50 `39,444 ms`, p95 `140,122 ms`;
- selector computation: p50 `0.063 ms`, p95 `0.130 ms`;
- selected→claim telemetry содержит две эпохи semantics; актуальные записи с claim раньше финальной selector persistence корректно clamp-ятся в `0 ms`, поэтому единый исторический percentile не является валидным causal latency;
- claim→refinement, recent n=15: p50 `43,809.435 ms`, p95 `99,849.546 ms`;
- required 1m close→refinement: p50 `18,820.184 ms`, p95 `80,816.528 ms`;
- Binance 1m data fetch внутри refinement: p50 `11.222 ms`, p95 `90.445 ms`;
- refinement compute: p50 `1,580.314 ms`, p95 `1,801.126 ms`.

Точный основной claim→refinement bottleneck — ожидание causal required 1m candle плюс continuation polling/queue; REST и refinement compute не объясняют десятки секунд.

Readiness cold profiling до окончательного fix:

- total `16,205.4 ms`;
- PITR/WAL lineage scan `11,975.4 ms`;
- 20-symbol approval read `4,010.6 ms`;
- все остальные компоненты вместе менее `0.2 s`.

После production prewarm + stale-while-revalidate + immediate fail-closed cold/hard-stale:

- первый cold request во время prewarm: `421.9 ms`, fail-closed mutation state;
- после prewarm: runtime/mutation/market/approval true, commission READY 20/20;
- n=20: p50 `178.8 ms`, p95 `669.4 ms`, max `947.0 ms`.

Wall-clock defect исправлен: approval `as_of_ms` используется только для source-data causality; command deadline получает фактический UTC server wall clock. Deadline recheck перед command сохранён.

Исторический production command cohort:

- boundary→command: p50 `30,817 ms`, p95 `40,490 ms` (n=67);
- boundary→position OPEN: p50/p95 `60,000 ms` (n=65, simulation candle boundary);
- command→OPEN: p50 `29,183 ms`, p95 `36,588 ms`, max `39,678 ms`.

Post-deploy natural entry cohort отсутствует; after-values для selected→claim/refinement→command→OPEN остаются `NOT_OBSERVED`.

## D. Open-position monitoring

- Production runtime health: approval watcher, selector и execution worker active; ticks увеличиваются.
- 65/65 historical positions CLOSED, 0 OPEN на reconciliation.
- OPEN→cursor/first-monitor persistence: p50/p95/max `0 ms` (same transaction in current schema).
- Intratrade event→evaluation отдельно от candle boundary не хранится. Историческая exit evaluation использует causal closed 1m candles.
- Holding time не классифицируется как latency defect: p50 `660 s`, p95 `4,920 s`.

## E. Exit latency

Production CLOSED cohort n=65:

- exit signal boundary→decision: p50/p95 `0 ms`;
- decision→fill: p50/p95 `60,000 ms` (configured simulation latency candle, policy не менялась);
- fill→CLOSED: p50/p95 `0 ms`;
- signal→CLOSED: p50/p95 `60,000 ms`;
- CLOSED→PnL persist: `0 ms`, поскольку position close и realized PnL фиксируются одной транзакцией.

PostgreSQL full-cycle exit coverage:

```text
FULL_CYCLE_TARGET_PROFIT_TEST = PASS
FULL_CYCLE_STOP_LOSS_TEST = PASS
FULL_CYCLE_TIME_EXIT_TEST = PASS
FULL_CYCLE_NET_PNL_PROTECTION_TEST = PASS
POSTGRES_FULL_CYCLE_E2E = PASS
DUPLICATE_ENTRY_COMMAND_COUNT = 0
DUPLICATE_EXIT_FILL_COUNT = 0
```

## F. Economics

Production CLOSED cohort n=65:

```text
CLOSED_TRADE_COUNT = 65
WIN_COUNT = 20
LOSS_COUNT = 45
BREAKEVEN_COUNT = 0
GROSS_PNL_TOTAL = -1.025190172600000000
FEES_TOTAL = 10.489307020000000000
SLIPPAGE_TOTAL = NOT_SEPARATELY_PERSISTED
NET_PNL_TOTAL = -11.514497192600000000
NET_PNL_P50 = -0.328255614000000000
NET_PNL_P95 = 0.556566710000000000
NET_RR_P50 = -1.5470242266568070
NET_RR_P95 = 1.9185083323606142
HOLDING_TIME_P50_SEC = 660
HOLDING_TIME_P95_SEC = 4920
MAE_P50_BPS = 15.0521622376
MAE_P95_BPS = 124.7927258699
MFE_P50_BPS = 24.1380167536
MFE_P95_BPS = 99.3861178582
```

Gross рассчитан как persisted net + entry fees + exit fees. Отдельной persisted slippage amount колонка нет, поэтому значение не выдумывалось.

## G. Empirical ingest

Текущий empirical closed-position sink — `scalping_outcome_diagnostics`. Для current schema-era cohort 2026-09-19..20 coverage `12/12`, CLOSED→diagnostic p50/p95/max `0 ms` (same persisted timestamp). Общая historical таблица содержит 13 diagnostics на 65 CLOSED, потому что 52 позиции закрыты до ввода текущего diagnostics path; это не трактуется как post-fix loss.

Prospective calibration collector также `RUNNING`, owner count 1, last_error null, last boundary current; он не заменяет closed-position diagnostics и не используется для выдуманного per-trade latency.

```text
PNL_PERSIST_TO_EMPIRICAL_INGEST_P50_MS = 0_CURRENT_SCHEMA_COHORT
EMPIRICAL_INGEST_ROOT_CAUSE = NO_FOR_CURRENT_SCHEMA_COHORT
```

## H. Root causes

```text
BINANCE_STREAM_ROOT_CAUSE = NOT_APPLICABLE_NO_PRODUCTION_STREAM_PATH
BINANCE_REST_ROOT_CAUSE = NO; measured RTT is sub-second and refinement fetch p95 is 90.445 ms
BINANCE_SERIAL_CALL_ROOT_CAUSE = YES; due tasks were executed serially; bounded pool deployed
RATE_LIMIT_ROOT_CAUSE = NO; no 429/retry evidence after deploy

SERVER_QUEUE_ROOT_CAUSE = PARTIAL; continuation polling and partial-freshness retries contribute
SERVER_CPU_ROOT_CAUSE = NO_PROVEN_CPU_SATURATION
DB_POOL_ROOT_CAUSE = NO_PROVEN_POOL_EXHAUSTION
DB_QUERY_ROOT_CAUSE = YES_FOR_OLD_FUNNEL_AND_COLD_READINESS
EVENT_LOOP_ROOT_CAUSE = NO

20_SYMBOL_CYCLE_ROOT_CAUSE = SERIAL_SYMBOL_COMPUTE_FIXED; PARTIAL_FRESHNESS_BATCH_RETRY_REMAINS
SELECTOR_LATENCY_ROOT_CAUSE = NO; p95 0.130 ms
READINESS_ROOT_CAUSE = PITR_WAL_SCAN_11975_MS_PLUS_20_SYMBOL_APPROVAL_READ_4011_MS
CONTINUATION_LATENCY_ROOT_CAUSE = REQUIRED_1M_CAUSAL_WAIT_PLUS_POLL_QUEUE
ONE_MINUTE_DATA_ROOT_CAUSE = REQUIRED_CLOSED_1M_CANDLE_WAIT; REST_FETCH_NOT_BOTTLENECK
WALL_CLOCK_DEADLINE_ROOT_CAUSE = APPROVAL_AS_OF_WAS_USED_AS_EXECUTION_NOW; FIXED

COMMAND_TO_OPEN_ROOT_CAUSE = ONE_CONFIGURED_SIMULATION_CANDLE
OPEN_POSITION_MONITOR_ROOT_CAUSE = NO
EXIT_DECISION_ROOT_CAUSE = NO
EXIT_FILL_ROOT_CAUSE = ONE_CONFIGURED_SIMULATION_CANDLE
CLOSED_PNL_PERSIST_ROOT_CAUSE = NO; SAME_TRANSACTION
EMPIRICAL_INGEST_ROOT_CAUSE = NO_FOR_CURRENT_SCHEMA_COHORT
```

## I. Before/after latency

| Metric | Before | After | Verdict |
|---|---:|---:|---|
| Readiness observed cold/max | 13,517–17,964 ms | 421.9 ms fail-closed cold | improved |
| Readiness warm p50/p95/max | not bounded | 178.8 / 669.4 / 947.0 ms | target met |
| Funnel cold | 42,215 ms / HTTP 500 in prior evidence | 3,621 ms first compact build | improved, cold >1 s |
| Funnel warm p50/p95/max | 2,265–3,066 ms cached prior | 472.9 / 750.8 / 977.6 ms under active load | improved |
| Per-symbol analysis p50/p95/max | 732 / 8,367 / 10,937 ms (n=100) | 2,011 / 5,271 / 6,041 ms (n=60) | p95/max improved, p50 regressed |
| Full 20-symbol compute p50/p95/max | 13,300 / 17,753 / 17,753 ms (5 cycles) | 18,842 / 38,742 / 38,742 ms (3 cycles) | not accepted |
| 09:00 postdeploy first/10th/20th from cycle start | — | 644 / 2,650 / 6,041 ms | bounded compute |
| 09:00 boundary→20th | — | 98,178 ms | dominated by 1h readiness + restart backlog |
| 09:10 boundary→20th | — | 37,957 ms | partial-freshness batching remains |

Конкурентный orchestrator сначала выявил shared pinned SQLAlchemy session race (`Session.add during flush`); production smoke не был принят. Исправление `4f602ef…` сериализует только authoritative owned-session writes, сохраняя concurrent symbol computation. После redeploy: 20/20 cycles complete, owner ACQUIRED, last_error null, 0 SAWarning/traceback.

Полный cycle p50 не улучшился из-за staggered readiness/preflight batches. Это зафиксировано как остаточный blocker, а не скрыто средними per-symbol числами.

## J. Production state

```text
HEALTH = OK
READINESS = READY_AFTER_PREWARM; CURRENT_MUTATION_READY=true
BINANCE_CONNECTIVITY = PASS
MARKET_DATA_FRESHNESS = OK_120_OF_120
COMMISSION_STATUS = READY_20_OF_20
POSITION_MONITOR_STATUS = ACTIVE
EXIT_WORKER_STATUS = ACTIVE
UNIVERSE_SYMBOL_COUNT = 20
ALEMBIC_VERSION = 0035_scalping_v2_ingestion_policy_contract
LIVE_STATE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
NEW_4H_FUNNEL_COLLECTED = NO
NEW_12H_FUNNEL_COLLECTED = NO
```

Deployed revisions at evidence time:

```text
MARKET_DATA_REVISION = UNSET_IMAGE_LABEL; image rebuilt from f6e878d8a010ff4d62305d678cba47851bcecebd
ORCHESTRATOR_REVISION = 4f602eff0e6381252f224cc59955589fc13efe45
OPERATOR_CONTROL_REVISION = f6e878d8a010ff4d62305d678cba47851bcecebd
READONLY_REVISION = 1b2efbc5a11cb1f64d78efcd7386de1592b88d1a
CLIENT_REVISION = NOT_APPLICABLE_NO_CLIENT_CHANGE
```

Hard invariants:

```text
STRATEGY_CHANGED = NO
SELECTOR_RANKING_CHANGED = NO
COMMISSION_POLICY_CHANGED = NO
RR_CHANGED = NO
TARGET_CHANGED = NO
STOP_CHANGED = NO
EXIT_POLICY_CHANGED = NO
NET_PNL_PROTECTION_CHANGED = NO
TRADE_PLAN_TTL_CHANGED = NO
ENTRY_WINDOW_CHANGED = NO
UNIVERSE_CHANGED = NO
MAX_OPEN_CHANGED = NO
MAX_NEW_COMMANDS_CHANGED = NO
TRADE_15M_CHANGED = NO
LIVE_CHANGED = NO
REAL_BINANCE_ORDER_CALLS = 0
```

`CURRENT_BLOCKER = no post-deploy natural selected→command→OPEN→CLOSED sample; full 20-symbol cycle p50/p95 not reduced because partial-freshness batching still staggers the last symbols.`

`NEXT_TASK = optimize/reconcile all-symbol freshness release without weakening causal gates, then obtain a natural post-deploy lifecycle sample during ordinary smoke; do not force a trade.`
