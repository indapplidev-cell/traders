# Production DB credential rotation and safe shared-client rebind

## Verdict

`TRADERS_PRODUCTION_DB_CREDENTIAL_ROTATION_INVALIDATION_AND_SAFE_SHARED_CLIENT_REBIND_01`
completed with PASS. The exposed principal was `traders_ml`; the affected
clients were market-data, 15m, and 5m. Readonly and Control use the unaffected
`traders_readonly_api` and `traders_paper_runtime` principals.

The new credential was created without output, stored only in the ignored,
Docker-excluded, ACL-restricted binding
`.secrets.production.local/shared-db-password`, mounted read-only, and removed
from Docker `Config.Env`. All three affected clients retained their prior image
IDs, established fresh DB sessions, and passed real SQL queries. A fresh old
credential connection was rejected with SQLSTATE `28P01`; a fresh new
credential connection was accepted.

## Client acceptance matrix

| client | principal | new binding loaded | reconnect | DB query | health | old credential rejected |
|---|---|---:|---:|---:|---:|---:|
| market-data-sync | traders_ml | YES | YES | PASS | PASS | YES |
| online-orchestrator-5m | traders_ml | YES | YES | PASS | PASS | YES |
| online-orchestrator (15m) | traders_ml | YES | YES | PASS | PASS | YES |

## Continuity and safety

- 15m: three natural boundaries from 15:15 through 15:45 UTC, all exact10;
  missing/duplicate/batch anomalies `0/0/0`.
- 5m: seven natural boundaries from 15:15 through 15:45 UTC, all exact10;
  missing/duplicate/batch anomalies `0/0/0`; singleton owner count 1.
- Schema remained `0018_promote_5m_production_search`.
- WAL/PITR/ACK remained healthy with backlog/pending/unresolved `0/0/0`, valid
  lineage and no physical gap.
- Readonly remained HTTP 200 with 28 GET and zero write routes.
- Control remained ARMED generation 6; canary remained
  `WAITING_FOR_ELIGIBLE_APPROVAL`; LIVE remained disabled.
- Commands and positions remained `0/0`; no Control POST, trading mutation, or
  Binance order call occurred.
- Docker restart-count deltas were all zero. Market-data, 15m, and 5m each had
  one narrow container replacement; PostgreSQL, Readonly, and Control had none.
- Exact new-secret scan found zero tracked, evidence, or task-log findings.

## Validation

Focused security/DB-binding/Readonly regression: 656 passed. Broad affected
regression: 2099 passed, 13 skipped, with one unrelated historical audit test
whose fixed old baseline sees a previously existing `production_market_data.py`
change; changed-path regression failures are zero. Compose validation, tracked
secret policy, compile, protected binding verifier, exact-secret scanner, live
DB queries, old-auth negative proof, and operational gates passed.

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_PRODUCTION_DB_CREDENTIAL_ROTATION_INVALIDATION_AND_SAFE_SHARED_CLIENT_REBIND_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
PRODUCTION_DB_CREDENTIAL_INCIDENT_CLOSED = YES
PRODUCTION_DB_CREDENTIAL_ROTATION_COMPLETED = YES
OLD_CREDENTIAL_INVALIDATED = YES
SHARED_CLIENTS_REBOUND = YES
OLD_SECRET_VALUE_OUTPUT = 0
NEW_SECRET_VALUE_OUTPUT = 0
PROTECTED_SECRET_VALUE_OUTPUT = 0
SECRET_DERIVED_HASH_CREATED = NO
SECRET_LOGGING_IMPLEMENTED = NO
PROJECT_STATE_COMMIT_RESOLUTION = git log -1 --format=%H -- docs/audits/TRADERS_PRODUCTION_DB_CREDENTIAL_ROTATION_INVALIDATION_AND_SAFE_SHARED_CLIENT_REBIND_01_FINAL.md
NEXT_ACTION = TRADERS_5M_SCALPING_EXTENDED_UNIQUE_OPPORTUNITY_SHADOW_OBSERVATION_01
```
