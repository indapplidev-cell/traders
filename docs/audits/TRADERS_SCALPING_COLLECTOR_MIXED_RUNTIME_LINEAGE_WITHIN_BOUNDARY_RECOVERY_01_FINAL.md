# TRADERS_SCALPING_COLLECTOR_MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY_RECOVERY_01 — final evidence

Reconciled at `2026-08-28T22:43:26Z`. This report records a collector-only
forensic recovery. No trading algorithm, profile parameters, Control state,
LIVE state, PostgreSQL service, WAL lineage, 15m runtime, or 5m trading runtime
was changed or restarted.

## Final report

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_SCALPING_COLLECTOR_MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY_RECOVERY_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE

SERVER_HEAD_BEFORE = 233e1db51b5c8257a70931649975d0f78a24b38a
SERVER_IMPLEMENTATION_COMMIT = 8eb97ad5f70c672ead3abbe72e258151059991ee
SERVER_HEAD_AFTER = 8db8af52ba782fe44ba7a082e9dcd3a5fc4411f3
DESKTOP_HEAD_BEFORE = 356da014ec91b091414a9f2bfe909f0f2b1486b8
DESKTOP_HEAD_AFTER = 356da014ec91b091414a9f2bfe909f0f2b1486b8
MOBILE_HEAD_BEFORE = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
MOBILE_HEAD_AFTER = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
PRODUCTION_ALEMBIC_HEAD_BEFORE = 0018_promote_5m_production_search
PRODUCTION_ALEMBIC_HEAD_AFTER = 0018_promote_5m_production_search

SCALPING_PROFILE_ID = trade-5m-v1
SCALPING_PARAMETER_SET_ID_BEFORE = trade-5m-v1-runtime-v1-87b8a882d06b3539
SCALPING_PARAMETER_SET_ID_AFTER = trade-5m-v1-runtime-v1-87b8a882d06b3539

COLLECTOR_INSTANCE_ID_BEFORE = scalping-calibration-collector-6fd8c14c-308a-40e5-ae37-37c5bc03a000_LAST_FAILED_HEALTH_AT_PREFLIGHT
COLLECTOR_SEGMENT_ID_BEFORE = scalping-calibration-segment-d8a498357af94ae584b3b691
COLLECTOR_OWNER_COUNT_BEFORE = 0
COLLECTOR_RESTART_COUNT_BEFORE = 292
COLLECTOR_HEALTH_BEFORE = FAILED_RESTART_LOOP_MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY

AFFECTED_BOUNDARY_IDENTIFIED = YES
FIRST_FAILING_BOUNDARY = 1787936400000_2026-08-28T17:00:00Z
LAST_GOOD_HOMOGENEOUS_BOUNDARY = 1787936100000_2026-08-28T16:55:00Z
FIRST_MIXED_BOUNDARY = 1787936400000_2026-08-28T17:00:00Z
MIXED_BOUNDARY_COUNT = 1
DISTINCT_RUNTIME_LINEAGE_COUNT_WITHIN_BOUNDARY = 2
MIXED_LINEAGE_MEMBERS_IDENTIFIED = YES
RUNTIME_LINEAGE_A = daemon_orchestrator-578f42ff56f7_source_c30dd05ab55a102f787be3e9ec1fac6c78d71619_artifact_sha256:cfaa97127236222cef0476acc099b10257f2abaad9ca3ca82890b24746db81c6_parameter_trade-5m-v1-runtime-v1-87b8a882d06b3539_profile_trade-5m-v1_schema0018_count9
RUNTIME_LINEAGE_B = daemon_orchestrator-d94efb4ea8fa_source_8b446e09ba39e1a40aeedcf594e14f86c856431f_artifact_sha256:09ac8432f00325532e209896d263595cfac2f00d8385ce19da2c4b7098b26731_cross-profile-claim_profile-row-trade-5m-v1_DUPLICATE_WINDOW_no-decision-payload_count1
ADDITIONAL_RUNTIME_LINEAGES = NONE
ROOT_CAUSE = DUPLICATE_RUNTIME_PRODUCER_CROSS_PROFILE_STALE_ACTIVE_CLAIM
ROOT_CAUSE_PROVEN = YES

