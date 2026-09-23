# Scalping v2 PAPER plan-to-position bridge remediation

Date: 2026-09-23  
Scope: `trade-5m-v2`, PAPER only, `trading-universe-v3`, LIVE disabled.

## Verdict

The regression was an execution bridge defect. Strategy admission reached 11
complete PAPER plans, but the command consumer compared a global fill-policy
record with the per-approval configuration fingerprint. The approval fingerprint
changed when the v3 universe snapshot changed, so compatible plans were rejected.
Two independent lifecycle defects amplified the result: sorted arming scopes
were labelled v2, and the refinement domain value `REJECTED` was written into a
column whose canonical value is `REJECTED_1M`.

No strategy, threshold, selector, budget, cost, universe membership, LIVE
state, or Binance order behavior was changed.

## Exact production forensic set

The audited window is the exact 11 `PAPER_PLAN_READY` rows with boundaries
1789991700000 through 1789999500000. Full immutable IDs remain in
`online_pipeline_results`; the table below records the exact run ID, plan
identity, approval identity, and lifecycle fields needed to reproduce each row.

| boundary | symbol | run_id | plan_id suffix | approval_id | selector | rank | winner | lifecycle | reason | attempts |
|---|---|---|---|---|---:|---:|:---:|---|---|---:|
| 11:55 | WLDUSDT | `orchestrator:e869b71191db4e65b7ded5963ca0b280` | `paper:WLDUSDT:5m:1789991700000:…` | `paper:risk-approval:v1:ee66b770…4312b` | SELECTED | 1 | yes | EXECUTION_FAILED | PAPER_INGESTION_POLICY_MISMATCH | 3 |
| 12:10 | DOGEUSDT | `orchestrator:5039632c8c3841c987d418614b4bfe18` | `paper:DOGEUSDT:5m:1789992600000:…` | `paper:risk-approval:v1:1b749eee…a1bc8f` | SELECTED | 1 | yes | EXPIRED_BEFORE_EXECUTION | EXPIRED_BEFORE_EXECUTION | 5 |
| 12:25 | ETHUSDT | `orchestrator:0214b52831754f33a58ed6018397c835` | `paper:ETHUSDT:5m:1789993500000:…` | `paper:risk-approval:v1:5be77f6c…79ba6` | SELECTED | 1 | yes | EXECUTION_FAILED | PAPER_INGESTION_POLICY_MISMATCH | 8 |
| 12:25 | FILUSDT | `orchestrator:7caa9c422a1940c98b9cbb2c50257fa2` | `paper:FILUSDT:5m:1789993500000:…` | `paper:risk-approval:v1:03d75379…0ae94` | — | — | — | NULL | NULL | 0 |
| 12:25 | SOLUSDT | `orchestrator:3a14af2ae438424b902bd685aa77d2ae` | `paper:SOLUSDT:5m:1789993500000:…` | `paper:risk-approval:v1:4a0646fa…1c114` | NOT_SELECTED | 2 | no | EXPIRED_BEFORE_EXECUTION | EXPIRED_BEFORE_EXECUTION | 0 |
| 13:50 | BTCUSDT | `orchestrator:bfe24d8920d846ce88e3ff19d55a3c03` | `paper:BTCUSDT:5m:1789998600000:…` | `paper:risk-approval:v1:0affad36…54216` | SELECTED | 1 | yes | EXECUTION_FAILED | PAPER_INGESTION_POLICY_MISMATCH | 6 |
| 13:50 | ETHUSDT | `orchestrator:4afd4b0f54b447c8ba2a70dfaf198e0` | `paper:ETHUSDT:5m:1789998600000:…` | `paper:risk-approval:v1:4f39f378…d847b` | — | — | — | NULL | NULL | 0 |
| 13:50 | XLMUSDT | `orchestrator:003c36b03d314747b6d7e92fcce6fd9f` | `paper:XLMUSDT:5m:1789998600000:…` | `paper:risk-approval:v1:2f773000…0de87c` | — | — | — | NULL | NULL | 0 |
| 13:50 | XRPUSDT | `orchestrator:68b5182cf90641d78bda9da0df6ddcdd` | `paper:XRPUSDT:5m:1789998600000:…` | `paper:risk-approval:v1:780a265bdd…2279` | — | — | — | NULL | NULL | 0 |
| 13:55 | BNBUSDT | `orchestrator:63765c4d0d27497d9190833c7c5e0ba9` | `paper:BNBUSDT:5m:1789998900000:…` | `paper:risk-approval:v1:a6c07f35…bf5ec` | SELECTED | 1 | yes | EXECUTION_FAILED | PAPER_INGESTION_POLICY_MISMATCH | 6 |
| 14:05 | BTCUSDT | `orchestrator:ef238b2878a84a42b367bde3cf16ab19` | `paper:BTCUSDT:5m:1789999500000:…` | `paper:risk-approval:v1:1f7ee281…88281` | SELECTED | 1 | yes | EXPIRED_BEFORE_EXECUTION | EXPIRED_BEFORE_EXECUTION | 5 |

