# TRADERS_LEGACY_PG_FIXTURE_DEBT_TASK_E

```text
TASK_STATUS = PASS
FINAL_VERDICT = PASS_9_STALE_POSTGRES_FIXTURE_FAILURES_REDUCED_TO_ZERO
POSTGRES = 16_ALPINE_LOOPBACK_127.0.0.1_55441
DATABASE = paper_test_yaml_reverify
PRINCIPAL = paper_test_yaml_reverify_NONSUPERUSER_NOCREATEDB_NOCREATEROLE_NOREPLICATION_NOBYPASSRLS
ALEMBIC_HEAD = 0031_scalping_parameter_sets
PG_FAILURES_BEFORE = 9
PG_FAILURES_AFTER = 0
FULL_RELEVANT_E2E = 18_PASSED
PRODUCTION_MUTATIONS = 0
PRODUCTION_YAML_CHANGES = 0
ACTIVE_5M_SEMANTIC_CHANGES = 0
```

## Independent reproduction and classification

The suite was run against a fresh task-owned PostgreSQL 16 database through a
test-only principal.  The initial result was exactly `9 failed, 9 passed`.

| Test | Exact stale assumption observed | Classification | Reconciliation |
|---|---|---|---|
| `test_15m_first_class_gates_persist_and_project_on_fresh_postgres` | A disabled `trade-15m-v1` fixture attempted to persist a new runtime result without current runtime identity/provenance. | `STALE_15M_RUNTIME_ASSUMPTION` | Replaced by fail-closed proof: the schema stays readable, the profile is disabled, and no new 15m result is accepted. |
| `test_authoritative_refinement_rejection_creates_no_command_and_no_rank2_fallback` | The old narrow market vector no longer reached the intended refinement stage under the canonical Set #2 cost/RR gate. | `STALE_PRE_YAML_FIXTURE` | Widened only the deterministic market-data vector; policy remains resolver-owned. |
| `test_authoritative_refinement_waiting_then_expired_creates_no_command` | Same pre-YAML market vector stopped at economic geometry. | `STALE_PRE_YAML_FIXTURE` | Same current-policy-compatible market vector. |
| `test_continuous_v2_two_positions_without_rearm_postgres_e2e` | Old market vector, copied `10 bps` risk expectation, and no authoritative exit-commission snapshot. | `STALE_CONFIG_HASH_EXPECTATION`; `STALE_PROVENANCE_EXPECTATION` | Risk expectation now comes from `resolve_runtime_parameters`; exit commission is a typed authoritative test projection. |
| `test_continuous_budget_restart_pause_and_utc_reset_postgres_e2e` | Copied `50 bps` aggregate expectation assumed the earlier per-command risk. | `STALE_CONFIG_HASH_EXPECTATION` | Aggregate is derived from canonical `risk_per_trade_bps`; lifecycle assertions remain intact. |
| `test_natural_approval_opens_paper_position_end_to_end` | Old market/entry vector and missing current exit-commission authority. | `STALE_PRE_YAML_FIXTURE`; `STALE_PROVENANCE_EXPECTATION` | Updated only market inputs and supplied typed commission provenance derived from the canonical resolver. |
| `test_expired_natural_approval_does_not_create_command` | Old market vector failed before expiry logic. | `STALE_PRE_YAML_FIXTURE` | Current-policy-compatible market vector restores intended expiry coverage. |
| `test_selected_identity_mismatch_is_durable_and_creates_no_command` | Old market vector failed before identity mismatch handling. | `STALE_PRE_YAML_FIXTURE` | Current-policy-compatible market vector restores intended identity coverage. |
| `test_real_backup_blocker_is_durable_then_fixed_candidate_opens_position` | Old market vector and missing exit commission prevented the post-blocker lifecycle path. | `STALE_PRE_YAML_FIXTURE`; `STALE_PROVENANCE_EXPECTATION` | Current market vector plus typed commission projection restores the readiness/backup assertion. |

No assertion was converted to `xfail` or `skip`.  The final run preserved
PostgreSQL persistence, exact migration head, frozen Set #2 provenance,
fail-closed 15m behavior, profile isolation, PAPER command/position lifecycle,
commission provenance, reconciliation, and restart/idempotency coverage.

## Final command and result

```text
PAPER_NATURAL_E2E_DATABASE_URL=<task-owned-loopback-url> \
python -m pytest tests/integration/paper_natural_execution_e2e -q

18 passed, 1 warning in 50.33s
```

The warning is Alembic's non-failing `path_separator` deprecation notice; it is
not a test failure and does not affect schema or runtime semantics.
