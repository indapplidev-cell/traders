# Desktop 24h dual-profile Funnel export failure diagnosis — FINAL

## Verdict

`FAIL_PRODUCTION_DESKTOP_EXPORT_ACCEPTANCE_BLOCKED`.

The 24-hour report cannot currently be downloaded by the production desktop
client in either **Scalping** (`trade-5m-v1`) or **Trade 15m**
(`trade-15m-v1`). The server response is valid, but a 200-record page is larger
than the client's configured two-million-byte response ceiling. The client
therefore raises `ProviderContractError`, rendered in Russian as
`Ответ сервера несовместим`.

## Screenshot correlation

The server access log contains the screenshot request:

```text
profile = trade-5m-v1
from = 2026-08-26T14:46:23.657396Z
to = 2026-08-27T14:46:23.657396Z
format = jsonl-records
page_size = 200
completed = 2026-08-27T14:46:41.728218774Z
HTTP = 200
```

The approximately 18.071-second cold completion also exceeded the client's
fixed 10-second per-page timeout. A later retry can receive the completed
single-flight/cache result and then fail on the independent response-size
limit, matching the final contract-class message shown in the screenshot.

## Exact production reproduction

The reproduction used the checked-in desktop `ServerProvider`,
`UrllibJsonTransport`, `FunnelExportRequest`, and `FunnelExportPage.parse`
against `http://127.0.0.1:8765`; no direct database access or mutation was
performed.

| Profile | HTTP/schema/profile | Rows | UTF-8 bytes | Client limit | Result through exact client |
|---|---|---:|---:|---:|---|
| `trade-5m-v1` | 200 / v1 / match | 200 | 3,515,001 | 2,000,000 | `ProviderContractError: response too large` |
| `trade-15m-v1` | 200 / v1 / match | 200 | 3,991,244 | 2,000,000 | `ProviderContractError: response too large` |

The active client settings file confirms `timeout_seconds=60.0`,
`max_response_bytes=2000000`, and production Readonly HTTP mode. Export pages
override the general 60-second setting with a fixed 10-second timeout.

A bounded diagnostic request with `page_size=50` passed the same exact client
path for both profiles (5m 1.188 seconds, 15m 0.937 seconds). This isolates the
primary failure to the page byte-budget mismatch. It does not prove that 50 is
a permanent safe maximum and does not count as full 24-hour save acceptance.

## Runtime and safety

The Readonly API remained healthy with restart count zero on container
`a1d46644...`, image `sha256:6cf2399b...`. Both 200-record server responses had
the required `trading-funnel-export-v1` schema, matching profile, cursor and
`has_more=true`. No code, deployment, schema, business data, PAPER, trading,
parameter or LIVE mutation was performed. LIVE remains disabled.

## Required next task

Remediate the cross-repository contract so every page is guaranteed below the
client byte ceiling (or safely negotiate/enforce an equivalent byte budget),
and make export page timeout behavior consistent with the production read
budget. Then repeat real desktop save acceptance for 24-hour 5m and 15m exports,
including first cold page, every cursor page, final atomic file, row continuity,
and UI error mapping.