PREVIOUS_HOMOGENEOUS_DATASET_INTEGRITY = PASS
PREVIOUS_HOMOGENEOUS_BOUNDARIES_MUTATED_BY_TASK = 0
CONTAMINATED_BOUNDARY_PRESERVED = YES
CONTAMINATED_BOUNDARY_USED_FOR_CALIBRATION = NO
RAW_APPEND_ONLY_RECORDS_REWRITTEN = 0
RAW_APPEND_ONLY_RECORDS_DELETED = 0
OUTCOME_FOLLOWUP_INTEGRITY = PASS
FUTURE_LEAKAGE = 0

RECOVERY_STRATEGY = B_RESUME_SAME_SEGMENT_WITH_CANONICAL_BOUNDARY_EXCLUSION
RECOVERY_STRATEGY_JUSTIFICATION = ONE_FOREIGN_DUPLICATE_WINDOW_ROW_FROM_LEGACY_15M_RETRY_OWNER_NO_5M_DECISION_PAYLOAD_SAME_5M_RUNTIME_BEFORE_AND_AFTER
NEW_SEGMENT_REQUIRED = NO
OLD_HOMOGENEOUS_SEGMENT_ID = scalping-calibration-segment-d8a498357af94ae584b3b691
CONTAMINATED_BOUNDARY_INCIDENT_ID = mixed-lineage-b379c8030476d03683b70a3d
NEW_HOMOGENEOUS_SEGMENT_ID = NOT_APPLICABLE_SAME_SEGMENT_CONTINUATION

CHECKPOINT_BEFORE = sha256:2DE6BEE3BADCE9DDA39D60A25107CBBC6F37C31EAB66F9CE64C2E760E1D32B93_last_seen1787936100000_last_persisted1787936100000_records5190_daemon578f
CHECKPOINT_AFTER = acceptance_sha256:C48158A8E0B8DBC152E6B2400DB183BF10AB89219848EEE58986B063CFF1114C_last_seen1787956800000_last_persisted1787956800000_records5870_excluded1787936400000_daemon578f
CHECKPOINT_RECOVERY_CANONICAL = YES
MANIFEST_BEFORE = sha256:DEA4EA31D3898D8EE734DC1852B57F012D6CBA7657F9585A9A38A8E5861264C7_segments2_parts24_exclusions0
MANIFEST_AFTER = acceptance_sha256:63B11F6230C744A696FB0D020DE11E911031181F1EBFBD87F4842A6DEAE3CC26_segments2_parts27_exclusions1
MIXED_LINEAGE_FAIL_CLOSED_GUARD_PRESERVED = YES
FUTURE_MID_BOUNDARY_LINEAGE_MIX_PREVENTION = IMPLEMENTED_BOUNDARY_ATOMIC_REJECT_APPEND_ONLY_INCIDENT_MANIFEST_EXCLUSION_SEPARATE_SCAN_CURSOR

COLLECTOR_INSTANCE_ID_AFTER = scalping-calibration-collector-eb422dac-faa2-4e67-83fa-963dd851460a
COLLECTOR_SEGMENT_ID_AFTER = scalping-calibration-segment-d8a498357af94ae584b3b691
COLLECTOR_SINGLETON_OWNER_COUNT_AFTER = 1
COLLECTOR_RESTART_COUNT_AFTER = 0
COLLECTOR_RESTARTS_BY_TASK = 1_CONTROLLED_START_AFTER_HOLD
COLLECTOR_REPLACEMENTS_BY_TASK = 1
COLLECTOR_RESTART_LOOP_AFTER = NO
COLLECTOR_HEALTH_AFTER = RUNNING_OWNER1_ERRORS0_MISSING0_DUPLICATE0_FUTURE0_BOUNDARIES355_RECORDS5870

