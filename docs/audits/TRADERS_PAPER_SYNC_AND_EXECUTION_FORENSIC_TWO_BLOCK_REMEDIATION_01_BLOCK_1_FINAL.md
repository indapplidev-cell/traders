# PAPER sync and execution forensic two-block remediation 01 — Block 1

## Verdict

```text
TASK = TRADERS_PAPER_SYNC_AND_EXECUTION_FORENSIC_TWO_BLOCK_REMEDIATION_01
BLOCK = 1_ONLY
BLOCK_1_TECHNICAL_STATUS = PASS
BLOCK_1_FORMAL_STATUS = BLOCKED_ONLY_BY_ABSENT_TRADERS_CLIENT_GIT_REMOTE
BLOCK_2_STATUS = NOT_STARTED_AWAITING_USER_APPROVAL
FINAL_VERDICT = PASS_IMPLEMENTATION_TEST_DEPLOYMENT_NATURAL_OPEN_AND_HISTORY_SELECTION_CAUSALITY; CLIENT_PUSH_NOT_POSSIBLE_WITHOUT_REMOTE
```

Block 1 reuses the already proven server/read-model/refresh remediation in
`TRADERS_PAPER_EXECUTION_UI_SYNC_AND_REFRESH_LATENCY_FIX_01_FINAL.md` and adds a
new remediation for the user-observed History selection defect. Block 2 was not
started.

## User-observed defect and root cause

Selecting a different History row changed the Treeview selection but retained
the previous row's report until the asynchronous HTTP result arrived. The global
PAPER render gate then suppressed report-only state notifications because the
coherent PAPER snapshot ID had not changed. A concurrent full PAPER refresh could
also apply the canary report after the user selected another historical position.
History selection preservation used displayed close time rather than exact row
identity, which was ambiguous for equal timestamps.

The client now:

- records the exact selected `position_id`;
- clears the prior report in the same Tk event and renders an explicit localized
  loading state;
- uses one superseding async report lane and rejects results whose `position_id`
  is no longer selected;
- prevents a full refresh from overwriting a newer history selection;
- includes report/control identity in the PAPER view render key without changing
  the coherent snapshot identity;
- preserves History selection by exact Treeview IID (`position_id`);
- skips History table reconstruction when its immutable tuple is unchanged;
- keeps report-only repaint telemetry separate from coherent snapshot-render
  telemetry.

Natural Funnel acceptance also exposed three known reason codes that still used
the generic fallback. Authoritative RU/EN catalog entries and the generated
desktop bootstrap now cover `ENTRY_FILL_WINDOW_MISSED`,
`PAPER_POSITION_OPENED`, and `PORTFOLIO_REJECT_TOTAL_OPEN_RISK`.

## Production natural OPEN acceptance

No signal was forced and no production data was mutated for validation. A natural
DOGEUSDT Continuous PAPER position was OPEN during the final production harness.
PostgreSQL, Readonly, Funnel, PAPER, and the real Tk client agreed on its exact
identity.

```text
SYMBOL = DOGEUSDT
BOUNDARY = 1788613500000
CANDIDATE_ID = paper:production-approval-candidate:v1:b77996283e1ff14e202824315561f6222776f37cbe6a484979ee614fc4a9b58e
APPROVAL_ID = paper:risk-approval:v1:7c3e8ea2b1f811681e96c60be19274b0feebd9b528393dbac1a622a1d0fc340e
PLAN_ID = paper:DOGEUSDT:5m:1788613500000:risk:DOGEUSDT:5m:1788613500000:strategy:v2:f2a3da12b34f21f260a627e4a36ac999ed94335a397efa53f25aa7d42a888a1e:c779c463fb980e13:cd99aeb7d3a351c9
COMMAND_ID = paper:ingestion-command:v1:249cd271f3d2da6c21a86c2ad64b91f3d96ab1e2efaeafffeb568f7e2ea419e2
POSITION_ID = paper:continuous:position:96d42ece30f637bf879f80399253e0f6ef8fc2c288a319e064ea6d0f0e9afd6e
SELECTED_AT = 2026-09-05T13:05:30.207446Z
COMMAND_CREATED_AT = 2026-09-05T13:05:29.565Z
POSITION_OPENED_AT = 2026-09-05T13:06:00Z
FUNNEL_READONLY_AND_CLIENT_VISIBLE_AT = 2026-09-05T13:28:08.179022Z
PAPER_READONLY_VISIBLE_AT = 2026-09-05T13:28:22.619763Z
PAPER_CLIENT_RENDERED_AT = 2026-09-05T13:28:22.272181Z
FUNNEL_PAPER_IDENTITY_PARITY = PASS_COMMAND_AND_POSITION
FUNNEL_PAPER_GENERATION_PARITY = PASS_COHERENT_RUNTIME_FENCE
ACTIVE_POSITION_COUNT = 1
PAGE_SWITCH_IMMEDIATE_REFRESH = PASS_DISPATCHED_IMMEDIATELY
PAGE_SWITCH_FETCH_AND_RENDER_MS = 14441.0
PAPER_PROVIDER_MS = 14028
PAPER_RENDER_MS = 15
PAPER_OPEN_VISIBLE_WITHIN_NEXT_HEALTHY_REFRESH = PASS
FUNNEL_OPEN_VISIBLE_WITHIN_NEXT_HEALTHY_REFRESH = PASS
```

