# TRADERS_CLIENT_SCALPING_FUNNEL_OPERATIONAL_UX_REFINEMENT_01 — FINAL

## Decision

The bounded operational UX refactor passed. The Desktop now keeps the complete
canonical 12-stage Scalping funnel in one visible matrix at the reference
content viewport, derives only adjacent presentation metrics from authoritative
same-unit counts, separates discovery attrition from the downstream bottleneck,
and preserves `Portfolio = Unavailable`. No trading rule, threshold, runtime,
collector semantic, Control state, or LIVE authority changed.

## Required final report

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_CLIENT_SCALPING_FUNNEL_OPERATIONAL_UX_REFINEMENT_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE

SERVER_HEAD_BEFORE = 933879f3b4a80597de9c244244a0e2c55d5435da
SERVER_HEAD_AFTER_IMPLEMENTATION = ba17a05c2786c7c4ca7f0ae45ef13f841509a88d
DESKTOP_HEAD_BEFORE = ad7813016b2ec907447aeeddf3054c4a5a9f5716
DESKTOP_HEAD_AFTER = 382522dc65fe0972a32118f31c25fa04f958f790
MOBILE_HEAD_BEFORE = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
MOBILE_HEAD_AFTER = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db

PRODUCTION_ALEMBIC_HEAD_BEFORE = 0018_promote_5m_production_search
PRODUCTION_ALEMBIC_HEAD_AFTER = 0018_promote_5m_production_search

SERVER_API_CHANGE = ADDITIVE_I18N_CATALOG_METADATA_ONLY_FUNNEL_DTO_UNCHANGED
READONLY_GET_ROUTES_AFTER = 28
WRITE_ROUTES_ADDED = 0
READONLY_API_BACKWARD_COMPATIBLE = YES

REFERENCE_VIEWPORT = 1200x760_DESKTOP_WINDOW_APPROX1000x680_CONTENT_VIEWPORT
FULL_12_STAGE_FUNNEL_VISIBLE_WITHOUT_INTERNAL_SCROLL_AT_REFERENCE_VIEWPORT = YES
ROLLING_1H_4H_READABLE = YES

STAGE_LOSS_VISIBLE = YES
STAGE_CONVERSION_VISIBLE_OR_ONE_ACTION_ACCESSIBLE = YES_VISIBLE
LOSS_CALCULATION_SEMANTICS = PREVIOUS_ADJACENT_AVAILABLE_SAME_UNIT_COUNT_MINUS_CURRENT_COUNT
CONVERSION_CALCULATION_SEMANTICS = CURRENT_COUNT_DIVIDED_BY_PREVIOUS_ADJACENT_AVAILABLE_SAME_UNIT_COUNT

DISCOVERY_ATTRITION_DISTINCT_FROM_DOWNSTREAM_BOTTLENECK = YES
DOWNSTREAM_BOTTLENECK_VISIBLE = YES
BOTTLENECK_TIE_HANDLING = FIRST_CANONICAL_DOWNSTREAM_STAGE_FOR_EQUAL_POSITIVE_LOSS_PERCENT

CURRENT_LAST_CYCLE_COMPACT = YES
CURRENT_PREVIOUS_COMPARISON_VISIBLE = YES_FACTUAL_SIGNED_DELTA

PER_SYMBOL_TERMINAL_REASON_READABLE = YES
SYMBOL_DETAIL_PANEL = PASS_TWO_COLUMN_BASIC_PLUS_EXPANDABLE_ADVANCED
TERMINAL_REASON_MACHINE_CODE_VISIBLE_OR_EXPORTABLE = YES
TERMINAL_REASON_HUMAN_LABEL_SERVER_AUTHORED = YES

PORTFOLIO_UNAVAILABLE_SEMANTICS_PRESERVED = YES
NULL_STATE_PRESENTATION_CONSISTENT = YES_ZERO_NA_UNAVAILABLE_UNDEFINED_DISTINCT
WINDOW_COMPLETENESS_VISIBLE = YES_ACTUAL_OVER_EXPECTED_CYCLES
FUNNEL_COUNTING_UNIT_EXPLICIT = YES_SYMBOL_EVALUATIONS_FROM_SERVER_DOWNSTREAM_COUNT_UNIT

FUNNEL_STAGE_RENDERER_SINGLE_SOURCE = YES_SERVER_CANONICAL_ORDER
DESKTOP_TRADING_DECISION_DERIVATION = NONE
DESKTOP_PRESENTATION_METRICS_ONLY = YES

