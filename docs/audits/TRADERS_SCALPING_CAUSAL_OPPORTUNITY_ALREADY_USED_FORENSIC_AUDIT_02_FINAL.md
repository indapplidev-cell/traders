# TRADERS_SCALPING_CAUSAL_OPPORTUNITY_ALREADY_USED_FORENSIC_AUDIT_02

## Verdict

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_SCALPING_CAUSAL_OPPORTUNITY_ALREADY_USED_FORENSIC_AUDIT_02_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = SCALPING_72H_GATE_NOT_YET_REACHED_AND_PROFITABILITY_SAMPLE_REMAINS_INSUFFICIENT
STOP_CONDITION = NONE
```

This was a read-only forensic audit. A proven semantic defect does not make the
audit fail: the production behavior was not changed here.

## Human conclusion

When the system says `SCALP_REJECT_DUPLICATE_OPPORTUNITY` / “Причинная
возможность уже была использована”, the earlier candidate with the same
geometry opportunity ID already passed the causal Geometry, Target, Net Cost
and RR gates and successfully claimed an in-memory `ScalpingOpportunityRegistry`
slot. The claim happens immediately before construction of `PAPER_PLAN_READY`.
It does **not** prove that an order, fill or position existed.

Yes: a PAPER Plan that expires without an actual PAPER command, order, fill or
position can continue blocking a later otherwise-valid candidate. ETHUSDT at
boundary `1787936100000` proves the stronger no-entry case: its plan/final
approval expired at `1787936399999`, its causal outcome was `ENTRY_EXPIRED`, and
the same opportunity was rejected at `1787936700000`, `1787937000000` and
`1787937300000`. There is no time-based release. With current
`opportunity_reentry_enabled=False`, the block lasts for the lifetime of the
5m orchestrator process; an orchestrator restart clears the process-local set,
or a different identity bypasses the old key. This is useful duplicate/churn
protection, but plan-time consumption plus no expiry release is classified
`LIKELY_NEVER_RELEASED_EXPIRED_OPPORTUNITY`, not proven-correct execution
safety semantics.

## Exact baseline

```text
SERVER_HEAD_BEFORE = 2ea3a23d5c5218b898d536f93b5ce4dd0b9024a8
DESKTOP_HEAD_BEFORE = 356da014ec91b091414a9f2bfe909f0f2b1486b8
MOBILE_HEAD_BEFORE = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
PRODUCTION_ALEMBIC_HEAD = 0018_promote_5m_production_search
SCALPING_PROFILE_ID = trade-5m-v1
SCALPING_PARAMETER_SET_ID = trade-5m-v1-runtime-v1-87b8a882d06b3539
COLLECTOR_SEGMENT_ID = scalping-calibration-segment-d8a498357af94ae584b3b691
COLLECTOR_INSTANCE_ID = scalping-calibration-collector-eb422dac-faa2-4e67-83fa-963dd851460a
COLLECTOR_RUNTIME_SOURCE = c30dd05ab55a102f787be3e9ec1fac6c78d71619
COLLECTOR_RUNTIME_ARTIFACT = sha256:cfaa97127236222cef0476acc099b10257f2abaad9ca3ca82890b24746db81c6
COLLECTOR_INCIDENT_BOUNDARY_EXCLUDED = 1787936400000
CONTROL_STATE = ARMED
CONTROL_GENERATION = 6
LIVE_STATE = DISABLED
```

At the audit snapshot, the Readonly API was healthy/current. PAPER readiness
reported `wal_ready=true`, `pitr_ready=true`, valid lineage from
`2026-08-11T07:54:19.615Z`, `pitr_physical_gap=false`, and canary
`WAITING_FOR_ELIGIBLE_APPROVAL` with command count zero. The PAPER daemon and
scheduler were disabled and `live_allowed=false`.

## Machine reason mapping

| Fact | Evidence |
| --- | --- |
| Machine code | `SCALP_REJECT_DUPLICATE_OPPORTUNITY` |
| Producer | `ScalpingPaperRunner._process`, `app/engine_paper/scalping_paper_runner.py:236-276` |
| Registry | `ScalpingOpportunityRegistry.observe_and_claim`, `app/engine_paper/scalping_opportunity_registry.py:8-23` |
| RU label | `app/i18n/catalog.py:1097`: “Скальпинг отклонён: причинная возможность уже была использована” |
| EN label | `app/i18n/catalog.py:1123`: “Scalping rejected: causal opportunity was already admitted” |
| Desktop source | generated bootstrap mirrors the same RU/EN strings; it does not decide semantics |

The English word “admitted” is more precise than the Russian “использована”. A
better Russian label is: **“Скальпинг отклонён: эта причинная возможность уже
была допущена в PAPER Plan”**. It still needs a prior-lifecycle explanation to
avoid implying order/fill/position.

## Authoritative source trace

| Step | Source | Authoritative input | State/event | Authority |
| --- | --- | --- | --- | --- |
| Evaluation | `app/engine_orchestrator/pipeline_runner.py:427-569` | same closed 5m snapshot, setup, strategy and risk | calls `ScalpingPaperRunner` | production decision path |
| Setup identity | `app/engine_setup/setup_detector.py:136-144` | upper symbol, setup type, direction, causal invalidation or entry anchor | 24-hex setup opportunity hash | production-authoritative |
| Geometry identity | `app/engine_paper/scalping_shadow.py:142-156` | profile, upper symbol, direction, setup opportunity ID | 24-hex geometry opportunity hash | production-authoritative |
| Geometry/economics | `app/engine_paper/scalping_shadow.py:355-558` | only causal levels plus bounded current cost capture | `valid_plan=True` only after Geometry/Target/Net Cost/RR pass | production-authoritative |
| Claim/duplicate lookup | `app/engine_paper/scalping_paper_runner.py:236-250` | geometry opportunity ID, reentry flag | registry observation and `_admitted` membership | production-authoritative |
| Used rejection | `app/engine_paper/scalping_paper_runner.py:251-276` | `valid_plan` and claim result | first claim builds READY plan; repeat emits machine reason | production-authoritative |
| Plan persistence | `app/engine_paper/paper_runner.py:27-35`; `pipeline_result_store.py:353-427` | runner result | plan saved, then result persisted | production-authoritative |
| Final approval | `app/engine_paper/final_approval_materializer.py:155-339` | already-created READY plan | quantity, validity and final approval materialized afterward | production-authoritative |
| Expiry projection | `app/server_api/trading_funnel.py:577-618` | persisted approvals and current time | Readonly forces `APPROVAL_EXPIRED` when `valid_until<=now` | presentation/read-only authority |
| Command/order/fill/position | `command_ingestion_service.py`, `order_execution_service.py`, repositories | valid final approval and controlled worker | distinct later lifecycle; no hook back to registry | production-authoritative |
| Release/reopen | registry file contains no release/expiry API | reentry flag only | same key remains admitted; process restart loses in-memory set | production-authoritative absence |

Ordering proof: `ScalpingPaperRunner` calls `observe_and_claim` at lines 238-243,
then constructs `PAPER_PLAN_READY` at lines 251-261. Final Approval is later,
during `PipelineResultStore.finish` at lines 394-405. Therefore Final Approval,
entry eligibility, order, fill and position cannot be the consumption trigger.

## Identity contract

The canonical used-check key is the geometry opportunity ID:

```text
sha256("trade-5m-v1:<SYMBOL>:<BULLISH|BEARISH>:<setup_opportunity_id>")[:24]
```

The nested setup opportunity ID is:

```text
sha256("<SYMBOL>|<setup_type>|<direction>|<causal_invalidation_or_entry_anchor>")[:24]
```

Consequences proven from source and natural records:

- source boundary is deliberately excluded, so adjacent boundaries can share an ID;
- entry evolution, target, regime, score, costs and approval/order state are not
  identity inputs when a causal invalidation anchor is present;
- symbol and direction are present in both layers, so cross-symbol and
  cross-direction collision is cryptographically isolated (subject only to a
  SHA-256 96-bit truncation collision, not an application-level collision);
- setup type and exact string form of the anchor are present in the nested ID;
- a changed setup type or exact anchor creates a new ID even if the market idea
  otherwise looks similar.

Natural ETH proof: the same invalidation `2446.71`, type
`SCALP_COMPRESSION_BREAK` and BEARISH direction stayed ID
`opportunity:364c32242e4d32f32b9b33f1` while entry changed from `2440.81` to
`2439.25`, `2440.00`, and `2445.64`; the later three were rejected. A preceding
`SCALP_BREAKOUT` at the same invalidation obtained another ID, and later anchor
changes `2448.22` then `2446.56` produced still more IDs.

Assessment: identity is over-broad for changed entry/target/regime under an
unchanged type/anchor, and under-stable for exact anchor/type changes. The
natural records prove both boundary behaviors; whether every new anchor is the
same economic idea is not inferable, so the classification remains
`LIKELY_OVER_BROAD_IDENTITY` rather than a second independently proven defect.

## Consumption matrix

| Stage | Consumes? | Changes state? | Releases/reopens? | Evidence |
| --- | --- | --- | --- | --- |
| Strategy admitted | No | No | No | registry not called yet |
| Risk compatibility | No | No | No | runner policy precedes geometry |
| Geometry valid | No alone | No alone | No | `valid_plan` still requires later gates |
| Target valid | No alone | No alone | No | same |
| Net Cost pass | No alone | No alone | No | same |
| RR pass | Claim occurs after full pass | Yes, as part of valid-plan admission | No | runner 236-250 |
| Authoritative Risk | No additional claim | No | No | final materializer is later |
| Final Approval | No | No registry change | Expiry does not release | result store 394-405 |
| PAPER Plan | Yes, immediately before READY construction | Adds ID to process-local set | Plan expiry does not release | runner 238-261 |
| Entry eligible / entry touched | No | No registry change | No | no registry dependency |
| PAPER Order | No | No registry change | No | separate tables/services |
| Fill | No | No registry change | No | separate tables/services |
| Position | No | No registry change | No | separate tables/services |
| Closed trade | No | No registry change | No | no registry hook |
| Approval expired | No new consumption | Existing state remains | **No** | no release API; natural ETH proof |

```text
WHAT_CONSUMES_CAUSAL_OPPORTUNITY = VALID_GEOMETRY_TARGET_NET_COST_RR_CANDIDATE_CLAIM_IMMEDIATELY_BEFORE_PAPER_PLAN_READY
WHEN_CONSUMPTION_OCCURS = BEFORE_PAPER_PLAN_OBJECT_AND_BEFORE_FINAL_APPROVAL_ORDER_FILL_POSITION
WHAT_RELEASES_OR_REOPENS_OPPORTUNITY = ONLY_EXPLICIT_REENTRY_TRUE_OR_PROCESS_RESTART_OR_NEW_IDENTITY;NO_TTL_RELEASE
```

## Natural timelines

### ETHUSDT central expired-unexecuted/no-entry chain

```text
boundary = 1787936100000
direction = BEARISH
setup_type = SCALP_COMPRESSION_BREAK
setup_opportunity_id = opportunity:6c35c4d4dd0560a175c17fe8
registry_geometry_opportunity_id = opportunity:364c32242e4d32f32b9b33f1
entry/stop/target = 2440.81 / 2449.6942708333336 / 2405.97
plan_created_at_ms = 1787936134185
final_approval = FINAL_APPROVAL_CREATED
valid_until_ms = 1787936399999
collector_entry_status = EXPIRED
collector_baseline_outcome = ENTRY_EXPIRED
paper_command/order/fill/position = NO/NO/NO/NO
later_same_id_rejects = 1787936700000,1787937000000,1787937300000
later_entries = 2439.25,2440.00,2445.64
later_gross_rr = 3.21045069,3.53972175,9.93302034
later_net_rr = 1.57315290,1.69210563,3.11651102
```

Every later rejection occurred after approval expiry and still had
`scalping_geometry_diagnostics.valid_plan=true`. This proves that later
candidates were rejected solely by prior plan-time registry consumption, not by
Geometry, Target, Net Cost, RR, order, fill, position or live exposure.

### Secondary checks

- BNBUSDT: plan at `1787898600000`, final approval expired at
  `1787898899999`; same ID rejected at `1787898900000`. Collector ex-post path
  says `ENTERED/TIME_EXPIRED`, but production DB still has no command/order.
- AVAXUSDT: valid BEARISH plan at `1787935800000`, ID
  `opportunity:d8a7832a4da8522380f11e82`, final approval expired at
  `1787936099999`, order/fill/position unavailable/not opened. No later
  same-ID duplicate rejection was present in the bounded segment.
- LINKUSDT: the first claim/READY plan is the raw preserved production row at
  excluded mixed boundary `1787936400000`; it expired at `1787936699999` and
  caused included rejects at `1787936700000`, `1787937000000`, and
  `1787938500000`. The excluded boundary is not counted as a calibration row;
  it is used only as authoritative lineage for the later rejection cause.

## All already-used rejections in the homogeneous segment

Scope: all 5m observations in segment `d8a498...` available at audit cutoff,
with boundary `1787936400000` excluded from aggregate counts.

```text
ALREADY_USED_REJECT_COUNT_RAW = 12
ALREADY_USED_REJECT_COUNT_UNIQUE_OPPORTUNITIES = 5
ALREADY_USED_REJECTS_PRIOR_PLAN_ONLY = 0
ALREADY_USED_REJECTS_PRIOR_EXPIRED_UNEXECUTED = 12
ALREADY_USED_REJECTS_PRIOR_ENTRY_ELIGIBLE = 0
ALREADY_USED_REJECTS_PRIOR_ORDER = 0
ALREADY_USED_REJECTS_PRIOR_FILL = 0
ALREADY_USED_REJECTS_PRIOR_OPEN_POSITION = 0
ALREADY_USED_REJECTS_PRIOR_CLOSED_TRADE = 0
ALREADY_USED_REJECTS_PRIOR_UNKNOWN = 0
ALREADY_USED_REJECTS_CLASSIFIED_BY_PRIOR_LIFECYCLE = YES
```

“Prior expired unexecuted” is the terminal-state classification at each reject.
The separate causal price-path diagnostic of the prior plan was: three ETH
rejects caused by a prior `ENTRY_EXPIRED` plan; six rejects caused by prior
plans whose hypothetical entry was touched; three LINK rejects have entry path
`UNKNOWN/UNAVAILABLE` because the claimant boundary is the excluded incident.
None of those price-path states created a production PAPER command.

## Entry/order/fill/position proof

Production table counts at cutoff:

```text
paper_execution_commands = 0
paper_orders = 0
paper_fills = 0
paper_positions = 0
paper_journal_entries = 0
```

The registry code has no read or write dependency on these tables. Therefore:

- entry touch/eligibility does not consume or release differently;
- no natural `entry eligible -> PAPER order` case exists;
- no natural `PAPER order -> no fill` case exists;
- code proof still establishes that order/fill/position/close have no effect on
  the registry.

```text
ENTRY_ELIGIBLE_ORDER_FILL_POSITION_EFFECTS_PROVEN = YES_NO_NATURAL_ORDER_CASES_WITH_CODE_AND_ZERO_TABLE_PROOF
```

## Ex-post diagnostics (never part of decision path)

All 12 later rejected rows had `valid_plan=true`; thus all 12 passed current
Geometry, Target, Net Cost and RR before duplicate rejection. Outcome follow-up
exists for all 12: `TIME_EXPIRED=9`, `SL_FIRST=2`, `ENTRY_EXPIRED=1`. Eleven
entry-bearing paths have MFE P50/P90 `30.9280/77.2682 bps` and MAE P50/P90
`10.5494/36.7736 bps`; the entry-expired row correctly keeps MFE/MAE null.

These later outcomes are diagnostic only. They were read after the decision,
were not used to reconstruct or alter the original gate, and do not justify
relaxing the safety rule by themselves.

```text
EXPIRED_THEN_ALREADY_USED_CASE_COUNT = 12
EXPIRED_THEN_ALREADY_USED_LATER_CURRENT_PIPELINE_PASS_COUNT = 12
DECISION_PATH_FUTURE_LEAKAGE = 0
```

## Safety-intent assessment

The rule does prevent repeated PAPER plans every 5m for one stable ID, reduces
churn, prevents repeated attempts on a stale anchor, avoids inflated raw plan
counts, and limits correlated exposure attempts. However:

1. claim occurs before plan construction/final approval;
2. approval expiry is ignored by the registry;
3. no terminal lifecycle state releases the ID;
4. the state is process-local, so restart releases everything without a market
   or lifecycle event while normal expiry releases nothing.

```text
SEMANTIC_RISK_CLASSIFICATION = LIKELY_NEVER_RELEASED_EXPIRED_OPPORTUNITY
PROVEN_FAILURE_MODE = PLAN_TIME_PROCESS_LOCAL_CLAIM_HAS_NO_TTL_OR_TERMINAL_RELEASE_AND_BLOCKS_EXPIRED_UNEXECUTED_SAME_ID
TRADING_IMPACT_ASSESSMENT = VALID_LATER_REEVALUATIONS_CAN_BE_SUPPRESSED_UNTIL_PROCESS_RESTART_OR_IDENTITY_CHANGE
OVER_BROAD_IDENTITY_ASSESSMENT = LIKELY_ENTRY_TARGET_REGIME_EVOLUTION_COLLIDES_WHILE_TYPE_AND_INVALIDATION_STAY_EQUAL
UNDER_BROAD_IDENTITY_ASSESSMENT = EXACT_TYPE_OR_FLOAT_ANCHOR_CHANGE_CREATES_NEW_ID;NATURAL_MULTIPLE_IDS_PROVEN_BUT_DEFECT_INTENT_UNPROVEN
```

## UI / Readonly observability

Readonly correctly derives `APPROVAL_EXPIRED` and exposes plan/final approval,
validity, entry/stop/target, order/fill/position as unavailable/not opened. It
does **not** join a duplicate row to the prior registry opportunity. The row
lacks prior opportunity reference, claimed-at time, consumed-by stage, prior
terminal reason and prior entry/order/fill/position facts. The registry itself
stores only a set and observation count, so `consumed_at` and lifecycle cause
are not authoritative persisted fields.

```text
UI_LABEL_SEMANTIC_ACCURACY = FAIL_LABEL_IMPLIES_GENERIC_USE_WHILE_BACKEND_MEANS_PRIOR_VALID_PLAN_ADMISSION
READONLY_API_EXPLAINS_PRIOR_CONSUMPTION = NO
OBSERVABILITY_REMEDIATION_RECOMMENDED = YES_SEPARATE_ADDITIVE_READONLY_DESKTOP_TASK_WITH_PRIOR_ID_CLAIM_TIME_STAGE_LIFECYCLE_TERMINAL_AND_EXECUTION_FACTS
```

## Collector, WAL/PITR, control and security

At the audit snapshot and final read-only checks:

```text
COLLECTOR_RUNNING_AFTER_TASK = YES
COLLECTOR_SINGLETON_OWNER_COUNT_AFTER = 1
COLLECTOR_RESTART_LOOP_AFTER = NO_RESTART_COUNT0
COLLECTOR_SEGMENT_UNCHANGED = YES
INCIDENT_BOUNDARY_EXCLUSION_PRESERVED = YES_1787936400000
RAW_APPEND_ONLY_RECORDS_MUTATED = 0
CALIBRATION_COHORT_MIXING_AFTER = NO
COLLECTOR_MISSING_DUPLICATE_ERROR_FUTURE = 0_0_0_0
WAL_READY_AFTER = true
PITR_READY_AFTER = true
PHYSICAL_WAL_GAP_AFTER = false
ACK_OWNER_HEALTH_AFTER = PASS_SINGLETON_PID27564_HEARTBEAT_HEALTHY_BACKLOG0_PENDING0
CONTROL_STATE_AFTER = ARMED
CONTROL_GENERATION_AFTER = 6
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SECRET_OUTPUT = 0
SECURITY_FINDINGS = 0
```

The mixed boundary remains append-only preserved and manifest-excluded. It was
not added to aggregate counts or ex-post calibration statistics.

## Validation

```text
PYTEST = 341_PASS
BANDIT = HIGH0_MEDIUM0_LOW7_KNOWN_STATUS_STRING_FALSE_POSITIVES
SECRET_SCANNER = ACTIVE_PRODUCTION_DB_EXPOSURE_SCAN_PASS_FINDINGS0
SAFE_DIAGNOSTICS = NO_COMMAND_LINE_VALUE_NO_SECRET_VALUE
PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
DB_MUTATIONS_BY_TASK = 0
SCALPING_PARAMETER_PROMOTION_BY_TASK = 0
15M_RUNTIME_RESTARTS_BY_TASK = 0
SCALPING_RUNTIME_RESTARTS_BY_TASK = 0
COLLECTOR_RESTARTS_BY_TASK = 0
CONTROL_RESTARTS_BY_TASK = 0
POSTGRES_RESTARTS_BY_TASK = 0
```

## Required final report

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_SCALPING_CAUSAL_OPPORTUNITY_ALREADY_USED_FORENSIC_AUDIT_02_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = SCALPING_72H_GATE_NOT_YET_REACHED_AND_PROFITABILITY_SAMPLE_REMAINS_INSUFFICIENT
STOP_CONDITION = NONE

SERVER_HEAD_BEFORE = 2ea3a23d5c5218b898d536f93b5ce4dd0b9024a8
SERVER_HEAD_AFTER = RESOLVED_IN_FINAL_TASK_HANDOFF
DESKTOP_HEAD_BEFORE = 356da014ec91b091414a9f2bfe909f0f2b1486b8
DESKTOP_HEAD_AFTER = 356da014ec91b091414a9f2bfe909f0f2b1486b8
MOBILE_HEAD_BEFORE = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
MOBILE_HEAD_AFTER = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
PRODUCTION_ALEMBIC_HEAD = 0018_promote_5m_production_search

SCALPING_PROFILE_ID = trade-5m-v1
SCALPING_PARAMETER_SET_ID = trade-5m-v1-runtime-v1-87b8a882d06b3539
COLLECTOR_SEGMENT_ID = scalping-calibration-segment-d8a498357af94ae584b3b691
COLLECTOR_INCIDENT_BOUNDARY_EXCLUDED = YES_1787936400000

ALREADY_USED_MACHINE_REASON = SCALP_REJECT_DUPLICATE_OPPORTUNITY
ALREADY_USED_UI_LABEL = Скальпинг отклонён: причинная возможность уже была использована
ALREADY_USED_REASON_PRODUCER_IDENTIFIED = YES

CAUSAL_OPPORTUNITY_ID_SOURCE = ShadowGeometryCandidate.opportunity_id_OVER_SetupDetector.opportunity_id
CAUSAL_OPPORTUNITY_ID_FIELDS = PROFILE_SYMBOL_DIRECTION_SETUP_IDENTITY_NESTED_SYMBOL_SETUP_TYPE_DIRECTION_INVALIDATION_OR_ENTRY_ANCHOR
IDENTITY_BOUNDARY_RULES_PROVEN = YES
CROSS_SYMBOL_COLLISION = APPLICATION_LEVEL_IMPOSSIBLE_SYMBOL_IN_IDENTITY_EXCEPT_HASH_COLLISION
CROSS_DIRECTION_COLLISION = APPLICATION_LEVEL_IMPOSSIBLE_DIRECTION_IN_IDENTITY_EXCEPT_HASH_COLLISION

WHAT_CONSUMES_CAUSAL_OPPORTUNITY = VALID_PLAN_CLAIM_IMMEDIATELY_BEFORE_PAPER_PLAN_READY
CONSUMPTION_CODE_PATH = scalping_paper_runner.py:236-276_TO_scalping_opportunity_registry.py:14-23
CONSUMPTION_EVENT_SOURCE = PROCESS_LOCAL_OBSERVE_AND_CLAIM
WHEN_CONSUMPTION_OCCURS = AFTER_GEOMETRY_TARGET_NET_COST_RR_PASS_BEFORE_PLAN_OBJECT_FINAL_APPROVAL_AND_EXECUTION

CONSUMPTION_AT_FINAL_APPROVAL = NO_ALREADY_CONSUMED
CONSUMPTION_AT_PAPER_PLAN = YES_IMMEDIATELY_BEFORE_READY_PLAN_CONSTRUCTION
CONSUMPTION_AT_ENTRY_ELIGIBLE = NO
CONSUMPTION_AT_PAPER_ORDER = NO
CONSUMPTION_AT_FILL = NO
CONSUMPTION_AT_POSITION = NO

WHAT_RELEASES_OR_REOPENS_OPPORTUNITY = REENTRY_TRUE_OR_PROCESS_RESTART_OR_NEW_IDENTITY_ONLY
REOPEN_CODE_PATH = NONE_FOR_EXPIRY_OR_TERMINAL_LIFECYCLE
REOPEN_CONDITIONS = opportunity_reentry_enabled_TRUE_OR_REGISTRY_PROCESS_RESTART_OR_IDENTITY_INPUT_CHANGE
APPROVAL_EXPIRED_RELEASES_OPPORTUNITY = NO
EXPIRED_UNEXECUTED_PLAN_REUSE_SEMANTICS_PROVEN = YES
ENTRY_ELIGIBLE_ORDER_FILL_POSITION_EFFECTS_PROVEN = YES_NO_NATURAL_ORDER_CASES_WITH_CODE_PROOF

ETH_NATURAL_TIMELINE = B1787936100000_PLAN_FINALAPPROVAL_EXP1787936399999_ENTRYEXPIRED_COMMAND0_ORDER0_FILL0_POSITION0_THEN_DUPLICATE_B1787936700000_B1787937000000_B1787937300000
SECONDARY_NATURAL_TIMELINE = BNB_EXPIRED_THEN_DUPLICATE_AND_AVAX_EXPIRED_UNEXECUTED_NO_LATER_SAME_ID_DUPLICATE

ALREADY_USED_REJECT_COUNT_RAW = 12
ALREADY_USED_REJECT_COUNT_UNIQUE_OPPORTUNITIES = 5
ALREADY_USED_REJECTS_PRIOR_PLAN_ONLY = 0
ALREADY_USED_REJECTS_PRIOR_EXPIRED_UNEXECUTED = 12
ALREADY_USED_REJECTS_PRIOR_ENTRY_ELIGIBLE = 0
ALREADY_USED_REJECTS_PRIOR_ORDER = 0
ALREADY_USED_REJECTS_PRIOR_FILL = 0
ALREADY_USED_REJECTS_PRIOR_OPEN_POSITION = 0
ALREADY_USED_REJECTS_PRIOR_CLOSED_TRADE = 0
ALREADY_USED_REJECTS_PRIOR_UNKNOWN = 0
ALREADY_USED_REJECTS_CLASSIFIED_BY_PRIOR_LIFECYCLE = YES

EXPIRED_THEN_ALREADY_USED_CASE_COUNT = 12
EXPIRED_THEN_ALREADY_USED_LATER_CURRENT_PIPELINE_PASS_COUNT = 12
EX_POST_MFE_MAE_SUMMARY = ENTRYBEARING11_MFE_P50_30.9280_P90_77.2682_MAE_P50_10.5494_P90_36.7736_BPS_ONE_ENTRYEXPIRED_NULL

OVER_BROAD_IDENTITY_ASSESSMENT = LIKELY
UNDER_BROAD_IDENTITY_ASSESSMENT = NATURAL_MULTIPLE_EXACT_ANCHOR_TYPE_IDS_PROVEN_DEFECT_INTENT_UNPROVEN
SEMANTIC_RISK_CLASSIFICATION = LIKELY_NEVER_RELEASED_EXPIRED_OPPORTUNITY
PROVEN_FAILURE_MODE = EXPIRED_UNEXECUTED_PLAN_REMAINS_PROCESS_LOCAL_USED_WITHOUT_TTL_RELEASE
TRADING_IMPACT_ASSESSMENT = LATER_FULL_PIPELINE_PASS_REEVALUATIONS_SUPPRESSED_UNTIL_RESTART_OR_NEW_ID

UI_LABEL_SEMANTIC_ACCURACY = FAIL_WITH_PROOF
READONLY_API_EXPLAINS_PRIOR_CONSUMPTION = NO
OBSERVABILITY_REMEDIATION_RECOMMENDED = YES_SEPARATE_ADDITIVE_TASK

DECISION_PATH_FUTURE_LEAKAGE = 0
PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
DB_MUTATIONS_BY_TASK = 0
SCALPING_PARAMETER_PROMOTION_BY_TASK = 0

COLLECTOR_RUNNING_AFTER_TASK = YES
COLLECTOR_SINGLETON_OWNER_COUNT_AFTER = 1
COLLECTOR_RESTART_LOOP_AFTER = NO
COLLECTOR_SEGMENT_UNCHANGED = YES
INCIDENT_BOUNDARY_EXCLUSION_PRESERVED = YES
RAW_APPEND_ONLY_RECORDS_MUTATED = 0
CALIBRATION_COHORT_MIXING_AFTER = NO

15M_RUNTIME_RESTARTS_BY_TASK = 0
SCALPING_RUNTIME_RESTARTS_BY_TASK = 0
COLLECTOR_RESTARTS_BY_TASK = 0
CONTROL_RESTARTS_BY_TASK = 0
POSTGRES_RESTARTS_BY_TASK = 0

WAL_READY_AFTER = true
PITR_READY_AFTER = true
PHYSICAL_WAL_GAP_AFTER = false
ACK_OWNER_HEALTH_AFTER = PASS

CONTROL_STATE_AFTER = ARMED
CONTROL_GENERATION_AFTER = 6
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0

SECURITY_SCANNER = BANDIT_HIGH0_MEDIUM0
SECRET_SCANNER = ACTIVE_PRODUCTION_DB_EXPOSURE_FINDINGS0
SECRET_OUTPUT = 0
SECURITY_FINDINGS = 0

SERVER_COMMITS = RESOLVED_IN_FINAL_TASK_HANDOFF
DESKTOP_COMMITS = NONE
MOBILE_COMMITS = NONE
SERVER_ROOT_CLEAN_AFTER = RESOLVED_IN_FINAL_TASK_HANDOFF
DESKTOP_ROOT_CLEAN_AFTER = YES
MOBILE_ROOT_CLEAN_AFTER = YES
PUSHED = NO

EVIDENCE_FILE = D:\disk_E\game_projects\traders\evidence_inbox\TRADERS_SCALPING_CAUSAL_OPPORTUNITY_ALREADY_USED_FORENSIC_AUDIT_02_FINAL.md
EVIDENCE_SHA256 = RESOLVED_FROM_FINAL_IMMUTABLE_COPY_IN_TASK_HANDOFF_AND_SIDECAR
NEXT_ACTION = CREATE_SEPARATE_CAUSAL_OPPORTUNITY_CONSUMPTION_RELEASE_IDENTITY_REMEDIATION_TASK
```

