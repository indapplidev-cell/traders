# TRADERS_SCALPING_V2_PROFITABILITY_REMEDIATION_BLOCK_01_BASELINE

```text
TASK_STATUS = PASS
BLOCK = 01_BASELINE_INVENTORY_ONLY
BASELINE_HEAD = 9a7667137f52af72d8d6fee1fd8d2610b0be3e36
ACTIVE_SCALPING_PROFILE = trade-5m-v2
ACTIVE_RUNTIME_PROFILES = trade-5m-v2,trade-15m-v1
LIVE = DISABLED
PRODUCTION_POLICY_CHANGES = 0
BINANCE_ORDER_API_CALLS = 0
FOCUSED_TESTS = 65_PASS
```

## Authoritative paths before remediation

The current closest thing to a runtime parameter authority is the immutable
`RuntimeProfileParameters` object in
`app/engine_orchestrator/runtime_parameters.py`.  It is constructed from
`TradeSearchProfile` values in `app/engine_orchestrator/trade_profile.py` and a
large set of numeric and string literals in `_runtime_parameters()`.  It is not
loaded from a separately validated, server-owned configuration file.

Runtime profile registration and activation are split across:

- `app/engine_orchestrator/trade_profile.py`: profile enum, profile objects,
  registry and profile resolution;
- `app/engine_orchestrator/runtime_parameters.py`: runtime parameter registry,
  validation and deterministic legacy `parameter_set_id`;
- `app/engine_orchestrator/parallel_profiles.py` and the orchestrator CLI:
  runnable profile construction and scheduler/owner paths;
- `app/engine_paper/production_approval.py`: active execution profile maps and
  final-approval admission;
- `app/engine_paper/scalping_paper_runner.py`: v2 geometry, cost input loading,
  causal opportunity observation and PAPER plan construction;
- `app/engine_paper/scalping_shadow.py` and
  `app/engine_paper/scalping_policy_v2.py`: geometry, cost, RR and empirical
  expectancy admission;
- `app/engine_paper/eligible_approval_ranking.py`, continuous worker and
  operator-control composition: selector, command and position limits;
- `app/engine_paper/entry_refinement.py`: 1m refinement mode, window and
  economics recheck;
- `app/server_api/trading_funnel.py`, `funnel_export.py`, schemas and routes:
  readonly profile/provenance projection.

## Trade-significant parameter inventory

| Domain | Current source(s) | Values/policies observed at baseline | Duplication/conflict risk |
|---|---|---|---|
| Profile authority | `trade_profile.py`, `production_approval.py`, CLI/compose | v2 is active 5m; 15m remains active; v1 remains registered for compatibility | Active sets are repeated in registries, parser choices, schemas and tests. |
| Signal/timeframes | `TradeSearchProfile`, analysis/setup modules | 5m trigger; 1m/5m/15m/1h context; seven Scalping setup families | Setup allowlists are repeated in profile/runtime/risk contracts. |
| Analysis windows | `trade_profile.py`, `_runtime_parameters()` | history, ATR, impulse, structure, decision, confirmation, volume and regime windows | 15m defaults and Scalping values are embedded in Python. |
| Strategy admission | `runtime_parameters.py`, strategy engine | policy id, allowed setup types, shadow thresholds 55/60/65, minimum score 55 for v2 | Thresholds and allowlists are embedded and repeated by tests. |
| Geometry | `runtime_parameters.py`, `scalping_shadow.py` | ATR buffer 0.25; v2 stop envelope 50 bps; minimum target 45 bps; cohort lists | Defaults also exist in dataclass/function signatures and research helpers. |
| RR/expectancy | `trade_profile.py`, `runtime_parameters.py`, `scalping_policy_v2.py` | v2 planned RR floor 0.4; minimum empirical sample 30; static fallback admits when net RR >= 0.4 | `INSUFFICIENT_BUCKET_STATIC_RR_PASS` is explicitly permissive and appears in runtime plus tests. |
| Costs | `runtime_parameters.py`, `scalping_paper_runner.py`, `scalping_shadow.py`, commission snapshot provider | configured 10+10 bps fee fallback, 2+2 bps slippage, public spread/depth, safety margin, max depth impact 20 bps | Dynamic commission is authoritative when present, but numeric fallbacks/defaults and a `2 * (10 + 2)` floor are duplicated. Missing current authority fails v2 admission in the production path. |
| Risk/sizing | `runtime_parameters.py`, `risk_config.py`, `scalping_sizing.py`, continuous authority | risk per trade 10 bps; total open risk 50 bps; v2 max concurrent positions 2 | Limits and paper statistics are split across runtime, risk and continuous components. |
| Selector/capacity | production approval, eligible ranking, controlled runtime/canary | active selector admits one winner; max new commands per cycle is 1 in current continuous PAPER runtime | The command-cycle bound is not owned by the runtime profile parameter object. |
| Validity/fill | profile/runtime parameters, shadow materializer, controlled worker | validity boundaries, v2 entry TTL 30 seconds, price drift 10 bps | TTL and window constants also appear in refinement/observer code. |
| Exit | runtime parameters, `scalping_exit_policy.py` | v2 time stop 15 minutes; adaptive production exit disabled; stop/target policy IDs | Exit horizons/cohorts are embedded in Python. |
| Causal identity | setup detector, `scalping_shadow.py`, opportunity registry | hash of profile/symbol/direction/setup/structural anchors; re-entry disabled | There are multiple identity builders and an in-memory observation/claim path; persistence/reset provenance is incomplete. |
| 1m refinement | `entry_refinement.py`, environment variable, composition | default SHADOW; next-5m/approval-validity window; price drift/spread/net-edge/RR policy object | Mode is environment-owned and numerical policy values are assembled outside one central config. |
| Commission freshness | commission snapshot repository/loader and runner | dynamic protected snapshot with validity/freshness metadata; bounded paper stub may be used only under explicit authorization | Freshness/source/fallback policy is not expressed in one versioned trade parameter document. |