REFRESH_SELECTION_STABILITY = PASS_SYMBOL_ID_SURVIVES_SOURCE_RUN_ID_CHANGE
REFRESH_FLICKER_MATERIAL = NO_IN_PLACE_STAGE_AND_SYMBOL_ROW_UPDATE
RESPONSIVE_LAYOUT = PASS_1000x680_1540x860_800x520_FALLBACK

RU_EN_KEY_PARITY = PASS
RU_EN_PLACEHOLDER_PARITY = PASS
DESKTOP_LOCAL_DOMAIN_TRANSLATION_MAPS_ADDED = 0

EXPORT_DERIVED_METRICS = YES_SUMMARY_JSON_AND_MARKDOWN_PRESENTATION_DIAGNOSTICS_MARKED_DERIVED
EXPORT_BACKWARD_COMPATIBLE = YES_RAW_JSONL_CSV_AND_SCHEMA_VERSION_UNCHANGED

NEW_N_PLUS_ONE = NO
EXTRA_REFRESH_HTTP_CALLS_MATERIAL = NO_ZERO_ADDED
DESKTOP_REFRESH_MATERIAL_REGRESSION = NO_10_SECOND_REFRESH_RENDER_MEDIAN75_246MS_MAX165_801MS

15M_FUNNEL_UI_REGRESSION = PASS
15M_TRADING_BEHAVIOR_CHANGED = NO
TRADE_15M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
SCALPING_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
SCALPING_PARAMETER_PROMOTION_BY_TASK = NO

NATURAL_5M_CURRENT_VERIFIED = YES_COMPLETE10_OF10
NATURAL_5M_LAST_VERIFIED = YES_COMPLETE10_OF10
ROLLING_1H_VERIFIED = YES_12_OF12
ROLLING_4H_VERIFIED = YES_48_OF48
EXACT10_SYMBOLS_VERIFIED = YES

15M_RUNTIME_RESTARTS_BY_TASK = 0
SCALPING_RUNTIME_RESTARTS_BY_TASK = 0
COLLECTOR_RESTARTS_BY_TASK = 0
CONTROL_RESTARTS_BY_TASK = 0
POSTGRES_RESTARTS_BY_TASK = 0
READONLY_REPLACEMENTS_BY_TASK = 1_ADDITIVE_SERVER_CATALOG

COLLECTOR_RUNNING_AFTER_TASK = YES_OWNER1_BOUNDARIES262_RECORDS4940
WAL_READY_AFTER = true
PITR_READY_AFTER = true
PHYSICAL_WAL_GAP_AFTER = false
ACK_OWNER_HEALTH_AFTER = PASS_PID27564_HEARTBEAT_FRESH_BACKLOG0_PENDING0

CONTROL_STATE_AFTER = ARMED
CONTROL_GENERATION_AFTER = 6
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0

SERVER_TESTS = PASS_FOCUSED39;FULL_REPO_DIAGNOSTIC30827_PASS30_SKIP_WITH_ENVIRONMENTAL_PG_GROUP_FAILURES_NON_TASK_GATE
DESKTOP_TESTS = PASS_1478_PASSED_2_SKIPPED_3029_SUBTESTS
I18N_TESTS = PASS_SERVER_GENERATED_BOOTSTRAP_RU_EN_KEYS_PLACEHOLDERS
15M_REGRESSION_TESTS = PASS_DESKTOP_FULL_SUITE_AND_LEGACY_PROFILE_RENDERER
SECURITY_SCANNER = PASS_BANDIT_HIGH0
SECRET_SCANNER = PASS_CHANGED_PATH_FINDINGS0
SECRET_OUTPUT = 0
SECURITY_FINDINGS = 0

SERVER_COMMITS = ba17a05c2786c7c4ca7f0ae45ef13f841509a88d
DESKTOP_COMMITS = 110230e71c9d47e0318c5d07c765e5130bde6f64,d49df541a026cae5f8aeb9257aedf4392628cec4,fe1f984a6ced6f04641af92e1a32850669ccba87,9857fd19324057e22f66b2a97f6061787e9b4e59,382522dc65fe0972a32118f31c25fa04f958f790
MOBILE_COMMITS = NONE

SERVER_ROOT_CLEAN_AFTER = PENDING_FINAL_RECONCILIATION
DESKTOP_ROOT_CLEAN_AFTER = YES
MOBILE_ROOT_CLEAN_AFTER = YES
PUSHED = NO

