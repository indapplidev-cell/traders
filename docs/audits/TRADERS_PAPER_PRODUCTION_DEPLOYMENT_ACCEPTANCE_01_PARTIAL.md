# TRADERS PAPER production deployment acceptance 01

Reconciled at `2026-08-30T11:42:30Z`.

## 1. Deploy necessity

```text
DEPLOY_REQUIRED = YES
```

Production uses Docker Compose. The running 15m orchestrator was built from
`8b446e09ba39e1a40aeedcf594e14f86c856431f`, the 5m orchestrator from
`c30dd05ab55a102f787be3e9ec1fac6c78d71619`, Operator Control from
`9fe3a4f1dba41c054cd5003e589ac72ba21394f5`, and Readonly from
`74e1188cc11b813e9d4bfa3c07d496003fe7126c`. Direct byte hashes from all four
running containers differed from the tested PAPER watermark tree. The running
artifacts therefore did not contain the fix.

The runtime mapping was:

- `online-orchestrator` and `online-orchestrator-5m`: market snapshot creation,
  analysis watermark propagation, pipeline persistence, PAPER plan and final
  approval materialization;
- `operator-control-api`: approval adapter, selector/canary continuation,
  PAPER executor, and lifecycle worker;
- `readonly-api`: approval/funnel observation and the read-only PAPER/UI
  projection;
- `market-data-sync`: candle synchronization only; it does not construct a
  `MarketDataSnapshot` in its running entrypoint and was not restarted.

## 2. Provenance

```text
TESTED_SHA = fbcb46cec928b22c2c5e987e5ad66ad4c231cf6d
DEPLOY_SHA = d7d072df4b924d675c4bb1de447635f0b6b0e41d
RUNNING_SHA = d7d072df4b924d675c4bb1de447635f0b6b0e41d
DIFF_TESTED_TO_DEPLOY = FINAL_DECISION.md, docs/audits/TRADERS_PAPER_NATURAL_EXECUTION_POSTGRES_E2E_01_FINAL.md, online_trader.md
EXECUTABLE_DIFF = NO
ORCHESTRATOR_IMAGE_TAG = traders-paper-runtime:d7d072df4b924d675c4bb1de447635f0b6b0e41d
ORCHESTRATOR_IMAGE_DIGEST = sha256:85c36e2c8474954c7e509bc9a91bf33c2759cf8d570d60179932acdc24c44612
CONTROL_IMAGE_TAG = traders-operator-control-api:d7d072df4b924d675c4bb1de447635f0b6b0e41d
CONTROL_IMAGE_DIGEST = sha256:b7d50beeb5e9286bf2582216dd0d575335e8f0bdf37047e02ce9ffe57d95b80c
READONLY_IMAGE_TAG = traders-readonly-api:d7d072df4b924d675c4bb1de447635f0b6b0e41d
READONLY_IMAGE_DIGEST = sha256:96ef6773189d69d79a2b68de3e4491ad70a1d6210d7ff316b04fcbffa042fd4d
```

`fbcb46c..d7d072d` contains documentation only. The application, scripts,
migrations, Dockerfiles, Compose definitions, requirements and project metadata
have no diff. All eleven changed executable/read-model files were byte-identical
between the clean build context and each applicable built image. All three
images passed `compileall`. Each image carries
`org.opencontainers.image.revision=d7d072df4b924d675c4bb1de447635f0b6b0e41d`.

Rollback artifacts were tagged and verified before replacement:

```text
15M_PREVIOUS_SHA = 8b446e09ba39e1a40aeedcf594e14f86c856431f
15M_PREVIOUS_IMAGE_DIGEST = sha256:09ac8432f00325532e209896d263595cfac2f00d8385ce19da2c4b7098b26731
15M_ROLLBACK_TAG = traders-ml-online-orchestrator:rollback-paper-watermark-8b446e09
5M_PREVIOUS_SHA = c30dd05ab55a102f787be3e9ec1fac6c78d71619
5M_PREVIOUS_IMAGE_DIGEST = sha256:cfaa97127236222cef0476acc099b10257f2abaad9ca3ca82890b24746db81c6
5M_ROLLBACK_TAG = traders-ml-online-orchestrator-5m:rollback-paper-watermark-c30dd05a
CONTROL_PREVIOUS_SHA = 9fe3a4f1dba41c054cd5003e589ac72ba21394f5
CONTROL_PREVIOUS_IMAGE_DIGEST = sha256:a4664ff5c34844c59f89224369cda859b72d30c27663b7b2ff1a128626590f39
CONTROL_ROLLBACK_TAG = traders-operator-control-api:rollback-paper-watermark-9fe3a4f1
READONLY_PREVIOUS_SHA = 74e1188cc11b813e9d4bfa3c07d496003fe7126c
READONLY_PREVIOUS_IMAGE_DIGEST = sha256:ec832722bec3659c197f3e5f6af0a9361919139ec5a56e3597515cf7612bced2
READONLY_ROLLBACK_TAG = traders-readonly-api:rollback-paper-watermark-74e1188c
```