The four mismatch rows are WLDUSDT 11:55, ETHUSDT 12:25, BTCUSDT 13:50,
and BNBUSDT 13:55. The three expiry rows are DOGEUSDT 12:10, SOLUSDT
12:25, and BTCUSDT 14:05. The four null projections are FILUSDT 12:25,
ETHUSDT/XLMUSDT/XRPUSDT 13:50.

## Contract diff and call flow

Before: `NaturalFinalApprovalMaterializer` produced an approval snapshot
fingerprint; `PaperCommandIngestionService._validate_policy` used that value as
the expected fingerprint for the global `paper_simulation_policies` row. The
stored row still had the pre-v3 fingerprint `paper:approval-config:v1:786f…`,
while all 11 approvals had `paper:approval-config:v1:8d8de742…`.

After: Scalping v2 uses policy contract version 2 and a deterministic
`paper:simulation-contract:v2:<sha256>` fingerprint derived from the immutable
fill policy fields. Policy identity, version, status, price source, timeframe,
latency, slippage, fee, partial-fill, future-data, conflict policy, and the
contract fingerprint are still compared field by field. Legacy v1 keeps its
approval-bound behavior. The explicit migration is
`0035_scalping_v2_ingestion_policy_contract`.

The runtime path is now:

`FINAL_APPROVAL → online_pipeline_results PAPER_PLAN → deterministic selector →
durable outcome row → versioned ingestion contract → command/order → PAPER fill
→ position`.

Losers are terminalized at selection as `NOT_SELECTED / LOWER_SELECTOR_RANK`.
Expiry no longer overwrites losers. Record/expiry operations lock the outcome
row, making the boundary race deterministic. Refinement domain values are
normalized before persistence (`REJECTED → REJECTED_1M`, etc.).

## Revisions and schema

Before: orchestrator/operator source `d93d3a55e530f134f623aab8d8238b293b7770d8`,
readonly `44f97d3b2e45f677744ab5feceed602e4cf684be`; Alembic
`0034_scalping_universe_v3`. The readonly revision difference was projection
only, but the operator had incompatible policy semantics.

After source changes, operator and readonly must be built from the same commit;
schema head is `0035_scalping_v2_ingestion_policy_contract`. LIVE remains
disabled and no direct command, position, or status mutation was used.

## Validation evidence

Passed focused checks:

- 21 PostgreSQL ingestion tests, including independent approval snapshot and
  fail-closed negative cases.
- deterministic natural PostgreSQL E2E: command, entry fill, one OPEN position,
  readonly projection, exact replay with no duplicate graph.
- continuous Scalping v2 E2E: v3 refinement policy, capacity terminal reason,
  exit path, and retry safety.
- 1,946 readonly/funnel/registry tests passed; one pre-existing source-contract
  test still reports the unrelated `binance` token in the server tree.
- lifecycle-store, i18n, universe-v3 sorted-scope, schema compatibility, and
  desktop generated-bootstrap checks passed.

The 20-symbol quantity-authority regression is parameterized over the complete
`SCALPING_TRADING_UNIVERSE` and remains unchanged; the v3 bridge accepts the
sorted arming snapshot while preserving the exact 20-member universe.

## Readonly, export, and desktop parity

The canonical outcome row remains the source for funnel/API fields
`selector_status`, `plan_terminal_state`, `plan_terminal_reason`, command
status/reason, position status, position-not-open reason, and timestamps. The
readonly schema capability bridge recognizes 0035 with the 0034 shape. The
server catalog and generated desktop bootstrap now map
`PAPER_INGESTION_POLICY_MISMATCH`, `EXPIRED_BEFORE_EXECUTION`,
`LOWER_SELECTOR_RANK`, `MAX_OPEN_POSITIONS_REACHED`, and
`MAX_NEW_COMMANDS_PER_CYCLE_REACHED` to localized text instead of Unknown.

## Deployment and acceptance

Production deployment is limited to the migration, operator-control runtime,
and readonly projection image. No ARM/START/LIVE transition is performed.
Post-deploy checks must record Alembic 0035, component image revisions, health
200 responses for `/api/v1/health`, `/api/v1/paper/readiness`, funnel, analysis,
and universe endpoints, plus zero real Binance order calls. Desktop acceptance
uses the required PID-bound preflight and only read-only navigation of
`План PAPER | 4ч`.

Before: 11 plans, 4 policy mismatches, 3 unexplained expiries, 4 null
projections, 0 commands, 0 positions. After the deterministic E2E: one
compatible plan produced exactly one command, one fill, and one OPEN position;
the replay produced no duplicate command or position. Existing expired rows are
not backdated or manually rewritten.
