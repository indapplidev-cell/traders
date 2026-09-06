# Scalping v2 integrated profitability pipeline — deployment evidence

- Reconciled at (UTC): `2026-09-06T17:42:16Z`
- Deployed source commit: `59b4d993433d1908739bd0464f3f34fc30908f22`
- Active PAPER profile: `trade-5m-v2`
- Legacy 15m container: `STOPPED` (`Exited (0)`)
- LIVE allowed: `false`
- Production schema head: `0028_scalping_profitability_grants`
- Authoritative config: `config/trading/trade_parameters.yaml`
- Config schema/hash: `1` / `cd3d340faad52fc2301b4b09953b58dad0865073bb4d0b2b4bb547ee86a5afb0`
- Runtime config hash match: `PASS` (host, worker startup and readonly funnel)
- Readonly health/readiness/funnel: `PASS` (`OK`, `READY`, `trade-5m-v2`, `CURRENT`)
- Continuous PAPER control: `CONTINUOUS_ARMED`; current mutation remains fail-closed when approval is unavailable
- Real Binance order API calls made by this task: `0`

## Immutable image evidence

- `traders-ml-online-orchestrator-5m:latest`: `sha256:f8c6a7b6995a25bb325806b29f4483d278c473df999e36406cd887173a4726d1`
- `traders-readonly-api:production-readonly-v1`: `sha256:f7fa50405ab1f1b4717cf39c8c92df74281194475f766f960b74171476f80095`
- `traders-operator-control-api:production-v1`: `sha256:c3ee14579f8064d54c572550d017f9027ca59dda212d5a44b73e0e09e211f44e`
- All three image revision labels equal the deployed source commit.
- The running container image IDs equal the listed immutable image IDs.

## Database least privilege

- `traders_readonly_api`: `SELECT` on `scalping_opportunities` and
  `scalping_outcome_diagnostics`; no `INSERT` on diagnostics.
- `traders_paper_runtime`: `SELECT, INSERT, UPDATE` on
  `scalping_opportunities`; `SELECT, INSERT` and no `UPDATE` on diagnostics.

## Validation evidence

- Current v2 focused regression: `101 passed`.
- Schema/config guard regression: `57 passed, 7 skipped` (PostgreSQL-only cases skipped in that local invocation).
- Isolated PostgreSQL profitability integration: `3 passed` at schema head `0028`.
- Broader mixed-era scalping selection: `137 passed, 63 failed`; all 63 failures are archived test assumptions around removed `trade-5m-v1`, disabled 15m behavior, plus one pre-existing collector identity assertion. This suite is not represented as PASS.
- Desktop full regression: `1500 passed, 2 skipped, 3029 subtests`; two transient Windows Tcl reads passed on immediate isolated retry.

## Block 12 bounded smoke

- Command: `python -m app.research.scalping_v2_parameter_sweep --config config/research/scalping_v2_parameter_sweep.yaml --max-configs 2 --run-id codex-smoke-20260906-integrated-v2`
- Report: `artifacts/scalping_v2_parameter_sweep/codex-smoke-20260906-integrated-v2/REPORT.md`
- Dataset: bounded production PostgreSQL PAPER outcomes through the readonly role.
- Rows/configurations: `52` / `2`.
- Production command/position/diagnostic counts before and after: `54/53/0` -> `54/53/0`.
- Production mutations: `0`; Binance order API calls: `0`.
- Full parameter sweep run by Codex: `NO`.
