# TRADERS PAPER market-data watermark lineage remediation 01

```text
TASK = TRADERS_PAPER_MARKET_DATA_WATERMARK_LINEAGE_REMEDIATION_01
FINAL_VERDICT = PASS_IMPLEMENTED_AND_ISOLATED_VALIDATED_NOT_DEPLOYED
PROJECT_STATE_COMMIT = 30d2259350855b1b7fce8318f57b3a8544413037
ROOT_CAUSE = MARKET_DATA_SNAPSHOT_OWNED_NO_IDENTITY_ONLINE_ANALYSIS_PROPAGATED_NULL_NATURAL_MATERIALIZER_CREATED_FINAL_APPROVAL_CONSUMER_REJECTED_WATERMARK
IDENTITY = market-data-snapshot:v1:SHA256_CANONICAL_JSON
PRODUCER_INVARIANT = NATURAL_FINAL_APPROVAL_REQUIRES_VALID_VERSIONED_MARKET_DATA_SNAPSHOT_ID
CONSUMER_INVARIANT = MARKET_DATA_WATERMARK_MISMATCH_RETAINED_FAIL_CLOSED
MIXED_OUTCOME = HARD_ADAPTER_REJECTION_PRESERVED_WITH_PER_SYMBOL_RESULTS
OBSERVABILITY = STRUCTURED_CHANGED_CLASSIFICATION_INFO_REPEATED_DEBUG_AND_FUNNEL_PRODUCTION_ELIGIBILITY_FIELDS
MIGRATION = NONE
HISTORICAL_APPROVAL_BACKFILL = NONE
PRODUCTION_MUTATIONS = 0
LIVE_CHANGES = 0
RUNTIME_GATE_CHANGES = 0
TARGETED_TESTS = 1820_PASS
BROAD_TESTS = 6262_PASS_5_SKIP_4_DESELECT_WITH_2_PREEXISTING_FAILURES_AND_EXTERNAL_POSTGRES_SUITES_UNAVAILABLE
POSTGRES_E2E = NOT_EXERCISED_NO_ISOLATED_LOOPBACK_PAPER_TEST_DATABASE
ISOLATED_CHAIN = SNAPSHOT_ID_EQUALS_ANALYSIS_WATERMARK_FINAL_APPROVAL_CREATED_ADAPTER_ELIGIBLE_CANDIDATE_CREATED
COMMAND_ORDER_FILL_POSITION = NOT_EXERCISED
DEPLOYMENT = NOT_PERFORMED
PRODUCTION_IMAGES = UNCHANGED
PRODUCTION_CANARY = WAITING_FOR_ELIGIBLE_APPROVAL_COMMAND0_POSITION0
NEXT_ACTION = DEPLOY_IMPLEMENTATION_THEN_WAIT_FOR_NEW_NATURAL_APPROVAL_WITHOUT_REPLAYING_HISTORICAL_ROWS
```

## Root cause and correction

The confirmed diagnosis did not change. `MarketDataSnapshot` had no owned
identity, while `OnlineAnalysisRunner._source_id()` silently accepted that
absence. The resulting persisted analysis watermark was null. The natural
materializer nevertheless wrote a final approval, and the production adapter
correctly rejected it as `MARKET_DATA_WATERMARK_MISMATCH`.

`MarketDataSnapshot` now owns a deterministic versioned SHA-256 identity over
canonical JSON containing normalized symbol, timeframe, closed boundary,
snapshot source, and the strictly ordered closed candle market/provenance
fields. Receipt time, pipeline execution time, health/enough-data/gap flags,
host/process state, and other transient metadata are excluded.

`OnlineAnalysisRunner` propagates the typed snapshot identity without a broad
fallback. `NaturalFinalApprovalMaterializer` rejects a missing, empty, or
non-versioned watermark before creating the immutable approval triplet. The
watermark also participates in downstream materialization idempotency.

## Consumer and diagnostics

The production adapter watermark check remains unchanged and fail-closed for
historical, corrupt, manual, and incompatible payloads. Classification now
emits bounded structured fields at INFO only when the relevant approval/outcome
changes and DEBUG for repeated polling. Mixed outcomes retain a hard adapter
rejection instead of collapsing it into a generic wait. The read-only Funnel
adds production eligibility outcome, classification time, first rejection
reason, watermark, and validity deadline without changing upstream counts.

## Validation

- Identity determinism, candle sensitivity, transient metadata independence,
  and explicit ordering rejection pass.
- Pipeline construction exposes a versioned snapshot identity.
- Online analysis watermark equals the source snapshot identity.
- Missing watermark blocks final approval creation.
- Old defective approval remains `MARKET_DATA_WATERMARK_MISMATCH`.
- A real snapshot through online analysis, persisted pipeline materialization,
  and the production adapter produces an eligible candidate without a manually
  supplied watermark.
- Targeted/relevant regression: 1820 passed.
- Broader available regression: 6262 passed, 5 skipped, 4 deselected. Two
  isolated failures are pre-existing in untouched contracts: the current
  scalping risk fixture and a legacy expected Alembic head 0014 versus actual
  0015. External PostgreSQL suites could not run because no task-owned
  loopback `paper_test_*` database URL exists.

No migration, deployment, backfill, historical approval execution, command,
order, fill, position, production DB mutation, runtime gate change, or LIVE
change was performed.
