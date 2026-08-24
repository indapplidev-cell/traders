# TRADERS 5m scalping source integration acceptance retry 01

## Verdict and baseline

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_5M_SCALPING_GEOMETRY_RISK_QUOTA_AND_NET_COST_REMEDIATION_01_SOURCE_INTEGRATION_ACCEPTANCE_RETRY_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE

SERVER_HEAD_BEFORE = 8cb18957c97b6e63db744c40c9da2daa4b722917
SERVER_TREE_BEFORE = 7d7bd4762d7b8dc39974e36e74880a3ddee15554
SERVER_ROOT_CLEAN_BEFORE = YES
DESKTOP_HEAD_BEFORE = 1aa8194740760f6011813b8f7aed44929aa82f5b
DESKTOP_TREE_BEFORE = 2d99d4f1dcb1bd091e21fb4f62be8fb1e3b3c614
DESKTOP_ROOT_CLEAN_BEFORE = YES
MOBILE_HEAD_BEFORE = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
MOBILE_TREE_BEFORE = f791937049c431725718b4a26ce7e23b2a3ea4ec
MOBILE_ROOT_CLEAN_BEFORE = YES
PRODUCTION_ALEMBIC_HEAD_BEFORE = 0018_promote_5m_production_search
PRODUCTION_ALEMBIC_HEAD_AFTER = 0018_promote_5m_production_search
```

Production RR remains 1.5. No tuning, execution-authority expansion, Control or
LIVE mutation, schema change, push, whole-stack restart, private Binance use or
order call occurred.

## WAL/PITR/ACK

```text
WAL_READY_BEFORE = true
WAL_READY_AFTER = true
PITR_READY_BEFORE = true
PITR_READY_AFTER = true
ACTIVE_UNRESOLVED_FAILURES_BEFORE = 0
ACTIVE_UNRESOLVED_FAILURES_AFTER = 0
EXPORT_BACKLOG_BEFORE = 0
EXPORT_BACKLOG_AFTER = 0
PENDING_ARCHIVE_STATUS_BEFORE = 0
PENDING_ARCHIVE_STATUS_AFTER = 0
LINEAGE_VALID_AFTER = true
PHYSICAL_WAL_GAP_AFTER = false
BASE_BACKUP_CHAIN_CONTIGUOUS_AFTER = true
ACK_OWNER_PROCESS_IDENTITY_MATCH_AFTER = true
ACK_OWNER_HEARTBEAT_HEALTH_AFTER = PASS
ACK_OWNER_AFTER = PID4912_python_C:\Program Files\Python311\python.exe
ACK_STATE_AFTER = RUNNING_ERROR_NONE_HEARTBEAT_AGE_2.241S
```

The pre-check at `2026-08-24T17:35:06Z` had archive coverage 1164,
archived count 146 and continuous PITR window 1,157,470 seconds. The post-check
at `2026-08-24T18:16:11Z` had coverage 1167, archived count 149 and window
1,160,168 seconds. Both had zero missing required/source-recoverable segments.

## Source inventory and runtime identity

```text
5M_REMEDIATION_SOURCE_INVENTORY_COMPLETE = YES
SOURCE_IMPLEMENTATION_COMMITS = 9edcbc8e0b0c0b38bf15426deb0bc78e749fef3f,18831fd62e3fef6a3dc9e73a7b746ac98afe8176
SOURCE_INTEGRATION_COMMITS = d1055b6f91d2f77de205c4c3fb61e7c076d2407c,6650f5f13e03342613518584633c90b020e945ed
DESKTOP_I18N_COMMIT = 1aa8194740760f6011813b8f7aed44929aa82f5b
SOURCE_RUNTIME_IDENTITY_MATCH = YES_FILE_SHA256_EXACT
FINAL_5M_SOURCE_COMMIT = 6650f5f13e03342613518584633c90b020e945ed
FINAL_5M_IMAGE = sha256:b3928a801238a21032fa53e1d34fde02a6036e902b41d23182a05aea5e00bee8
FINAL_5M_CONTAINER = bce201e45c5d0e4ba75686a77f6e18c8cb1e55696d2828b1e5f72a76b43104e5
FINAL_5M_RESTART_COUNT = 0
```

- Risk quota: `risk_limits.py`, `risk_context.py`, `risk_policy.py`,
  `execution_budget.py`.
- Geometry, hierarchy, economics, cohorts and rejected diagnostics:
  `app/engine_paper/scalping_shadow.py`.
- Production 5m adapter: `app/engine_paper/scalping_paper_runner.py`.
- Profile-only wiring: `app/engine_orchestrator/pipeline_runner.py`.
- Public data: `app/engine_market_data/binance_public_rest.py`.
- Reasons/i18n: `paper_reason_codes.py`, `risk_reason_codes.py`,
  `app/i18n/catalog.py` and desktop generated bootstrap.
- Matrix/tests: `run_5m_scalping_shadow_matrix.py`, focused remediation and
  5m runtime owner tests.

## Current 5m stage loss

Fresh bounded rolling-four-hour SQL before integration:

```text
CURRENT_5M_STAGE_LOSS_MATRIX_COMPLETE = YES_RAW_SQL_CORROBORATED
CURRENT_5M_ANALYSES = 480
CURRENT_5M_STRUCTURAL_SETUPS = 27
CURRENT_5M_STRATEGY_ADMITTED = 4
CURRENT_5M_RISK_ADMITTED = 4
CURRENT_5M_GEOMETRY_VALID = 0
CURRENT_5M_COST_GATE_PASS = 0
CURRENT_5M_PAPER_PLANS = 0
CURRENT_5M_FINAL_APPROVALS = 0
DEEPEST_REASONS = 453_NO_SETUP_23_STRATEGY_REJECT_4_MISSING_CAUSAL_LEVELS_AND_TARGET
```

The accepted three-boundary post-final sample was `30 -> 0 -> 0 -> 0 -> 0 ->
0 -> 0 -> 0`: every row was NO_SETUP, so geometry/cost calls were correctly not
made. It does not replace the rolling baseline.

## Risk, geometry, target, cost and rejection contracts

```text
RISK_QUOTA_CONSUMPTION_STAGE_AFTER = VALID_PLAN_THEN_EXISTING_FINAL_APPROVAL_QUANTITY_AND_RISK_AUTHORITY
PROFILE_RESEARCH_COUNTERS_SEPARATE = YES
GLOBAL_ACCOUNT_RISK_AUTHORITY_SHARED = YES
RISK_BUDGET_RESERVATION_LEAKS = 0
5M_ATR_BUFFER_COHORTS = 0.25_0.50_0.75_1.00
5M_STOP_ENVELOPE_COHORTS = 0.50%_0.65%_0.80%
PRODUCTION_5M_ATR_BUFFER = 0.25
PRODUCTION_5M_STOP_ENVELOPE = 0.80%
STOP_CLIPPED_INSIDE_CAUSAL_INVALIDATION = NO
CAUSAL_STOP_TOO_WIDE_REASON_IMPLEMENTED = YES
5M_TARGET_HIERARCHY = LOCAL_5M_THEN_VALIDATED_STRUCTURAL_THEN_RELEVANT_ACHIEVABLE_HIGHER_TF
5M_TARGET_FUTURE_LEAKAGE = 0
FEE_SOURCE = CONFIGURED_CONSERVATIVE_FEE_ASSUMPTION_NOT_AUTHORITATIVE
SPREAD_SOURCE = BINANCE_PUBLIC_BOOK_TICKER
DEPTH_IMPACT_SOURCE = BINANCE_PUBLIC_MARKET_DATA_DEPTH_BOUNDED_VWAP_LIMIT100
MISSING_SPREAD_FAILS_CLOSED = YES
ECONOMIC_GATE_ENABLED = YES
EXPECTED_NET_EDGE_COMPUTED = YES
GROSS_RR_COMPUTED = YES
NET_RR_COMPUTED = YES
BREAK_EVEN_WIN_RATE_COMPUTED = YES
RR_COHORTS = 1.00_1.20_1.50_SHADOW
PRODUCTION_5M_MIN_RR_CHANGED_BY_TASK = NO_REMAINS_1.5
REJECTED_GEOMETRY_DIAGNOSTICS_PRESERVED = YES
RAW_RR_PRESERVED_ON_REJECT = YES_WHEN_CAUSALLY_COMPUTABLE
STOP_DISTANCE_PRESERVED_ON_REJECT = YES
TARGET_DISTANCE_PRESERVED_ON_REJECT = YES_WHEN_CAUSALLY_COMPUTABLE
COST_COMPONENTS_PRESERVED_ON_REJECT = YES_KNOWN_CONFIG_NULL_UNKNOWN_MARKET
REJECTION_REASON_PRESERVED = YES_RAW_MACHINE_CODE
UNKNOWN_EQUALS_ZERO = NO
```

The existing approved `BinancePublicRestClient` is reused. There are zero cost
requests before valid geometry and at most two after it: public book ticker and
bounded depth. A source probe passed all ten symbols.

The first rollout boundary found a narrow diagnostics omission: stop-wide rows
had geometry but not already-known fixed fee/slippage/safety fields. Commit
`6650f5f...` initialized those values before early rejection and added tests;
spread/depth remain null when not requested. This exact root cause authorized
the second and final replacement. No redeploy loop occurred.

## Deterministic matrix and same-data proof

Dataset `DETERMINISTIC_CAUSAL_5M_FIXTURES_V1`: eight candidates, 108
configurations (4 ATR x 3 envelope x 3 target diagnostic x 3 RR), no execution.
Target diagnostics 45/60/80 bps classify only and never synthesize targets.

| ATR | Env | Geometry | Wide | Missing | Cost | Gross RR 1/1.2/1.5 | Net RR 1/1.2/1.5 | Valid |
|---:|---:|---:|---:|---:|---:|---|---|---:|
| .25 | 50 | 3 | 3 | 2 | 2 | 2/2/2 | 1/1/0 | 0 |
| .25 | 65 | 4 | 2 | 2 | 3 | 3/3/3 | 2/2/1 | 1 |
| .25 | 80 | 5 | 1 | 2 | 4 | 4/4/4 | 2/2/1 | 1 |
| .50 | 50 | 2 | 4 | 2 | 1 | 1/1/1 | 1/1/0 | 0 |
| .50 | 65 | 4 | 2 | 2 | 3 | 3/3/3 | 2/2/1 | 1 |
| .50 | 80 | 5 | 1 | 2 | 4 | 4/4/4 | 2/2/1 | 1 |
| .75 | 50 | 2 | 4 | 2 | 1 | 1/1/1 | 1/1/0 | 0 |
| .75 | 65 | 4 | 2 | 2 | 3 | 3/3/3 | 2/2/1 | 1 |
| .75 | 80 | 5 | 1 | 2 | 4 | 4/4/4 | 2/2/1 | 1 |
| 1.00 | 50 | 2 | 4 | 2 | 1 | 1/1/1 | 1/1/0 | 0 |
| 1.00 | 65 | 3 | 3 | 2 | 2 | 2/2/2 | 1/1/0 | 0 |
| 1.00 | 80 | 5 | 1 | 2 | 4 | 4/4/3 | 2/2/0 | 0 |

```text
OLD_GEOMETRY_RR_1_2_PASS_COUNT = 5
NEW_GEOMETRY_RR_1_2_PASS_COUNT = 4
NEW_GEOMETRY_NET_COST_PASS_COUNT = 4
CONFIGURATION_SELECTED_BY_SIGNAL_COUNT = NO
```

Detailed medians/P90 are unchanged from the source-remediation audit; the
primary `.25/80/45` medians are stop 42.5 bps, P90 stop 83.75, target 110,
gross RR 2.0833, net RR 1.1375, net edge 79 bps and break-even 0.4751.

## Natural concurrency, performance and behavior

```text
5M_NATURAL_BOUNDARIES_OBSERVED = 3_FINAL_PLUS_1_EXCLUDED_PRE_FIX
TRADE_5M_SEARCH_CONTINUITY = PASS
TRADE_15M_SEARCH_CONTINUITY = PASS
5M_SINGLETON_OWNER_COUNT = 1
5M_15M_DEDUPE_COLLISION = 0
5M_15M_CURSOR_COLLISION = 0
5M_RUNTIME_REPLACEMENT_COUNT = 2
TRADE_5M_RUNTIME_STOPPED_BY_TASK = TRANSIENT_RECREATE_ONLY_NO_MISSING_BOUNDARY
TRADE_5M_RUNTIME_RESTARTED_BY_TASK = YES_BOUNDED_ONLY
TRADE_15M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
TRADE_5M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = YES_INTENDED_ADMISSION_ONLY
```

| 5m boundary | rows/symbols/run IDs/completed/errors | min/median/max ms |
|---:|---|---:|
| 1787594700000 | 10/10/10/10/0 | 90/103.5/122 |
| 1787595000000 | 10/10/10/10/0 | 90/130/200 |
| 1787595300000 | 10/10/10/10/0 | 87/91/163 |

At `1787595300000`, 15m simultaneously produced exact10 with ten distinct run
IDs and 145/178/265 ms min/median/max. 5m produced exact10 with 87/91/163 ms.
The 15m container `8f966246...`, image `sha256:09ac8432...`, start time and
restart count remained unchanged.

```text
5M_BASELINE_4H_LATENCY_MEDIAN_P90_MS = 95_133.1
5M_POST_ACCEPTANCE_LATENCY_MAX_MS = 200
15M_BASELINE_4H_LATENCY_MEDIAN_P90_MS = 169.5_1202.8
15M_POST_CONCURRENT_BOUNDARY_MEDIAN_MAX_MS = 178_265
15M_LATENCY_MATERIAL_REGRESSION = NO
DB_QUERY_COUNT_BEFORE_AFTER = 4_4_PER_5M_SYMBOL_SNAPSHOT_BUILD
5M_COST_DATA_QUERY_BOUNDED = YES_0_BEFORE_GEOMETRY_MAX2_AFTER
NEW_N_PLUS_ONE = NO
PRODUCTION_CONTROL_MUTATIONS_BY_TASK = 0
BINANCE_ORDER_API_CALLS_BY_TASK = 0
LIVE_MODE_CHANGED_BY_TASK = NO
```

Business counts stayed commands/orders/fills/positions/journal `0/0/0/0/0`.
The canary stayed `NO_ELIGIBLE_APPROVAL`, generation 6, command 0, position 0.

## Tests, i18n, security and ownership

```text
CHANGED_PATH_REGRESSION_FAILURES = 0
5M_QUOTA_TESTS = PASS
5M_GEOMETRY_TESTS = PASS
5M_TARGET_TESTS = PASS
5M_COST_GATE_TESTS = PASS
5M_RR_COHORT_TESTS = PASS
5M_REJECTED_DIAGNOSTICS_TESTS = PASS
15M_NON_REGRESSION = PASS
SERVER_IMPACTED_REGRESSION = 177_PASSED_5_SKIPPED
COMPILEALL = PASS
DESKTOP_REGRESSION = 1454_PASSED_2_SKIPPED_3029_SUBTESTS
MOBILE_REGRESSION = GRADLE_TEST_BUILD_SUCCESSFUL
SECURITY_SCANNER = 686_PASSED_10_SKIPPED
SERVER_I18N_AUTHORITY_PRESERVED = YES
NEW_REASON_CODE_I18N_COVERAGE = PASS_RU_EN_KEY_AND_PLACEHOLDER_PARITY
SECRET_OUTPUT_BY_TASK = 0
PROTECTED_SECRET_VALUE_OUTPUT = 0
NEW_SECURITY_FINDINGS = 0
```

Current full server: `30677 passed, 30 skipped, 439 failed, 342 errors`.
All 781 non-passes reproduce the pre-existing stale historical/schema guards or
missing opt-in PostgreSQL URLs. None is in changed 5m/risk/PAPER/cost/i18n or
runtime paths; final focused paths were rerun green.

```text
SERVER_COMMITS = 9edcbc8e,18831fd6,d1055b6f,6650f5f1,PROJECT_STATE_AUDIT,ONLINE_TRADER_RECONCILIATION
DESKTOP_COMMITS = 1aa81947_PREEXISTING_REMEDIATION_I18N
MOBILE_COMMITS = NONE
PUSHED = NO
NEXT_ACTION = TRADERS_5M_SCALPING_PRODUCTION_OBSERVATION_AND_CALIBRATION_BASELINE_01
```