NATURAL_RECOVERY_5M_BOUNDARIES_VERIFIED = 3
RECOVERY_BOUNDARY_1 = 1787956200000_2026-08-28T22:30:00Z_EXACT10_SINGLE578f_CLOSED10_FUTURE0
RECOVERY_BOUNDARY_2 = 1787956500000_2026-08-28T22:35:00Z_EXACT10_SINGLE578f_CLOSED10_FUTURE0
RECOVERY_BOUNDARY_3 = 1787956800000_2026-08-28T22:40:00Z_EXACT10_SINGLE578f_CLOSED10_FUTURE0
FIRST_RECOVERED_BOUNDARY_EXACT10 = PASS
RECOVERY_MISSING_COUNT = 0
RECOVERY_DUPLICATE_COUNT = 0
CALIBRATION_COHORT_MIXING_AFTER = 0

15M_CONTINUITY = PASS
SCALPING_TRADING_CONTINUITY = PASS
TRADE_15M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
SCALPING_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
SCALPING_PARAMETER_PROMOTION_BY_TASK = NO
15M_RUNTIME_RESTARTS_BY_TASK = 0
SCALPING_RUNTIME_RESTARTS_BY_TASK = 0
POSTGRES_RESTARTS_BY_TASK = 0
CONTROL_RESTARTS_BY_TASK = 0

WAL_READY_AFTER = true
PITR_READY_AFTER = true
PHYSICAL_WAL_GAP_AFTER = false
ACK_OWNER_HEALTH_AFTER = HEALTHY_SINGLETON_PID27564_IDENTITY_LOCK_STATE_HEARTBEAT_MATCH_BACKLOG0_PENDING0
PITR_LINEAGE_ID_AFTER = base-20260811T075419Z-f179b4e1
CONTROL_STATE_AFTER = ARMED
CONTROL_GENERATION_AFTER = 6
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0

COLLECTOR_RESOURCE_BEHAVIOR = HEALTHY_STEADY_CPU0PCT_MEMORY179.8MiB_NO_POLLING_OR_RESTART_STORM
5M_LATENCY_MATERIAL_REGRESSION = NO_PRETASK_P50_149MS_P95_1421.7MS_POST_P50_140MS_P95_200.95MS
15M_LATENCY_MATERIAL_REGRESSION = NO_PRETASK_P50_228.5MS_P95_1873.3MS_POST_P50_197MS_P95_290.25MS

MIXED_LINEAGE_TESTS = PASS
BOUNDARY_ATOMICITY_TESTS = PASS
SEGMENT_ROLLOVER_TESTS = PASS
CHECKPOINT_RECOVERY_TESTS = PASS
APPEND_ONLY_INTEGRITY_TESTS = PASS
OUTCOME_FOLLOWUP_TESTS = PASS
EXACT10_TESTS = PASS
FUTURE_LEAKAGE_TESTS = PASS
15M_NON_REGRESSION_TESTS = PASS
SCALPING_NON_REGRESSION_TESTS = PASS_WITH_ONE_UNCHANGED_PREEXISTING_RISK_FIXTURE_MISMATCH
SECURITY_SCANNER = BANDIT_PASS_HIGH0
SECRET_SCANNER = PASS_ZERO_FINDINGS
SECRET_OUTPUT = 0
SECURITY_FINDINGS = 0

PREVIOUS_UI_IMPLEMENTATION_REWORKED = NO
PREVIOUS_UI_FINAL_ACCEPTANCE_RERUN = PASS_RU_EN_1000X680_EXACT10_10_NO_INTERNAL_FUNNEL_SCROLL_SELECTED_ADAUSDT