Business literals remain in `runtime_parameters.py`, `pipeline_runner.py`,
`scalping_shadow.py`, `scalping_policy_v2.py`, `scalping_paper_runner.py`,
`entry_refinement.py`, continuous/controlled PAPER composition, risk/sizing,
exit policy, observation/research scripts and their fixtures.  Mathematical
constants, protocol intervals, enum/status values and historical compatibility
identifiers are not candidates for parameter centralisation.

## Legacy `trade-5m-v1` inventory

Excluding `online_trader.md`, historical audit documents, reports, artifacts and
Git internals, the baseline search found 201 textual references across 52
files.  Runtime-capable references exist in:

- migrations 0017/0018/0021 (historical schema/data compatibility);
- `app/engine_orchestrator/trade_profile.py` and
  `runtime_parameters.py` (registered supported profile);
- setup, Scalping shadow/runner, observation calibration and server API/export
  code paths;
- legacy operator/research scripts and active API schema choices;
- legacy v1-specific fixtures and tests.

Historical persisted values and migrations must remain readable.  Block 02
must remove v1 from every new-candidate, approval, selector, command and
position creation path while retaining explicit readonly legacy handling.

## `trade-15m-v1` activation inventory

Excluding the same historical/status material, the baseline search found 87
references across 36 files.  New 15m work can currently enter through:

- the registered trade/runtime profile and orchestrator profile daemon;
- CLI/default profile selections and Docker/operations startup configuration;
- `ACTIVE_RUNTIME_PROFILE_IDS` and execution profile maps;
- final approval, selector and PAPER routing allowed-profile checks;
- API defaults and dual-profile readonly projections.

Block 03 must turn off scheduling, generation, approval, selector and PAPER
execution while preserving strategy mathematics and readonly historical data.

## Proven baseline defects and constraints

1. No single YAML-equivalent server-owned trade parameter authority exists.
2. `evaluate_expectancy()` admits insufficient buckets through static net RR
   and emits `INSUFFICIENT_BUCKET_STATIC_RR_PASS`.
3. The empirical bucket is a flat raw wins/sample input, not a hierarchical,
   shrunk, confidence-bounded probability with provenance.
4. Required RR is a global static floor rather than a function of conservative
   win probability and positive after-cost EV.
5. Adverse fill uncertainty is not an explicit separately projected reserve.
6. Causal opportunity identity exists, but durable one-execution/reset evidence
   and duplicate provenance are incomplete.
7. Closed PAPER performance lacks the complete requested MAE/MFE and
   stop/target diagnostic contract.
8. 1m is SHADOW, but mode and thresholds are not owned by one central config and
   terminal naming/timeout invariants require reconciliation.

## Validation

Command:

```text
python -m pytest -q tests/test_scalping_v2_production_authority.py tests/test_scalping_independent_profile_v2.py tests/test_5m_scalping_geometry_quota_cost_remediation.py tests/engine_paper/test_entry_refinement.py
```

Result: `65 passed in 10.94s`.  A Windows pytest temporary-directory cleanup
warning was emitted after success; it did not alter project state or test
results.

```text
FINAL_VERDICT = PASS_BASELINE_INVENTORY_COMPLETE_NO_POLICY_CHANGE
NEXT_BLOCK = 02_REMOVE_SCALPING_V1_RUNTIME_AND_ACTIVE_POLICY_PATHS
```