Rollback requires no Alembic downgrade, data deletion, approval replay, or
other destructive operation.

## 3. Deploy scope

| Service | Old artifact | New artifact | Restarted | Result |
|---|---|---|---|---|
| `online-orchestrator` | `sha256:09ac8432...` | `sha256:85c36e2c...` | YES | RUNNING, restart 0 |
| `online-orchestrator-5m` | `sha256:cfaa9712...` | `sha256:85c36e2c...` | YES | RUNNING, restart 0 |
| `operator-control-api` | `sha256:a4664ff5...` | `sha256:b7d50bee...` | YES | HEALTHY, restart 0 |
| `readonly-api` | `sha256:ec832722...` | `sha256:96ef6773...` | YES | HEALTHY, restart 0 |

`market-data-sync`, PostgreSQL and the calibration collector were not restarted.
The deployment used the project's Compose boundaries with `--no-build`,
`--no-deps`, and narrow service replacement after the immutable images had
already been built and verified.

## 4. Safety state

```text
LIVE = false
Control = ARMED generation 6, HEALTHY, audit PASS
Canary = WAITING_FOR_ELIGIBLE_APPROVAL, max commands 1, max positions 1, used 0/0
WAL = true, wal_level replica, archive_mode on, ACK owner healthy
PITR = true, lineage valid, physical gap false, backlog/pending 0/0
Schema head = 0018_promote_5m_production_search
Schema head count = 1
Migration for fix = NONE
Commands before = 0
Positions before = 0
Orders before = 0
Fills before = 0
```

The same counters remained zero immediately after deployment. No downgrade,
schema mutation, canary reset, limit expansion, permission weakening, LIVE
activation, or push occurred.

## 5. Deployment result

```text
DEPLOYMENT_RESULT = DEPLOYED
RUNNING_ARTIFACT_MATCH = PASS
RUNTIME_HEALTH = PASS
POST_DEPLOY_SMOKE = PASS
ROLLBACK = NOT_REQUIRED
```

Operator Control retained `ARMED` generation 6 and reported 3 GET/5 POST routes,
valid read access, rejected unauthenticated and invalid-token mutations, and the
new source identity. Readonly remained GET-only and healthy. Market and approval
adapters, schema, reconciliation, WAL and PITR all reported ready. There were no
new deployment-related `ERROR`, `CRITICAL`, traceback, permission, serialization
or schema-incompatibility log matches.

## 6. Fresh natural approval

```text
pipeline_run_id = PENDING
snapshot_id = PENDING
analysis_id = PENDING
paper_plan_id = PENDING
approval_id = PENDING
valid_until_ms = PENDING
```

Nine natural 5m pipeline results completed after the new 5m container's exact
`StartedAt`. All nine persisted a valid
`market-data-snapshot:v1:<64 lowercase hex>` analysis watermark. None produced a
PAPER plan or final approval, which is normal strategy output and not a failure.

Persisted equality proof for the latest SUIUSDT result:

```text
pipeline_run_id = orchestrator:8cf1a28f3c1f47a4911f12852e09a9ca
MarketDataSnapshot[5m].snapshot_id = market-data-snapshot:v1:4f7ec6dadfd0dc46f816358a62da79aeea53ddeb582f30b6fda5a9044c6c4ac0
AnalysisSnapshot.source_market_data_snapshot_id = market-data-snapshot:v1:4f7ec6dadfd0dc46f816358a62da79aeea53ddeb582f30b6fda5a9044c6c4ac0
equal = true
final_approval_generation.outcome = NOT_ELIGIBLE
```

This proves that production accepts and persists the new snapshot contract. It
does not close PAPER execution acceptance because no fresh natural approval
exists yet.

## 7. Production execution trace

