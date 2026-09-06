# Post-connection-loss cost-gate recovery 01

## Verdict

```text
TASK = TRADERS_POST_CONNECTION_LOSS_RECOVERY_AND_COST_GATE_REHYDRATION_01
FINAL_VERDICT = PASS_CURRENT_PAPER_OPERATION_RECOVERED_WITH_BOUNDED_USER_AUTHORIZED_FEE_STUB
ROOT_CAUSE = PROTECTED_USER_AUTHORIZED_COMMISSION_SNAPSHOT_EXPIRED_AFTER_STRICT_24H_TTL
RECONNECT_CAUSALITY = DOCKER_OUTAGE_OVERLAPPED_THE_FAILURE_BUT_DID_NOT_CAUSE_IT
ROOT_CAUSE_FIXED = YES_FOR_CURRENT_PAPER_RUNTIME_AUTOMATIC_BOUNDED_REHYDRATION
REAL_ACCOUNT_COMMISSION_SOURCE = NOT_CONFIGURED_REMAINS_A_FUTURE_OPERATIONS_BLOCKER
```

## Timeline and server truth

The last 5m evaluation carrying the earlier PAPER-authoritative
`USER_AUTHORIZED_STUB` was the 2026-09-05 18:55 UTC boundary. The protected
snapshot's original `fetched_at` was 2026-09-04T19:02:49.337317Z and the
strict TTL was 24 hours. The first diagnostic using the non-authoritative
fallback was the 19:05 UTC boundary and the first systematic
`PAPER_NO_PLAN_NON_AUTHORITATIVE_COMMISSION` rejection was 19:10 UTC.

Docker stopped at approximately 2026-09-05T22:56:26Z and the engine returned
at approximately 22:56:28Z. The corrected 5m runtime started at 23:00:32Z,
processed the 22:55 catch-up boundary without a command, and completed the
first current post-reconnect 23:00 boundary at approximately 23:01:06Z. Thus
the fee failure preceded the Docker outage by almost four hours. PostgreSQL
contained the exact source failure; Readonly and Desktop did not invent it.

## Remediation

- Real Binance account commission snapshots retain the strict 24-hour TTL.
- A protected `USER_AUTHORIZED_STUB` can now be rehydrated only with an
  explicit, bounded `USER_AUTHORIZED_STUB_REHYDRATION_V1` authorization.
- The production authorization is PAPER-only, valid from
  2026-09-06T10:21:12.141185Z through 2026-09-13T10:21:12.141185Z, refreshes
  its watermark every 900 seconds, and still records
  `real_account_data=false` in the protected source.
- Missing, unreadable, invalid or expired authorization remains fail-closed.
  Fee zero, stale fee acceptance and LIVE authority were not introduced.
- Each evaluation rereads the protected source. Source recovery advances the
  generation/watermark and cannot reuse an earlier cost decision.
- Readonly Funnel and exports now expose market, fee, book and cost readiness,
  generation, timestamps, recovery latency and fee watermark.
- RU and EN catalogs contain an exact human reason for
  `PAPER_NO_PLAN_NON_AUTHORITATIVE_COMMISSION`.

## Controlled recovery evidence

The rebuilt 5m container started at 2026-09-06T10:20:30.925843Z. In that same
running container, before authorization, the loader returned
`SNAPSHOT_STALE/False`. After the protected bounded authorization was written,
the same container returned `READY/True`, and its restart count remained zero.
The first natural cost evaluation arrived at 10:25:27.690Z, about 255.5 seconds
after authorization and at the next available natural boundary.

Four natural current boundaries (10:25, 10:30, 10:35 and 10:40 UTC) completed
10/10. Across their 40 exported rows there were zero missing terminal reasons
and zero generic `UNKNOWN/UNAVAILABLE` terminal reasons. Four candidates
needed the recovered economics model:

| Boundary UTC | Symbol | Candidate | Market snapshot suffix | Fee watermark generation | Fee bps round trip | Spread bps | Depth bps | Slippage bps round trip | Total bps | Decision / exact reason |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 10:25 | AVAXUSDT | `shadow-geometry:84a8e83a51880dc1f114` | `...ff1a802` | 1987433 | 20.0 | 1.3060798015 | 0 | 4.0 | 28.3060798 | REJECT / ECONOMIC_GEOMETRY_NOT_FEASIBLE |
| 10:30 | AVAXUSDT | `shadow-geometry:4255fa1fd2799d815c91` | `...d387110` | 1987434 | 20.0 | 1.3060798015 | 0 | 4.0 | 28.3060798 | REJECT / ECONOMIC_GEOMETRY_NOT_FEASIBLE |
| 10:30 | BNBUSDT | `shadow-geometry:389fdd2e70e85a8197f1` | `...06ca5a` | 1987434 | 20.0 | 0.1321396716 | effectively 0 | 4.0 | 27.13213967 | REJECT / ECONOMIC_GEOMETRY_NOT_FEASIBLE |
| 10:40 | BNBUSDT | `shadow-geometry:0a233db84c5626de0fd0` | `...1e5760b` | 1987434 | 20.0 | 0.1321117401 | 0 | 4.0 | 27.13211174 | REJECT / ECONOMIC_GEOMETRY_NOT_FEASIBLE |

All four had `commission_authoritative=true` for PAPER policy,
`fee_source_status=READY`, `book_source_status=READY`,
`market_source_status=READY`, `cost_model_status=READY` and
`connection_generation=1`. The public sources were
`BINANCE_PUBLIC_BOOK_TICKER` and `BINANCE_PUBLIC_MARKET_DATA_DEPTH`; slippage
was the existing bounded 2 bps entry plus 2 bps exit reserve. These were
legitimate cost-aware geometry rejections, not source-unavailable failures.
Acceptance does not require forcing a trade.

The 1h window had 12/12 boundaries and gap 0. The 4h window honestly retained
36 observed boundaries versus 48 expected, gap 12 (35 completed); it was not
backfilled. Historical pre-recovery cost rejects remain in rolling aggregates
until they age out naturally.

## Safety and tests

```text
IMPLEMENTATION_COMMITS = 092d9940480a826fe26be1d950247c5fa4689946,2c819282b25fd2700921a0f1289fbf96557b2142,99192f5a46e3dc650054cf9a3b8a7039efa179ae
FIVE_MIN_IMAGE = sha256:0a289fb9ed58b94fe6f24868e6a427303885c5bbe1220a7d2dfa6aead384b454
FIVE_MIN_SOURCE = 2c819282b25fd2700921a0f1289fbf96557b2142
READONLY_IMAGE = sha256:900bd5b0e5baf12f2b780ad60652336836040d1b9a161cbed9659548eaf7f9c2
READONLY_SOURCE = 99192f5a46e3dc650054cf9a3b8a7039efa179ae
FIFTEEN_MIN_IMAGE = sha256:5632f5c5a6c1c31552d9c1f75271d05f15b2e4440986e4835a11997892376934_UNCHANGED_NOT_RECREATED
ALEMBIC = 0026_scalping_1m_entry_refinement
RECONNECT_TEST = HEALTHY_TO_LOSS_FAIL_CLOSED_TO_RESTORE_NEXT_BOUNDARY_READY_NO_STALE_REPLAY_PASS
PARTIAL_SOURCE_TEST = FEE_READY_DEPTH_DOWN_FAIL_CLOSED_DEPTH_RESTORED_READY_PASS
FOCUSED_SERVER = 87_PASS_PLUS15_PASS_PLUS39_PASS_PLUS15_PASS_16_SKIPPED
CLIENT = 1501_PASS_2_SKIP_3029_SUBTESTS_ONE_TRANSIENT_TCL_INIT_FAILURE_ISOLATED_PASS_PLUS20_FOCUSED_PASS
POSTGRES_PRODUCTION_READ_CORROBORATION = PASS_40_ROWS_4_BOUNDARIES_4_COST_READY_EXACT_DECISIONS
STALE_REPLAY_COMMANDS = 0
DUPLICATE_COMMAND_KEYS = 0
COMMANDS_SINCE_DISCONNECT = 0
PAPER = CONTINUOUS_ARMED_GENERATION12_HEALTHY_CURRENT_MUTATION_READY
ONE_MIN_ENTRY_REFINEMENT_MODE = SHADOW_UNCHANGED
TRADE_15M_BEHAVIOR_CHANGED = NO
TRADE_15M_REGRESSION = PASS
LIVE = DISABLED
REAL_BINANCE_ORDER_API_CALLS = 0
SECRET_OUTPUT = 0
```

The source tree client was restarted as PID 8024 and is responding. Its
generated server-owned RU/EN bootstrap includes the exact commission-source
reason. Native window enumeration was unavailable during final visual
automation, so no trading control was touched; HTTP/export parity and client
tests are the acceptance evidence. The client repository has no configured
remote, so its commits remain local.