The command creation timestamp preceding the outcome's first selected observation
by 642 ms is recorded factually and is not interpreted in Block 1; execution
timing/validity belongs to Block 2.

## History selection production acceptance

Three distinct real closed positions were selected sequentially through the real
Tk main loop and production HTTP provider. Every selection removed the prior
report immediately, rendered the localized loading state, and resolved to the
same exact `position_id`:

```text
ROW_1 = PASS_EXACT_270.4_MS
ROW_2 = PASS_EXACT_204.2_MS
ROW_3 = PASS_EXACT_224.9_MS
IMMEDIATE_LOADING_ALL = PASS
PREVIOUS_REPORT_VISIBLE_AFTER_SELECTION = NO
STALE_RESULT_SUPPRESSION = PASS_FOCUSED_REORDER_TEST
SNAPSHOT_RENDER_TIMESTAMP_PRESERVED_AFTER_REPORT_REPAINT = PASS
```

## Performance and prior Block 1 evidence

The previous accepted measurement remains applicable because this delta does not
change providers or Funnel parsing:

```text
PAPER_PROVIDER_MEDIAN_MS = 15026.0
PAPER_PROVIDER_P95_MS = 15807.9
PAPER_PROVIDER_MAX_MS = 16365.2
PAPER_CURRENT_NATURAL_MS = 14028
PAPER_RENDER_CURRENT_MS = 15
FUNNEL_PROVIDER_MEDIAN_MS = 226.0
FUNNEL_PROVIDER_P95_MS = 302.0
FUNNEL_PROVIDER_MAX_MS = 2091.6
FUNNEL_FULL_RENDER_MEDIAN_MS = 84.998
FUNNEL_FULL_RENDER_P95_MS = 108.407
FUNNEL_FULL_RENDER_MAX_MS = 158.437
FUNNEL_UNCHANGED_NOTIFICATION_MEDIAN_MS = 0.623
PAPER_VIEW_MODEL_BUILD = PROVIDER_RETURNS_IMMUTABLE_DTO_NO_SEPARATE_BUILD_PHASE
FUNNEL_VIEW_MODEL_BUILD = PROVIDER_RETURNS_IMMUTABLE_DTO_NO_SEPARATE_BUILD_PHASE
```

The PAPER History table is no longer rebuilt for report-only changes. The page
watchdog remains 30 seconds, single-flight remains active, timeout releases the
lane, next refresh remains schedulable, and last-good account/history/
reconciliation preservation remains covered by the earlier focused and
PostgreSQL evidence.

## Tests

