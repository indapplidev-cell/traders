# Mobile Control device security foundation

This source-only foundation keeps the deployed operator instance unchanged at
`127.0.0.1:8766`: HTTP loopback plus its protected static bearer. That bearer
is never accepted by the separate `mobile_device_signed_tls` profile. No
mobile listener, certificate, firewall rule, device enrollment, database
migration, Control mutation, canary action, or LIVE change is part of this
foundation task.

## Runtime profiles

Each Control process has exactly one explicit profile:

| Profile | Bind/transport | Authentication |
|---|---|---|
| `operator_loopback_bearer` | exact `127.0.0.1:8766`, HTTP loopback | existing protected bearer and scopes |
| `mobile_device_signed_tls` | one configured private IP and dedicated port, HTTPS only | registered enabled P-256 device key only |

The mobile factory requires a database binding, TLS certificate path, TLS
private-key path, expected server identity and an exact private bind address.
Missing persistence or TLS settings fail startup. The only plaintext override
requires both the mobile profile and `environment=TEST`; production config
cannot activate it. Production TLS private keys are provisioned outside Git in
a later controlled deployment.

The certificate must contain either a stable private DNS name in DNS SAN or a
stable private address in IP SAN. DHCP must therefore be replaced by a stable
lease/address or stable private DNS before deployment. Android uses normal
platform certificate-chain and hostname/IP verification. The preferred trust
model is a private/public issuing CA whose public certificate can survive leaf
rotation. Rotation issues a new overlapping-validity leaf from that CA; no
hostname verifier, trust-all manager, cleartext fallback, or server private
key is placed in the app.

## Device identity and enrollment

Android creates a `secp256r1` key with `AndroidKeyStore`, `PURPOSE_SIGN`, and
`SHA-256`. The private key is non-exportable and never serialized. The random
UUIDv4 device ID is independent from IMEI, serial, MAC, phone number and user
identity. SharedPreferences contains only the alias, device ID, algorithm,
key version, X.509 SubjectPublicKeyInfo public key, SHA-256 public-key
fingerprint and creation time.

Enrollment exports only those public metadata fields. The server registry
stores the SPKI DER bytes and authorizes only an existing, enabled,
non-revoked row with the exact key version and `ECDSA_P256_SHA256` algorithm.
Revocation affects one device and does not rotate the operator bearer, database
credentials, Binance credentials or any global Control secret. Rotation keeps
the device ID, increments `key_version`, replaces the public key and invalidates
the prior version. A lost phone is handled by revoking its row, removing its
future network authorization where applicable, and enrolling a replacement.

The Android signing key requires the device to be unlocked on API 28+, but
does not require biometric/device-credential authentication for every
signature. This keeps emergency STOP usable; the explicit action confirmation,
freshness, server generation and existing safety gates remain mandatory.

## `traders-control-mobile-v1` envelope

The signature input is a fixed sequence of twelve UTF-8 fields. Each field is
encoded as eight lowercase hexadecimal byte-length characters, `:`, then the
exact bytes. Ordered fields are:

1. scheme version;
2. device ID;
3. key version;
4. uppercase HTTP method;
5. raw encoded path;
6. raw encoded query string;
7. lowercase hex SHA-256 of the exact transmitted body bytes;
8. issued-at Unix seconds;
9. cryptographically random 128-bit base64url nonce;
10. request ID;
11. canonical action;
12. expected generation, or empty for GET.

Android signs the resulting bytes with `SHA256withECDSA` and transports the DER
signature as unpadded base64url. Mutations additionally require the signed
request ID and expected generation to equal the values in the exact JSON body.
Unknown versions, algorithms and missing fields fail closed.

The server accepts age up to 120 seconds inclusive and future clock skew up to
30 seconds inclusive. Mutation nonce claims are retained for 86,400 seconds,
well beyond the freshness interval. Cleanup is an indexed, bounded batch of at
most 500 expired rows invoked by future scheduled operations; request handling
does not perform cleanup and GET polling creates no durable nonce writes.

Verification order is headers/version, device/key authorization, time bounds,
exact body/path/query envelope construction, ECDSA verification, atomic
`(device_id, nonce)` claim for POST, then the existing generation,
acknowledgement, transition/safety, request-ID idempotency and mutation service.
A nonce is consumed even if a later business gate rejects the action.

## Existing route contract

| Method | Path | Scope | Action | Body requirements | State/result authority |
|---|---|---|---|---|---|
| GET | `/control/v1/status` | status read | `STATUS` | none | authoritative state/generation/health |
| GET | `/control/v1/canary/status` | canary read | `CANARY_STATUS` | optional signed query lookup | current/exact canary or not configured/404 |
| GET | `/control/v1/canaries/{canary_id}` | canary read | `CANARY_STATUS` | signed path ID | exact canary or 404 |
| POST | `/control/v1/arm-first-canary` | ARM | `ARM` | request ID, generation, three acknowledgements, PAPER/production, exact budgets/symbol scope | DISABLED to ARMED only through readiness and safety authority |
| POST | `/control/v1/start-first-canary` | START | `START` | request ID, generation, exact canary/arming IDs, acknowledgement | exact ARMED canary to running/waiting outcome |
| POST | `/control/v1/disable` | disable | `DISABLE` | request ID, generation, acknowledgement | safe zero-trade waiting canary/eligible legal transition only |
| POST | `/control/v1/emergency-stop` | emergency stop | `STOP` | request ID, generation, acknowledgement | existing emergency-stop authority |
| POST | `/control/v1/clear-emergency-stop` | clear stop | `CLEAR_EMERGENCY_STOP` | request ID, generation, two acknowledgements | EMERGENCY_STOP to DISABLED only |

Both profiles preserve the same service, request-ID business idempotency,
generation authority, acknowledgements, action eligibility, canary budgets and
mutation safety gate. `current_mutation_ready` continues to mean only readiness
for the next operator ARM control transition, never universal runtime readiness.

## Schema and deployment boundary

Alembic 0016 adds `control_mobile_devices` and
`control_mobile_replay_nonces`. The latter has primary key
`(device_id, nonce)`, a device foreign key and an expiry index. It stores no
request body or signature. Production remains at 0015 until the separately
authorized `TRADERS_CONTROL_MOBILE_DEVICE_AUTH_SCHEMA_CONTROLLED_DEPLOYMENT_01`.
Only after schema deployment may a later task provision protected TLS material,
enroll a public device key, start the separate TLS runtime and perform GET-only
real-device acceptance. MOBILE-08 remains blocked until that acceptance passes.