EVIDENCE_FILE = D:\disk_E\game_projects\traders\evidence_inbox\TRADERS_CLIENT_SCALPING_FUNNEL_OPERATIONAL_UX_REFINEMENT_01_FINAL.md
EVIDENCE_SHA256_RESOLUTION = Get-FileHash -Algorithm SHA256 EVIDENCE_FILE_AFTER_FINALIZATION

NEXT_ACTION = CONTINUE_SCALPING_COLLECTION_AND_USE_OPERATIONAL_FUNNEL_FOR_GEOMETRY_TARGET_NET_COST_RR_CALIBRATION_ANALYSIS
```

## Source and presentation semantics

The server continues to own stage order, counts, stage availability, count
units, terminal reason codes, and RU/EN labels. The client uses
`downstream_count_unit` to require identical units before calculating adjacent
loss or conversion. A missing/unavailable stage breaks the chain; the client
never jumps over Portfolio or another unavailable stage.

`Analysis qualified -> Structural setup` is displayed as Discovery attrition.
The downstream bottleneck ranking starts at `Structural setup -> Strategy
admitted`, ranks only positive loss percentages, excludes unavailable rows, and
uses canonical stage order as the deterministic tie breaker. These are
presentation diagnostics, not recommendations or trading decisions.

## Before / after visual evidence

Before: the accepted screen used a six-row `Stage | 1h | 4h` Treeview with an
internal vertical scrollbar. Current and previous cycles duplicated long
12-stage text lists above it; loss, conversion, window completeness, count unit,
and bottleneck were absent. The downstream rows required scrolling.

After: one 12-row matrix presents `Stage | Current | cycle delta | Previous |
1h | Attrition | Conversion | 4h | Attrition | Conversion`. Current/previous
metadata occupies two single-line panels. Discovery and 1h/4h downstream
bottlenecks are visible above the matrix. At `1000x680` content all 12 rows are
on-screen without funnel-internal scrolling; the lower detail area uses page
fallback only. At `1540x860` no page fallback is needed. At `800x520` the page
scrolls gracefully and labels do not overlap.

Natural RU screenshot:
`TRADERS_CLIENT_SCALPING_FUNNEL_OPERATIONAL_UX_REFINEMENT_01_AFTER_RU.png`,
SHA256 `B53619A4B2AE432847223856EFA0D2A493D85F3FE83C070E3C852D39C14B7149`.

Natural EN screenshot:
`TRADERS_CLIENT_SCALPING_FUNNEL_OPERATIONAL_UX_REFINEMENT_01_AFTER_EN.png`,
SHA256 `EC437966205777B10D877698CF2DE9AB7578E7E5159000B81072ECEA95C63861`.

Natural data showed exact-10 current and last cycles, 12/12 and 48/48 rolling
completeness, Discovery loss, RR as the largest downstream loss, and Portfolio
as `Unavailable`. No count was altered or synthesized.

## Refresh, export, and runtime

Stage and symbol rows update in place. Selection identity is the canonical
symbol, so a new `source_run_id` does not drop the selected detail. The existing
single GET refresh path is unchanged and no per-stage/per-symbol request was
added. Summary JSON/Markdown export receives additive `presentation_diagnostics`
containing window, machine stage code, server label, count, adjacent loss,
conversion, availability, bottleneck rank, machine reason, server reason label,
and `derived=true`; raw JSONL/CSV remains backward compatible.

One Readonly API container was narrowly replaced because the production server
catalog must author the new labels. It became healthy with restart count zero
and `28 GET / 0 write`. PostgreSQL, market data, 15m, 5m, collector, and Control
containers retained their existing uptime and restart-zero state. Production
Alembic remained `0018_promote_5m_production_search`. WAL/PITR remained ready,
physical WAL gap remained false, ACK owner remained healthy, Control remained
ARMED generation 6, and LIVE remained disabled.

## Validation note

All applicable changed-scope server tests passed (`39`). The unfiltered server
repository diagnostic completed with `30,827 passed, 30 skipped, 442 failed,
342 errors`; failures/errors are environment-dependent real-PostgreSQL and
cross-suite integration groups outside this i18n-only server change. They are
reported rather than hidden and are not used to promote unrelated behavior.
The complete Desktop suite passed (`1,478 passed, 2 skipped, 3,029 subtests`).
