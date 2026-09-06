# TRADERS ETH recovery close — Block 1 evidence

`RECONCILED_AT_UTC = 2026-09-06T22:48:57Z`

## Verdict

```text
BLOCK_1_IMPLEMENTED = YES
BLOCK_1_INTEGRATED = YES
BLOCK_1_DEPLOYED = YES
ETH_POSITION_BEFORE = OPEN
ETH_POSITION_AFTER = CLOSED
RECOVERY_EXIT_FILL = PASS
PAPER_ACCOUNTING = HEALTHY
PAPER_RECONCILIATION = HEALTHY
OPEN_RISK_RELEASED = YES
DIRECT_DB_POSITION_MUTATION = NO
BACKDATED_FAKE_FILL = NO
REAL_BINANCE_ORDER_API_CALLS = 0
LIVE = DISABLED
BLOCK_1_COMMIT = c1d7e7961e22d4aa3a8b17430aa1984c81308417
BLOCK_1_PUSH = PASS
```

## Before-mutation forensic snapshot

- Position: `paper:continuous:position:f4f42f4aded493c0f302b06244d87eaec1d074cbf9f15c978f172b4b655bde41`; command: `paper:ingestion-command:v1:ff773906d215b3d6c7900c2ae480c6db5798952b04d714e9e94014bbb95b5274`.
- Candidate: `paper:production-approval-candidate:v1:3db019fb73c7d7acf281d2ebc5eb87acf0d85ddb9652c2152a5d9441ccd40581`; approval: `paper:risk-approval:v1:617e61db6d0c97c25911b4d17e59bd713b7058769f7bf199c82787c43ae4a3c7`; plan: `paper:ETHUSDT:5m:1788705900000:risk:ETHUSDT:5m:1788705900000:strategy:v2:a6e828fe7c7d54fedb8097af5ef35785b33979dbd39b87ce83a5d427381dd27c:1f17ee9a1885e33d:fad6dcc93787b759`.
- `causal_opportunity_id = UNKNOWN_NOT_PERSISTED_FOR_THIS_LEGACY_TRADE` (no matching `scalping_opportunities` row; no value invented).
- `ETHUSDT SHORT`, OPEN, entry `2484.682964`, opened `2026-09-06T14:46:00Z`, stop `2497.31145834`, target `2460.92`, quantity `0.0361`, used capital `89.6970550004 USDT`, entry fee `0.08969706 USDT`.
- Before accounting: balance `89.71783993 USDT`, closed trades `52`; global active positions `1`, portfolio slot `1/1` occupied.
- Exit cursor before recovery: boundary `1788713820000`, version `131`.
- First provable stop breach: closed 1m REST candle opened `2026-09-06T18:31:00Z` (`open=2496.40 high=2497.44 low=2496.19 close=2496.92`), whose high exceeded the persisted SHORT stop.
- Current commission authority at action: real Binance account snapshot `binance:account-commission:f4f716f36c7132d461e36d86753300379189c0a92caa94e7c7aff72c3eae8ace`, fetched `2026-09-06T21:58:43.837565Z`, ETH effective exit commission `7.5 bps`, BNB discount enabled.

## Root cause

`ROOT_CAUSE = CONFIRMED`.

The persisted OPEN position, stop/target and cursor survived restart and market data was fresh. The production lifecycle worker evaluated the entry-readiness aggregate before every lifecycle stage. `approval_source_adapter_ready=false` / `APPROVAL_SOURCE_NOT_READY` is valid for admission of a new trade, but it incorrectly suppressed exit evaluation of an already OPEN position. The cursor therefore froze at `16:57Z`; the later correct SHORT comparison never ran against the `18:31Z` breach. During recovery, a second boundedness defect was confirmed (`PAPER_EXIT_WINDOW_TOO_LARGE`) after more than 64 missed candles; recovery now advances contiguous history in atomic windows of at most 64 while reserving the special decision for the current causal boundary.