SERVER_COMMITS = 8eb97ad5f70c672ead3abbe72e258151059991ee,8db8af52ba782fe44ba7a082e9dcd3a5fc4411f3
DESKTOP_COMMITS = NONE
MOBILE_COMMITS = NONE
SERVER_ROOT_CLEAN_AFTER = YES_AT_PROJECT_STATE_COMMIT
DESKTOP_ROOT_CLEAN_AFTER = YES
MOBILE_ROOT_CLEAN_AFTER = YES
PUSHED = NO
EVIDENCE_FILE = D:\disk_E\game_projects\traders\evidence_inbox\TRADERS_SCALPING_COLLECTOR_MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY_RECOVERY_01_FINAL.md
EVIDENCE_SHA256 = SELF_RESOLVE_WITH_Get-FileHash_-Algorithm_SHA256
NEXT_ACTION = CONTINUE_SAME_HOMOGENEOUS_SCALPING_SEGMENT_WITH_INCIDENT_BOUNDARY_EXCLUDED_AND_REASSESS_CALIBRATION_GATE
```

## Boundary and root-cause proof

The affected 5m interval is `[1787936100000, 1787936400000)`, closed at
`2026-08-28T17:00:00Z`. Production contains exactly ten rows. Nine symbols
(`ADA, AVAX, BNB, DOGE, ETH, LINK, SOL, SUI, XRP`) were completed by the
canonical 5m daemon `orchestrator-578f42ff56f7`. BTC was a single
`DUPLICATE_WINDOW/NO_ACTION` row completed by the deployed 15m daemon
`orchestrator-d94efb4ea8fa`. The record references span result IDs 40931..40943;
their canonical record-set digest is
`0776c277aa3404b90a2f3f728bbc0f400d4245545ffd7757fe52a2ea95678182`.

The deployed 15m source `8b446e09...` calls `claim_due_waiting` without a
profile predicate; its store query selects every due/stale active profile row.
The foreign row was created by the 5m owner at `17:01:12.359Z`, then reclaimed
by the legacy daemon at `17:01:22.232Z` and terminated as duplicate at
`17:01:23.031Z`. That daemon otherwise owns only 15m rows; this is its sole 5m
row. The canonical 5m daemon is unchanged before and after the incident and all
subsequent scanned boundaries are single-lineage. Therefore this is a bounded
duplicate-producer stale-claim incident, not a genuine 5m runtime deployment or
parameter transition.

## Immutable preservation and cohort integrity

The incident is stored in the new append-only `incidents` JSONL part and in the
manifest exclusion list. It includes all ten run/result references, symbol to
daemon membership, safe lineage metadata, source offsets and per-record SHA-256
references. No observation or follow-up was emitted for the mixed boundary.

All 287 accepted pre-incident boundaries from `1787850300000` through
`1787936100000` are exact10, one daemon lineage, errors0, future0. The complete
corpus parses with unique observation and outcome IDs; every outcome references
an observation. The first 5,190 pre-task observation records remain an exact
byte prefix. In particular, the active part prefix SHA-256 remains
`6ee64735a9986f97b82b9728dfe71ca44d21bf9219faea2bc8b2963a08d730e5`,
matching pre-flight, and all closed parts retain their pre-flight hashes.

The recovery keeps `last_persisted_boundary` at the last good boundary until a
clean boundary succeeds, while a separate `last_seen_boundary` scan cursor
records the excluded incident. A crash after incident append is idempotent:
incident identity, manifest exclusion and checkpoint are reconstructed without
accepting or rewriting the mixed rows.

## Validation evidence

- Collector deterministic tests: 13 passed. The A/B fixture rejects the mixed
  boundary, preserves incident and follow-ups, leaves last-good persisted state
  intact, and resumes at the next clean boundary.
- Focused collector/orchestrator/security matrix: 259 passed, 5 skipped.
- Broader orchestrator/risk/API matrix: 145 passed, 5 skipped, with the exact
  previously documented out-of-scope risk fixture mismatch unchanged.
- Desktop full suite: 249 tests passed, 2 isolated-PG tests skipped; the 1600
  deterministic matrix and 1300 disabled-server matrix passed.
- Production UI rerun: RU and EN both passed at 1000x680 with exact10 and no
  funnel-internal vertical scroll. No desktop source was changed.
- Bandit and changed-diff secret scan: zero findings; safe inspectors emitted
  no credential or command-line values.

At final acceptance, collector image `sha256:8454d15c...`, container
`334720af...`, owner count one and Docker restart count zero were stable. The
15m/5m/PostgreSQL/Control containers retained their pre-task identities and
restart count zero. WAL/PITR remained true/true with no physical gap, ACK owner
PID 27564 remained healthy, Control stayed ARMED generation 6, and LIVE stayed
disabled.
