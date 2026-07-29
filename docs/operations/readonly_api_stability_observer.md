# Readonly API stability observer health classification

The observer treats HTTP transport, JSON parsing, runtime health, and acceptance
as separate decisions. A 2xx response never becomes `CURRENT` merely because
the request succeeded.

The classifier uses the exact envelope and `HealthSnapshot` response fields:
`api_version`, `generated_at`, `status`, `observed_at`, `services`,
`timing_state`, `reason_code`, `operational`, `ready`, and
`acceptance_blocking`. All are required. Strings, arrays, and booleans are type
checked before enum or conflict evaluation.

| Class | Required signal contract | Priority |
|---|---|---:|
| `CURRENT` | `OK`, `CURRENT`, `true`, `true`, `false` | 1 |
| `WITHIN_GRACE` | `OK`, `WITHIN_GRACE`, `true`, `true`, `false` | 2 |
| `DEADLINE_EXPIRED` | `DEGRADED`, `DEADLINE_EXPIRED`, `false`, `false`, `true` | 3 |
| `DEGRADED` | blocking status, `DEGRADED`, `false`, `false`, `true` | 4 |
| `UNKNOWN` | `UNKNOWN`, `UNKNOWN`, `false`, `false`, `true` | 5 |

Validation runs before class priority. Missing fields, wrong types, unsupported
enum-like values, contradictory signals, invalid root JSON, and invalid JSON
remain fail-closed `UNKNOWN` with exact stable reason and branch IDs. No
free-text matching is authoritative and no field aliases are accepted because
the deployed response model defines no aliases for these fields.

For every health response, the observer retains only bounded structure:
schedule sequence, phase and UTC, numeric HTTP status, content type, byte
length, JSON parse success, JSON root type, allowlisted keys and paths,
allowlisted field types, normalized public enum-like/boolean values,
parser/classifier branch IDs, and a SHA-256 digest of field paths and JSON
types. The final renderer emits at most 20 UNKNOWN descriptors and marks
truncation explicitly. It never retains the response body, a full-payload hash,
headers, environment, traceback, credential-derived data, or non-allowlisted
values.

The historical failed window remains failed. Its aggregate proves one
successful 2xx health request reached the generic `UNKNOWN` branch, but the old
sample model did not retain sequence, UTC, exact status, content type, byte
length, or safe structure. The fixture in
`tests/fixtures/readonly_api_health_unknown_minimal.json` is therefore a
minimal secret-free reproduction of the proven decision path and current
response-model contract, not the historical payload.
