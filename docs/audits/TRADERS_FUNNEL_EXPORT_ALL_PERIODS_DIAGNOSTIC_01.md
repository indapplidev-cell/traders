# Funnel export all-period diagnostic

FINAL_VERDICT = PASS_DIAGNOSIS_REPRODUCED; EXPORT_DEFECT_OPEN
SCOPE = Readonly production HTTP GET and existing Desktop source inspection; no GUI interaction, runtime restart, trading/configuration mutation, or implementation change.
SERVER_BASELINE = d18a26996c018eb6e92460ee41bb97fb2f3a5d30
CLIENT_BASELINE = ef0415c5756d26c1ca3a432217a8b70c86a78825

## Cause

Desktop `config/settings.py` limits responses to 2,000,000 bytes. `funnel_export.py` requests 200 records per page. Current enriched records exceed the byte limit before JSON parsing. TransportResponseTooLargeError is mapped to ProviderContractError and the Russian UI displays the generic «Ответ сервера несовместим» message. This is not evidence of an incompatible API schema. Unrestricted standard-library GET responses passed the actual FunnelExportPage parser.

Exact production provider reproduction for a four-hour request:
- page_size=200: ProviderContractError, The server response is too large.; diagnostic: response exceeded 2000000 bytes.
- page_size=50: PASS, 50 records, has_more=True.

## Period matrix

Production trade-5m-v2, all symbols, jsonl-records, first page at page_size=200. Captured around 2026-09-14 00:30 UTC. Counts vary with naturally arriving data. PASS here means first-page transport and schema, not completion of the entire historical export.

| Period | Bytes | Rows | More pages | Default client |
|---|---:|---:|---|---|
| Current UTC cycle interval | 311 | 0 | false | PASS (empty) |
| Last UTC cycle interval | 223745 | 10 | false | PASS |
| 1h | 2235965 | 110 | false | FAIL size |
| 4h | 4267034 | 200 | true | FAIL size |
| 12h | 4208875 | 200 | true | FAIL size |
| 24h | 4252391 | 200 | true | FAIL size |
| 7d | 3999441 | 200 | true | FAIL size |
| 30d | 4099040 | 200 | true | FAIL size |
| Custom 37.2 minutes | 1658153 | 80 | false | PASS |
| All, epoch to now | 4096612 | 200 | true | FAIL size |

Custom intervals are data-dependent: this short interval passed, longer intervals can hit the same limit. Cycle intervals were derived from UTC five-minute boundaries, not selected through the GUI. No full paginated history or all-format file acceptance claimed. Source confirms JSONL, summary JSON and summary Markdown request jsonl-records; CSV requests csv-records, routed to the same server page builder. All formats share the bounded JSON transport.

An initial ad hoc probe using +00:00 timestamps returned 422; it was discarded and every matrix request rerun using actual FunnelExportRequest.page_query (Z timestamps), matching Desktop behavior.

## Next action

Repair Desktop pagination to reduce page size adaptively on the specific oversized-response error, preserve cursor/snapshot/resume semantics, and expose an accurate size error if a single record cannot fit. Verify full exports and resumptions. Merely increasing the global transport limit or choosing a shorter interval is not a durable repair.

Existing WAL owner blocker and LIVE restrictions unchanged; no new readiness, deployment or soak acceptance asserted. Existing unrelated worktree artifact deletions left untouched. Diagnostic changes remain local; no push.
