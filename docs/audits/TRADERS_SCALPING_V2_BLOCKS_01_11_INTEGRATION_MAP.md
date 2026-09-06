# Scalping v2 Blocks 01-11 runtime integration map

Task: `TRADERS_SCALPING_V2_INTEGRATE_EXISTING_BLOCKS_01_11_THEN_CONTINUE_12_14_02`

Baseline source: `d937835c89d257f6723670fc54ee20f3f494741e`

Audit time: 2026-09-06 (Europe/Moscow)

## Baseline reconciliation

- Branch `feature/engine-platform` is synchronized with
  `origin/feature/engine-platform` at the baseline source.
- Blocks 01-11 and the original Block 12 commit all exist and are ancestors of
  the baseline source. No history rewrite or replacement implementation is
  required.
- Production PostgreSQL reports the single Alembic head
  `0026_scalping_1m_entry_refinement`.
- The running 5m image is `sha256:0a289fb9...` with source label
  `2c819282b25fd2700921a0f1289fbf96557b2142`, not the baseline source.
- A disabled-by-compose 15m service is nevertheless still running from an old
  container. It must be stopped during activation.
- The production database contains 52 closed `trade-5m-v2` PAPER positions,
  so real persisted outcomes exist for a bounded statistics adapter.

## Call-path map before integration fixes

| Component | Implemented | Wired | Persisted | Used by production runtime | Tested | Deployed | Proven call path / gap |
|---|---:|---:|---:|---:|---:|---:|---|
| Central config loader | YES | PARTIAL | N/A | PARTIAL | YES | NO | `trade_parameters.py` loads strict YAML and `trade_profile.py` / `runtime_parameters.py` consume many values. Several runtime cohort constants and startup evidence still bypass or omit the authoritative projection. |
| Profile registry | YES | YES | N/A | YES (old image) | YES | PARTIAL | `ACTIVE_RUNTIME_PROFILE_IDS` contains only `trade-5m-v2`; `trade-15m-v1` is disabled in YAML and compose profile, but its pre-existing container is still running. |
| Scheduler | YES | YES | PostgreSQL | YES (old image) | YES | PARTIAL | `ClosedWindowDetector` and `OrchestratorDaemon` carry the profile identity. Only the 5m scheduler is allowed after activation. |
| Pipeline runner | YES | YES | PostgreSQL | YES (old image) | YES | PARTIAL | `PipelineRunner` selects `ScalpingPaperRunner` for v2 and persists module payloads through `PipelineResultStore`. |
| Statistics source | NO | NO | Existing outcomes only | NO | NO | NO | Real closed PAPER outcomes exist, but no adapter supplies hierarchical buckets to admission. |
| Probability estimator | YES | NO | Diagnostic fields only | NO | Unit only | NO | `estimate_conservative_probability()` is implemented, but `ShadowGeometryConfig.empirical_bucket` remains `None` in production construction. |
| Economics / EV admission | YES | PARTIAL | Pipeline JSON | NO for statistical EV | Unit only | NO | Net-cost geometry runs; dynamic EV always fails closed without a bucket because no production statistics source is wired. |
| Cost model | YES | YES | Pipeline JSON | YES (older implementation) | YES | PARTIAL | Dynamic commission + public spread/depth + slippage are evaluated before plan readiness. Failure is fail-closed; adverse reserve is present in source but not deployed from current HEAD. |
| Causal registry | YES | PARTIAL | JSON bind-mounted path | PARTIAL | Unit only | NO | Registry survives restart, but a candidate is claimed before selector/execution and `record_execution()` has no production call path. It is therefore not yet durable execution dedupe. |
| PAPER closure hook | Existing lifecycle | NO diagnostics hook | PostgreSQL | NO for MAE/MFE | Existing lifecycle tests | NO | Position close/accounting is durable, but it does not invoke the Block 10 diagnostic processor. |
| MAE/MFE | YES | NO | Offline JSON only | NO | Unit only | NO | Pure computation and idempotent store exist; no bounded automatic closed-position processor exists. |
| 1m refinement ordering | YES | PARTIAL | PostgreSQL outcome fields | PARTIAL | Unit/integration fragments | NO | Executor invokes refinement for a selected candidate. Full integrated proof must show economics and causal admission precede selector and that SHADOW cannot alter baseline execution. |
| Readonly projection | PARTIAL | PARTIAL | Reads pipeline/position state | YES (old image) | Existing readonly tests | NO | Existing funnel exposes parts of geometry/cost/refinement, but required probability, EV, causal and diagnostic state semantics are incomplete. |

## Integration blockers and required fixes

1. Introduce a deterministic read-only statistics adapter over the existing
   PostgreSQL PAPER lifecycle, and inject its exact/parent buckets into the
   conservative estimator. No fake data or static-RR fallback is permitted.
2. Move causal duplicate authority to a server-owned PostgreSQL record tied to
   actual execution, or otherwise prove an atomic execution-time claim. A
   geometry preview must not consume execution authority.
3. Add an idempotent, bounded closed-position MAE/MFE processor and durable
   diagnostic projection, invoked by the PAPER lifecycle without mutating
   trading decisions.
4. Add integrated PostgreSQL E2E covering positive admission, negative EV,
   hierarchy/no-authority behavior, causal duplicate/reset, disabled profiles,
   command/open/close/accounting/diagnostics and 1m SHADOW ordering.
5. Complete readonly/Desktop provenance, build exact-source images, stop the
   stale 15m runtime, deploy only required services, and reconcile config hash,
   source label, safety, schema and tests.

## I1 verdict

`I1_STATUS = PASS_GAPS_IDENTIFIED_WITH_CALL_PATH_EVIDENCE`

`BLOCKS_01_11_IMPLEMENTED = YES`

`BLOCKS_01_11_INTEGRATED = NO`

`BLOCKS_01_11_DEPLOYED = NO`

`BLOCKS_01_11_RUNTIME_ACTIVE = NO`