```text
adapter_outcome = PENDING_FRESH_APPROVAL
candidate_id = PENDING
winner = PENDING
command_id = PENDING
entry_order_id = PENDING
fill_id = PENDING
position_id = PENDING
position_state = PENDING
```

## 8. Database proof

| Table | Relevant row | State |
|---|---|---|
| `paper_execution_commands` | none | count 0 |
| `paper_orders` | none | count 0 |
| `paper_fills` | none | count 0 |
| `paper_positions` | none | count 0; OPEN 0 |

## 9. UI proof

```text
active_positions = 0
command_id = PENDING
position_id = PENDING
symbol = PENDING
entry_price = PENDING
state = PENDING
```

The Readonly projection is healthy and correctly shows no position. UI
acceptance remains pending the same future OPEN position.

## 10. Historical approvals

```text
historical defective approvals = 37
historical defective approvals modified = NO
replayed = NO
backfilled = NO
analysis source watermark NULL = 37/37
final approval source watermark NULL = 37/37
```

Immutable exclusion set:

```text
orchestrator:5dc369d7a2e74ebc951368419bfb177c
orchestrator:a86955c752ec4262917114d9d456334e
orchestrator:85704c635508402e98d26203e2f95936
orchestrator:9fcacb0296a64c8882d38d3bbe9f4dca
orchestrator:248f75d98b1741fb91ff2d3daef110b5
orchestrator:9d30198a54cc474cb0afb5e20dec2088
orchestrator:3c0f7e738d6b42129cbb9d2a3797409e
orchestrator:c172b8e06b354f21bf7db770a98d2f60
orchestrator:38e0f9c8d64d4aafad80762854fd94ac
orchestrator:1e53102e3f3e4642b03138f0eec39e8d
orchestrator:faa51dca02df49e49e4e71bc64eee76b
orchestrator:6bb02e2276164e869fd59673db871d32
orchestrator:2b982e4c8f97463691dde41e5fee4c2f
orchestrator:aca3d88cc2e8465da45bafd29fd69ce1
orchestrator:25941c4fa61a46dd93be50d87c7086a6
orchestrator:510bd573f89345c589f86f1a43f41421
orchestrator:21b5a0108c164f7fb284bb24ccdd9da0
orchestrator:fbfc7b42a350419aa924ed05dc54b33c
orchestrator:a9a4f679beaa4cfda801c41d4a80e021
orchestrator:4eb1251a584d477d8bc9e8b57aafd111
orchestrator:068b527f27f0488ba870f8faf3e8a490
orchestrator:321e450cfd3b46548be8a8212ab4164a
orchestrator:7a3da45a8b9648aeb97ddbdf830cd56b
orchestrator:1236eb65481a43a1bafc6ff1c2c5d2cc
orchestrator:976509b8cf674bb2b35aca5c5438d529
orchestrator:f1e35e80b5504748af1bbfcaf0ad2d81
orchestrator:3abcb19a8b884a2896a1970cb221c8b2
orchestrator:0c8ff87d10494384875e9b0b7a9bb9d1
orchestrator:cec55bf7bddf4dad8634ef7932322e48
orchestrator:2846ae9ff21d47bf9384e496704b5ffd
orchestrator:ee73dea9c30142f58cbe64a2c500fee8
orchestrator:be3a27509f474f1ebdf94c902d9944ba
orchestrator:9f78b2686858411ebb9f3d4b2cf90b99
orchestrator:6935890c676344f0b3c93e04bd9fe1c9
orchestrator:f122af2bba724919a5578796be342e31
orchestrator:2a43ce2710174450a376f50a7e028f47
orchestrator:c98dcf90caab427aa5dbf555c21ef41a
```

## 11. Logs/errors

```text
NEW_DEPLOYMENT_RELATED_ERROR_CRITICAL = NONE
PERMISSION_ERRORS = NONE
SERIALIZATION_OR_SCHEMA_INCOMPATIBILITY = NONE
```

## 12. Final verdict

```text
FINAL_VERDICT = DEPLOY_SUCCESS_WAITING_FOR_NATURAL_APPROVAL
```

Production acceptance remains open. It may close only after one fresh natural
post-deploy approval reaches `ELIGIBLE_APPROVAL`, selector winner, command,
ENTRY order, simulated fill, persisted OPEN PAPER position, and visibility of
that same position through the Readonly projection. Strategic filters must not
be weakened and no artificial production trade may be created.
