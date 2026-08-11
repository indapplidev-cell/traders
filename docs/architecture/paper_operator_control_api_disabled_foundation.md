# PAPER Operator Control API disabled foundation

The desktop control boundary is a separate inert FastAPI composition under
`app/operator_control`. It is not registered in the read-only reporting API.
Import and app construction do not bind a socket, resolve PostgreSQL, load a
production credential, start a worker, or perform a control transition.

## Network and deployment contract

- API version: `1`.
- Reserved host endpoint: `127.0.0.1:8766`.
- `0.0.0.0`, wildcard, IPv6, hostnames, and arbitrary interface overrides are
  rejected by configuration validation.
- Default operation mode is `DISABLED_FOUNDATION`, `enabled=false`,
  `mode=PAPER`, `live_allowed=false`.
- API documentation is disabled by default and CORS middleware is absent.
- Browser `Origin` requests and credentials in query parameters are rejected.
- Request bodies are limited to 16 KiB.
- This source foundation has no Compose, systemd, runtime entry point, or
  production credential binding and therefore cannot listen in production.

Port `8766` is stable and does not conflict with the deployed read-only API at
`8765`, its container-internal `8080`, or the reviewed canary default `18080`.

## Authentication and authorization

`PaperOperatorAuthenticator` accepts an `Authorization: Bearer` capability and
uses constant-time comparison. Localhost is only a network boundary, never an
authentication decision. Cookies and query-string credentials are not auth
sources. The seven exact scopes are:

- `paper.control.status.read`
- `paper.canary.status.read`
- `paper.canary.arm`
- `paper.canary.start`
- `paper.control.disable`
- `paper.control.emergency_stop`
- `paper.control.clear_emergency_stop`

`PaperOperatorControlCredentialBinding` defines the future port for a local,
OS-protected, restrictive-ACL and rotatable capability. Its implementation
must remain separate from database credentials and production environment
bindings. No production capability or binding is created by this task.

## Exact route surface

| Method | Route | Meaning |
|---|---|---|
| GET | `/control/v1/status` | sanitized host-control status |
| GET | `/control/v1/canary/status` | normalized bounded-canary status |
| POST | `/control/v1/arm-first-canary` | bounded max-one/max-one PAPER arm intent |
| POST | `/control/v1/start-first-canary` | immediate bounded executor start intent |
| POST | `/control/v1/disable` | semantic disable transition |
| POST | `/control/v1/emergency-stop` | semantic emergency-stop transition |
| POST | `/control/v1/clear-emergency-stop` | stop to disabled only |

There is no generic state setter, CRUD surface, order/position/trade endpoint,
or mutation through GET. The arm DTO accepts only the bounded symbol set
`BTCUSDT`, `ETHUSDT`, `SOLUSDT`, exactly one new-command budget and exactly one
open-position budget. Side, direction, quantity, price, stop, target, leverage,
risk override, and approval override fields are rejected rather than ignored.

## Authority and execution

`PaperOperatorControlService` delegates all real isolated state changes to the
existing `PaperProductionSafetyControl`. It does not implement a second state
machine, audit file, or lock graph. Existing atomic state publication,
generation validation, append-only audit reconciliation and host-local
interlock therefore remain authoritative.

The default production-target composition authenticates and validates each
request, reads safe authority status, then returns
`CONTROL_API_DISABLED_FOUNDATION` before any transition. The injected
`ISOLATED_CONTROL_ROOT` composition exists only for HTTP integration proofs.
Its in-memory request registry provides process-lifetime replay and conflict
protection without adding a second persistent audit. Enabling a future
production mutation mode requires a separately authorized durable idempotency
design and is outside this foundation.

`PaperFirstCanaryExecutor` is a narrow future interface with `preflight`,
`start_bounded_canary`, and `status`. The production adapter is disabled and
does not access PostgreSQL. A start request never accepts worker arguments or
trade approval and never waits for a signal. `NO_ELIGIBLE_APPROVAL` is a
healthy zero-mutation result. Real approval remains the responsibility of the
existing production approval source and strategy/risk/final-approval chain.