```text
DESKTOP_FOCUSED_FINAL = 65_PASSED
DESKTOP_I18N_FUNNEL_PAPER = 64_PASSED
DESKTOP_FULL_GREEN_BEFORE_FINAL_TELEMETRY_DELTA = 1500_PASSED_2_SKIPPED_3029_SUBTESTS
DESKTOP_FULL_AFTER_FINAL_TELEMETRY_DELTA = 1500_PASSED_2_SKIPPED_3029_SUBTESTS_PLUS_ONE_TRANSIENT_HOST_TCL_DISCOVERY_FAILURE
TRANSIENT_TCL_TEST_ISOLATED_RERUN = PASS
DESKTOP_COMPILEALL = PASS
SERVER_CURRENT_FOCUSED = 42_PASSED
SERVER_I18N_INITIAL = 11_PASSED
SERVER_PRIOR_BLOCK_1_FOCUSED = 1941_PASSED
POSTGRES_PRIOR_BLOCK_1_E2E = 826_PASSED_PLUS_8_NATURAL_CHAIN_SCENARIOS
SERVER_FULL_DISCOVERY = NOT_PASS_31299_PASSED_38_SKIPPED_63_FAILED_342_ERRORS
SERVER_FULL_DISCOVERY_CAUSE = LEGACY_EXPECTATION_FAILURES_AND_OPT_IN_POSTGRES_FIXTURES_WITHOUT_REQUIRED_DATABASE_URLS
TRADE_15M_BEHAVIOR_CHANGED = NO
TRADE_15M_REGRESSION = PASS_PRIOR_10_TESTS_AND_CONTAINER_UNCHANGED
```

New tests explicitly cover immediate removal of the previous report, late-result
suppression, exact-IID selection preservation, unchanged report snapshot
telemetry, and production exact identity across three historical rows.

## Deployment and safety

```text
ROOT_IMPLEMENTATION_COMMITS = 9530256230035b445eff88e97c189704089c840c,dcf0eca2b515751df67ad0258099202fca584cd2
DESKTOP_IMPLEMENTATION_COMMITS = 195934a5713e372de2df7314afa9d439f19cd30e,6ac53d62dea03943aeb6bc51d258a8e8bbd50288,235bd4366c1b78401433ad96e33fe963518d0357
READONLY_SOURCE = dcf0eca2b515751df67ad0258099202fca584cd2
READONLY_IMAGE = sha256:39944ad2a6037b55561ab3ce46e84c484dec0bcb97721c10bdfeae117fb5a24a
READONLY_HEALTH = HEALTHY_RESTART0
OPERATOR_SOURCE = 3c4a7c68108959321b51a7a2d184dbf36a7549ba_HEALTHY_RESTART0
ORCHESTRATOR_5M_SOURCE = 1c4c27208ddc78ad0ac3b3f4394917a4361ad7ef_RESTART0
TRADE_15M_CONTAINER = UNCHANGED_RESTART0
DESKTOP_SOURCE = 235bd4366c1b78401433ad96e33fe963518d0357_PID9220
ALEMBIC_HEAD = 0025_paper_budget_policy
PAPER_AUTHORITY_MODE = CONTINUOUS
SCALPING_V2_PROFILE_ID = trade-5m-v2
SCALPING_V2_AUTHORITATIVE = PASS
LIVE_STATE_AFTER = DISABLED
REAL_BINANCE_ORDER_API_CALLS = 0
SECRET_OUTPUT = 0
MOBILE_HEAD = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db_PREEXISTING_DIRTY_PRESERVED
```

## Git transport gate

The root repository is pushed and synchronized. The sibling `traders-client`
repository has no configured remote, and the authenticated GitHub owner has no
`traders-client` repository. Creating a repository or pushing its unrelated
history into the server repository would be an unauthorized external-state and
history decision.

```text
ROOT_PUSH = PASS
ROOT_AHEAD = 0
ROOT_BEHIND = 0
CLIENT_LOCAL_HEAD = 235bd4366c1b78401433ad96e33fe963518d0357
CLIENT_REMOTE = NOT_CONFIGURED
CLIENT_PUSH = BLOCKED_MISSING_DESTINATION
CLIENT_WORKTREE = CLEAN
BLOCK_1_PUSH = BLOCKED_FOR_CLIENT_ONLY
REMAINING_BLOCKER = USER_MUST_PROVIDE_OR_AUTHORIZE_EXACT_CLIENT_REMOTE_DESTINATION
NEXT_ACTION = CONFIGURE_AND_PUSH_CLIENT_REMOTE_THEN_REQUEST_EXPLICIT_BLOCK_2_APPROVAL
```

