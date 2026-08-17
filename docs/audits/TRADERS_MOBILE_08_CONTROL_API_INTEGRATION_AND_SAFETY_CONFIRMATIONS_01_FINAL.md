# MOBILE-08 Control security acceptance

Task: `TRADERS_MOBILE_08_CONTROL_API_INTEGRATION_AND_SAFETY_CONFIRMATIONS_01`

Verdict: `BLOCKED`

Blocker: `CURRENT_CONTROL_AUTH_NOT_SAFE_FOR_MOBILE_LAN_EXPOSURE`

Secondary blocker: `CONTROL_MOBILE_SECURITY_REMEDIATION_EXCEEDS_MOBILE_08_BOUNDED_SCOPE`

Stop condition: `CONTROL_SECURITY_REMEDIATION_REQUIRED_BEFORE_NETWORK_MUTATION`

## Baseline and runtime

All three required repositories were clean on their required branches before the
audit. Server was `feature/engine-platform` at
`58f8db6bf4a3ffb9f56640533ad1eb58977bc9cf`; mobile was `main` at
`3ec5903fa0efbfc3368924a834bd26405e0d15b6`; desktop was `main` at
`e16e48fdb78e605d0c3c6232946537ee241a8708`.

The production Control API is healthy and audit reconciliation passes. A
credential-safe GET-only probe reported state `ARMED`, generation `6`, and
`production_mutation_enabled=true`. Windows exposes only
`127.0.0.1:8766`; an unauthenticated status GET returned HTTP 401. No Control
LAN listener, firewall rule, portproxy, mobile Control URL, restart, database
change, or Control mutation was made.

## Authoritative source inventory

- Routes: `app/operator_control/routes.py`
- Schemas: `app/operator_control/schemas.py`
- Service and eligibility/generation checks: `app/operator_control/service.py`
- Authentication and credential binding: `app/operator_control/auth.py`,
  `app/operator_control/runtime.py`
- Safety authority and transition audit: `app/engine_safety/paper_production_control.py`
- Production execution boundary: `app/operator_control/production_executor.py`

## Exact route matrix

Every route requires its named bearer-token scope. GET routes have no generation
or acknowledgement field. Every POST has a bounded response
`PaperOperatorControlDecision`, requires `request_id` and
`expected_generation`, and is subject to the server safety authority.

| Method | Path | Class | Scope | Extra request gates | Server state/eligibility |
|---|---|---|---|---|---|
| GET | `/control/v1/status` | read | `paper.control.status.read` | none | any readable state; returns `PaperOperatorControlStatus` |
| GET | `/control/v1/canary/status` | read | `paper.canary.status.read` | optional exact canary/ARM request lookup | any; returns `PaperOperatorCanaryStatus` |
| GET | `/control/v1/canaries/{canary_id}` | read | `paper.canary.status.read` | exact canary id | any; returns `PaperOperatorCanaryStatus` |
| POST | `/control/v1/arm-first-canary` | mutation | `paper.canary.arm` | three acknowledgements, PRODUCTION/PAPER, 1/1 budgets, active symbols | `DISABLED`, matching generation, readiness preflight PASS |
| POST | `/control/v1/start-first-canary` | mutation | `paper.canary.start` | canary acknowledgement, exact canary and arming transition | `ARMED`, matching generation and correlation, executor preflight |
| POST | `/control/v1/disable` | mutation | `paper.control.disable` | operator acknowledgement | matching generation; legal/safe canary boundary; `ARMED -> DISABLED` or idempotent `DISABLED` |
| POST | `/control/v1/emergency-stop` | mutation | `paper.control.emergency_stop` | operator acknowledgement | matching generation; `DISABLED/ARMED -> EMERGENCY_STOP`, same-state idempotent |
| POST | `/control/v1/clear-emergency-stop` | mutation | `paper.control.clear_emergency_stop` | operator plus clear-stop acknowledgement | `EMERGENCY_STOP -> DISABLED`, matching generation |

Count: 3 GET, 5 POST mutation routes.

## Security decision

The current authentication model is a static bearer capability loaded from an
ACL-protected server file. The implementation compares it in constant time and
enforces route scopes, but production loads one capability with all scopes. It
has no mobile-device identity and the bearer value is the reusable authority.

The current transport is HTTP. The Authorization header is not protected from
LAN eavesdropping. Requests do not cryptographically bind method, path, body,
timestamp, nonce, generation, or action. `request_id` provides operation
idempotency/conflict detection, not security replay resistance: the same
authenticated request and fingerprint returns the stored result. The in-memory
idempotency registry also does not survive process restart, while selected
canary correlation records are durable for workflow recovery. A bearer holder
can select a new request id, so this is not an anti-replay authentication
scheme.

Consequently these mandatory properties fail for LAN exposure:

| Property | Result | Evidence |
|---|---|---|
| Mobile peer authentication | FAIL | shared capability does not distinguish a registered phone |
| Credential confidentiality | FAIL | reusable bearer over HTTP |
| Request integrity | FAIL | no request signature or TLS |
| Replay resistance | FAIL | no freshness/nonce verification; exact duplicate is idempotently accepted |
| Generation and server eligibility | PASS in existing API | server validates generation and legal transition/readiness |
| Device-bound credential storage | NOT IMPLEMENTED | Android has no Control credential or provider |
| Revocation/rotation lifecycle | FAIL for mobile | protected file rotation requires a deployment boundary; no per-device revocation |

Firewall/IP scoping cannot repair these application-layer failures. Exposing
the existing API would require a reusable Control bearer in Android and would
violate the task's automatic blockers.

## Required remediation

Create a dedicated, separately authorized Control mobile-security task. It must
design and test per-device enrollment with an Android Keystore non-exportable
private key, server allowlisted public keys with per-device disable/revocation
and rotation, a canonical signed envelope binding method/path/body hash/time/
nonce/action/generation, persistent nonce/freshness semantics across restart,
secret-free device-attributed audit events, and server-authenticated TLS with
normal certificate validation. Persistent replay state or PKI schema changes
require an explicit migration/deployment task. Only after that architecture is
deployed and adversarially accepted may MOBILE-08 resume from Phase A.

## Validation and invariants

- Existing isolated Control suites: 1927 passed; no production mutation used.
- Readonly Analysis and Markets: HTTP 200 through both loopback and the accepted
  `192.168.1.100:18765` phone-scoped forwarder.
- Existing Readonly portproxy remains the only portproxy.
- No task-created Control listener/firewall/URL or public path exists.
- Production ARM/START/STOP/DISABLE and all Control POST counts by this task: 0.
- Existing canary, budgets, PAPER runtime, database, Binance access, and LIVE
  state were not changed.

This block is a security acceptance outcome, not an implementation failure.
Android Control source, tests, APK acceptance, and real-device Control GET were
intentionally not attempted after the hard Phase A gate failed.
