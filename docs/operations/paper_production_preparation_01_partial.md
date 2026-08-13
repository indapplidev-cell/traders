# Production PAPER preparation 01 partial result

Task: `TRADERS_ML_PAPER_TRADING_PRODUCTION_PAPER_PREPARATION_01`

Observed at: `2026-08-13T12:52:04Z`

## Result

```text
TASK_STATUS = FAILED_PARTIAL
BLOCKER_CODE = CURRENT_PRODUCTION_PREPARATION_REQUIRES_SOURCE_REMEDIATION
STOP_CONDITION = UNPLANNED_SOURCE_CHANGE_REQUIRED
PRODUCTION_ALEMBIC_BEFORE = 0008_engine_orchestrator_freshness_retry
PRODUCTION_ALEMBIC_AFTER = 0013_paper_first_canary_correlation
PRODUCTION_MIGRATION_COMPLETED = YES
PRODUCTION_EXECUTOR_ACTIONS_COMPLETED = 0
PRODUCTION_RUNTIME_ROLE_PRESENT = NO
PRODUCTION_RUNTIME_BINDING_PRESENT = NO
PRODUCTION_BASELINE_COUNT = 0
PRODUCTION_CONTROL = DISABLED_GENERATION_3
PRODUCTION_PAPER_RUNTIME = OFF
PRODUCTION_OPERATOR_CONTROL_API = NOT_DEPLOYED
PRODUCTION_READONLY_API = 18_GET_0_WRITE_HEALTHY
PRODUCTION_PAPER_LIFECYCLE_ROWS = 0
LIVE_MODE = OFF
BINANCE_ORDER_API_CALLS_BY_TASK = 0
WAL_PITR = PASS_CONTINUOUS_190180_SECONDS_NO_PHYSICAL_GAP
```

All pre-execute gates passed, including identity, frozen migrations, WAL/PITR,
focused/security tests, secret-free production status and plan, and isolated
PostgreSQL 16 production-style status/plan/execute rehearsal. The authorized
production execute migrated the schema transactionally from revision 0008 to
0013. The executor then failed closed before its first action with exit code 4.

Current diagnostics prove that `traders_readonly_api` has only its three
pre-existing non-PAPER SELECT grants (`candles_15m`,
`online_pipeline_results`, and `online_pipeline_runs`). The production
preparation backend incorrectly classifies those legitimate grants as broader
than the PAPER-only preparation contract. The runtime role therefore remains
absent and no runtime grant, credential binding, baseline, runtime deployment,
control transition, PAPER lifecycle row, LIVE transition, or order call was
created.

After the successful migration, the normal production `status` command also
fails target verification because its target guard remains fixed to expected
revision 0008. Both findings require source remediation before the bounded
production preparation can safely resume. No manual privilege change,
downgrade, ad hoc DDL, destructive cleanup, or secret workaround was used.
