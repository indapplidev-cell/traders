# Runtime configuration epoch and Funnel acceptance

FINAL_STATUS = PASS
FINAL_VERDICT = PASS_ALL_A_B_C

TASK_A_STATUS = PASS
TASK_A_ROOT_CAUSE = YAML copied into stale Docker image (COPY config ./config); no config bind mount. Running source 50b682886e953064a8b90f76213fd646d7926b42 resolved old values. First activation exposed a second blocker: ShadowGeometryConfig rejected continuous active stop/target/RR values against fixed research cohorts.
TASK_A_FIX = Rebuild only 5m PAPER runtime; validate active geometry as finite positive values and preserve the existing 0.2 RR floor. Shadow comparison cohorts unchanged.
RUNTIME_RESTART_OR_REDEPLOY = TARGETED_5M_AND_READONLY_API_RECREATE
RUNTIME_ACTIVE_CONFIG_HASH = 786150d22035f20b7d4a56b2e3ee27ee29c829ea44d70de1a6a6258001b47092
RUNTIME_ACTIVATED_AT = 2026-09-13T19:30:41.638341+00:00
RUNTIME_CONTAINER_STARTED_AT = 2026-09-13T19:30:16.283866521Z
RUNTIME_SOURCE_COMMIT = 8e629b12d3fa078ba41a034fa7efdc6fc3a220f4
RESOLVED_MIN_NET_EDGE_BPS = 73.004386
RESOLVED_MINIMUM_PLANNED_RR = 1.953403
RESOLVED_STOP_MAX_BPS = 48.496589
RESOLVED_TARGET_MIN_BPS = 49.163216
OLD_VALUES_ACTIVE_AFTER = NO
RUNTIME_SYMBOL_HARDCODES = 0_IN_CONFIGURATION_RESOLUTION
RUNTIME_SYMBOL_OVERRIDES = 0

A natural activation proof preceded B: all ten rows at 19:05 UTC had the new frozen hash and four exact values. BNB/LINK/XRP geometry diagnostics independently recorded the new edge/RR/stop values. Historical rows at 18:55 retain their old hash and values. The failed first recreation was stopped, fixed, tested and replaced; final containers have restart count zero.

TASK_B_STATUS = PASS
CONFIG_PROVENANCE_MODEL = Frozen ConfigurationEpoch captured from decision runner ResolvedParameterSet; persisted inside module JSON; API/export reads persisted object only.
CONFIG_CONTENT_HASH_ALGORITHM = Existing resolver full deterministic SHA256 semantic authority hash of resolved parameters.
CONFIG_EPOCH_SEMANTICS = SHA256(content hash + NUL + snapshot load UTC); content and activation are distinct; cached retries retain their original snapshot; A/B/A reactivation creates a new epoch.
CONFIG_EPOCH_ID = d05f23b0f460e0ff3aa2f68ba893d40f0be42b7901d231c3547f4fde3a378a8f
EFFECTIVE_PARAMETERS_ON_EVERY_ROW = YES_20_OF_20
LEGACY_PARAMETER_SET_HASH_HANDLING = Retained compatibility field; canonical consumers use effective_configuration.config_content_hash. Historical rows without persisted epoch remain null, never relabelled.
EXPORT_SCHEMA_VERSION = trading-funnel-export-v1_ADDITIVE_HTTP_AND_DESKTOP_COMPATIBILITY_TESTED

B natural acceptance preceded C: 19:15 UTC, ten rows, one epoch, source 8515f1582811030f102b4e0e57908131ff596e08 and all four values. In-flight rows can temporarily have no result; acceptance uses completed cycles only and does not fabricate their identity.