## Canonical recovery result

- Authenticated action: `POST /control/v1/recovery-close-paper-position`, request `eth-recovery-close-20260906-01`, exact profile `trade-5m-v2` and exact position identity.
- Decision: `OPERATOR_RECOVERY_CLOSE`; reason: `PAPER_EXIT_OPERATOR_RECOVERY_CLOSE_AFTER_MISSED_STOP`; decision boundary `1788734040000`, decision price `2502.55`, decided `2026-09-06T22:18:00Z`.
- Fill: `paper:fill-id:v2:4dda379248fafa9ce89112f3ad23409ca1a41b8ec101fd2fb735a3d389c7976d`; current causal next-candle fill boundary `1788734100000`; filled `2026-09-06T22:35:00Z`; adverse 2 bps price `2503.05051`; quantity `0.0361`; fee `0.06777010 USDT`; fee authority `fee:binance-account:a4b988de39b04ffa:v1` (7.5 bps).
- Missed-stop distance at recovery decision: `20.9767253600 bps`; delay from first provable breach to decision: `13620 s`; delay to actual fill: `14640 s`. Financial close was not backdated.
- Final trade: gross PnL `-0.6630684106`, total fees `0.15746716`, net PnL `-0.8205355706`, balance `88.8973043594`, closed trades `53`, active positions `0`.
- Exact SQL cardinality after replay: one exit decision, one exit fill, zero OPEN/CLOSING positions. Replaying the same request returns HTTP 200 with `executed=false`, CLOSED→CLOSED and the same fill identity.
- Readonly: exact position HTTP 200 CLOSED; report HTTP 200 with recovery reason; account and reconciliation HTTP 200 HEALTHY; runtime lifecycle COMPLETED; LIVE false.
- Desktop source was not changed. A direct Desktop capture was attempted through the mandated Computer Use workflow, but Windows Graphics Capture returned `SetIsBorderRequired ... 0x80004002` twice. No UI state claim is made from that failed capture; the same Desktop data source is independently proven by the authoritative Readonly responses above.

Human labels are persisted in the server/client localization contract:

- RU: `Позиция закрыта восстановительным PAPER-выходом после пропущенного Stop Loss`.
- EN: `Position closed by a recovery PAPER exit after a missed Stop Loss`.

## Verification and deployment

- Focused no-DB suites: `2266 passed, 7 skipped` before final fee/catch-up refinements; evaluator/lifecycle final focus `285 passed`; fill/order focus `598 passed` excluding explicitly DB-required cases.
- Isolated PostgreSQL 16: recovery reason/service `21 passed`; schema focus `51 passed, 7 skipped`; durable canary lookup `10 passed`; order execution integration `20 passed` and final focused rerun `17 passed`.
- Operator image `sha256:99be71adfdd856c708743da2b3086eee32b2959acb343d3065aa0a4933466ec9`, OCI revision `c1d7e7961e22d4aa3a8b17430aa1984c81308417`, healthy, restart count `0`.
- Production Alembic: `0030_paper_recovery_close`. Worker/Readonly remained schema-compatible and healthy. The disabled 15m service was not recreated.
- Implementation chain: `b25aef2a3d567bbb166a6380db20500a7e43ab91`, `6b8023a7efc7691ae894f955adbed25d7163b36a`, `e59d2ef6e34b59d20cca45f5012a6bcfe725716c`, `62dc82d553b1ec219c67c9fcb1760ec984169c70`, `276708e14ebffe3cf88d32fed2ee883d28bec496`, `65d8c1babb10945757f91bfaaecd701e3dac28b4`, `7a5f473c435124b8b5a67782160c06b308c0ba2c`, `441dd191238ad93f95bd2ea81416fe5d7946510a`, `c1d7e7961e22d4aa3a8b17430aa1984c81308417`; all pushed to `origin/feature/engine-platform`.
