# Task G — regression and production readonly reconciliation

```text
STATUS = PARTIAL_TEST_DEBT_ZERO_PRODUCTION_SAFETY_PASS_ARCHITECTURE_GATES_FAIL
YAML_RUNTIME_RESEARCH_FOCUSED = 108 passed
POSTGRES16_NON_SUPERUSER_E2E = 18 passed, 0 failed
MATERIALIZATION_FIXTURES = 29 passed
DESKTOP = 1509 passed, 2 pre-existing skips, 3029 subtests, 0 failed
COMPILE = PASS_SERVER_AND_DESKTOP
STATIC_REAUDIT = EXPECTED_FAIL_317_UNKNOWN
```

Production was observed read-only. Latest 5m boundary 1789014900000 has exactly
10 symbols, active Set #2 and hash
`536fd1adafe68f0c3f6095303fb3954b38196285ad66c656073516fbeed87839`.
Orchestrator and collector have restart count zero. Legacy 15m is exited with
restart=no; `online_pipeline_runs` remains 29345 rows, max id 89289, boundary
1788993000000, therefore zero new rows from the soak marker.

The current soak slice has 57/864 boundaries, expected/collected 570/570,
mature-missing 0, duplicates 0, predecision 0, V3 outcomes 227 and config drift
false. Cost evidence is authoritative Binance account commission (7.5 bps each
side in the sampled projection), Binance public spread/depth, YAML slippage and
YAML adverse reserve.

Readonly health returned OK/ready. PAPER readiness returned HTTP 200/READY but
WAL=false, PITR=false and approval-source=false, so mutation readiness is false
with the three explicit denial reasons. The readonly container showed restart
count 37 at reconciliation; no restart or deploy was performed by this task.
These operational facts and the 317 architecture unknowns prevent certification
that only YAML tuning remains.

Only tests, audit tooling and offline research finalization changed. Effective
production YAML/runtime behavior and soak hash did not, so `SOAK_CONTINUES_VALID`.
