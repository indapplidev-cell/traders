# Exact row-to-detail identity — Task A

TASK_STATUS = COMPLETE
FINAL_VERDICT = PASS

LATEST_BY_SYMBOL_FALLBACK_FOUND = YES_REMOVED
STALE_DETAIL_CACHE_FOUND = YES_SYMBOL_ONLY_CLIENT_LOOKUP_REMOVED
ASYNC_RACE_FOUND = CLIENT_LOADER_ALREADY_GENERATION_GUARDED_AND_EXACT_SELECTION_NOW_FAILS_CLOSED
CROSS_PROFILE_CACHE_FOUND = POTENTIAL_PROFILE_SNAPSHOT_REUSE_NOW_REJECTED_BY_EXACT_IDENTITY

EXACT_IDENTITY_FIELDS = profile,timeframe,cycle_boundary_ms,symbol,source_run_id,opportunity_id,candidate_id,approval_id,plan_id
SERVER_EXACT_LOOKUP = PASS_CURRENT_ITEMS_AND_DETAIL_CANDIDATES_ARE_ONE_TO_ONE_CURRENT_CYCLE_ROWS
CLIENT_EXACT_BINDING = PASS_NO_SYMBOL_ONLY_DETAIL_LOOKUP
CLEAR_ON_SELECTION = PASS
ASYNC_STALE_RESPONSE_DISCARD = PASS

ROW_DETAIL_PARITY_TESTS = SERVER_52_PASS_CLIENT_FOCUSED_43_PASS_FRESH_EXACT10_JSONL_PASS
DESKTOP_INTERACTIVE_ACCEPTANCE = PASS_READONLY_PRODUCTION

STALE_DETAIL_AFTER = 0

The server previously preferred the newest historical PAPER plan or RR-reject
per symbol. The client then searched `detail_candidates` by symbol. Both paths
were removed. Current rows now carry an explicit immutable `row_identity`; an
empty downstream geometry remains empty for that same opportunity.

The frozen evidence is
`artifacts/test_scope_reconciliation_01/ROW_DETAIL_EXPECTED_IDENTITY.jsonl`:
10/10 rows from completed cycle `1789059300000` passed profile, timeframe,
cycle, symbol, source-run and candidate parity.

Read-only Desktop acceptance used PID 16000 / HWND 0x21052e after the mandatory
preflight before each action. LINK then DOGE showed their own 16:20Z row and
opportunity cycles; the 16:25Z refresh cleared the old selection; switching to
15m and back to Scalping left the Funnel with no cross-profile detail. Relevant
cropped capture SHA-256 values are `54880916...`, `913EBA51...`,
`13ADB72E...`, `381CBAF4...`; PAPER readiness capture is `BBCB4CE1...`.

SERVER_IMPLEMENTATION_COMMIT = 9076086
CLIENT_IMPLEMENTATION_COMMIT = 1698bac
SERVER_DEPLOYMENT = READONLY_ONLY_CONTAINER_457d08c_IMAGE_SHA256_08a3dc9c_RESTART0_HEALTHY
LIVE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