TASK_C_STATUS = PASS
CANONICAL_FUNNEL_STATE_MODEL = frozen StageResult(stage_id,reached,status,reason_code,raw_reason,terminal,phase)
DOWNSTREAM_TRACE_SOURCE = canonical_stages over persisted gate evidence
FUNNEL_TRACE_SOURCE = same StageResult tuple; APPROVED/WAIT are explicitly compatibility aliases; canonical_status carries exact state.
TRACE_MISMATCH_COUNT_BEFORE = 13_ON_10_ROW_B_CYCLE_FULL_SHARED_STAGE_MAPPING
TRACE_MISMATCH_COUNT_AFTER = 0_ON_20_ROWS
SCREEN_EXPORT_MISMATCH_COUNT = 0
GENERIC_UNAVAILABLE_ROOT_CAUSE = Independent analytics flags lost setup/target reachability; nullable Desktop formatter conflated absent fields, not reached and not applicable; exporter read nonexistent top-level analysis fields.
GENERIC_UNAVAILABLE_FOR_TYPED_STATES_AFTER = 0_ACROSS_924_REAL_SCREEN_FIELDS
ATR_PCT_SEMANTICS = Actual persisted quality_basis.impulse_context.atr_pct; zero preserved.
DIRECTION_CONFIDENCE_SEMANTICS = NOT_EVALUATED; no separate direction-confidence estimator; regime confidence is not substituted.
LIQUIDITY_STATE_SEMANTICS = NOT_EVALUATED; no categorical analysis liquidity classifier. Real fee/book authority remains separate.
STRUCTURE_STATE_SEMANTICS = Actual unified_context.altunina_context.structure_direction retained by online analysis projection.
VOLUME_STATE_SEMANTICS = Categorical state NOT_EVALUATED; actual calculated volume_context preserved separately without an invented classifier.
FOUR_HOUR_SEMANTICS = NOT_APPLICABLE; v2 requires 1m/5m/15m/1h; null timestamp preserved.
DYNAMIC_BINANCE_FEE_REGRESSION = PASS
FEE_FALLBACK_EXECUTABLE_BEHAVIOR = Existing fail-closed policy unchanged; configured fallback cannot become authoritative.

Terminal rejection truncates downstream decision reachability. Command/position/exit facts use a separate typed LIFECYCLE phase, sourced from persisted identifiers, not inferred from planner success. Historical 15m projection remains on its original compatibility path. No trading formula, selector, risk sizing or portfolio policy was changed.

REAL_ACCEPTANCE_EXPORT = artifacts/runtime_config_epoch_funnel_01/trading-funnel-trade-5m-v2.jsonl
REAL_ACCEPTANCE_ROWS = 20
REAL_ACCEPTANCE_SYMBOL_COVERAGE = ADAUSDT,AVAXUSDT,BNBUSDT,BTCUSDT,DOGEUSDT,ETHUSDT,LINKUSDT,SOLUSDT,SUIUSDT,XRPUSDT
REAL_ACCEPTANCE_CYCLES = 2026-09-13T19:35:00Z;2026-09-13T19:40:00Z
LIVE_STATE = DISABLED
BINANCE_ORDER_CALLS = 0
FIFTEEN_MINUTE_PROFILE_CHANGED = NO
ALEMBIC = 0031_scalping_parameter_sets_UNCHANGED
TESTS = SERVER_FOCUSED98PASS;DESKTOP28PASS
COMPILE = PASS

The old general export suite separately reports six retired trade-5m-v1 compatibility failures (missing runtime registry), also documented before this task; these are not counted as green tests. Current v2 HTTP/export/projection tests pass. No broad backtests or research search were run.

Desktop acceptance: current source client 6e4817de476e15cdb2f16554befe41475d962afe, PID 22004, HWND 3802092; preflight passed session/desktop/integrity/foreground/responsiveness and full-desktop crop. Fresh 19:35 BTC detail visually displayed “Этап не достигнут”. Screenshots remain in OS temporary storage, not Git. Browser actions and trading mutation controls were not used.

FILES_CHANGED = Dockerfile; app/engine_paper/scalping_shadow.py; app/engine_orchestrator/config_epoch.py; app/engine_orchestrator/pipeline_runner.py; app/engine_analysis/online_runner.py; app/server_api/effective_configuration.py; app/server_api/funnel_state.py; app/server_api/funnel_fields.py; app/server_api/funnel_export.py; app/server_api/trading_funnel.py; app/server_api/schemas/models.py; app/i18n/catalog.py; tests/engine_orchestrator/test_runtime_config_epoch.py; tests/server_api/test_funnel_epoch_parity.py; tests/server_api/test_trading_funnel.py; tests/test_scalping_independent_profile_v2.py; scripts/audit_runtime_config_epoch_funnel.py; task audit/evidence; online_trader.md. Client: ui/trading_funnel_view.py; generated i18n bootstrap; tests/test_funnel_typed_states.py; client_status.md.
COMMITS = A802df7d;B8515f15;C8e629b1;CLIENT6e4817d; acceptance and reconciliation resolved by Git.
PUSH = See final Git handoff; this report does not claim remote state before push.
AHEAD_BEHIND = See final Git handoff.
WORKTREE = 92 pre-existing user-owned artifact deletions preserved and not staged.
REMAINING_BLOCKERS = No A/B/C blocker; WAL/PITR false at reconciliation; LIVE promotion unauthorized; new configuration does not inherit prior-epoch soak acceptance.
NEXT_ACTION = Continue separate PAPER forward observation grouped by config_content_hash/config_epoch_id; independently resolve WAL/PITR readiness before any execution/readiness promotion.
