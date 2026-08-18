# Authoritative product i18n

The tracked server catalog in `app/i18n` is the only hand-maintained source
of product translations. It supports `ru` and `en`; keys are namespaced by
presentation context (`market.regime.*`, `setup.status.*`,
`funnel.reason.*`, `control.state.*`, and related families). Business APIs
continue to expose stable machine codes and business logic does not inspect a
locale or translated string.

The source-only Readonly API adds exactly two GET contracts:

- `GET /api/v1/i18n/manifest`
- `GET /api/v1/i18n/catalog/{locale}`

The manifest and catalog carry schema version, catalog version and a SHA-256
identity derived only from canonical public catalog content. Catalog exports
are deterministic and bounded, do not query the database, and have no write
counterpart. An unsupported locale receives the standard validation 4xx.
These two routes are implemented in source but were not deployed by the i18n
remediation task; the accepted production runtime therefore remains at its
previous 25 GET / 0 write contract until a separate deployment task.

Validation enforces exact RU/EN key parity, placeholder parity, namespaced and
bounded keys/values, and translation coverage for the public enum registries
and bounded funnel reason vocabulary. Adding a public code without both
translations fails tests.

Desktop and future Android clients are thin consumers. A client may keep a
local locale preference, a validated last-known-good cache and generated
platform resources, but may not maintain domain meanings. Desktop startup
renders from a valid cache (or the generated bootstrap), checks the manifest,
downloads only a changed locale, validates it, and atomically replaces the
cache. `scripts/generate_desktop_i18n_bootstrap.py` is the only supported way
to regenerate the desktop bootstrap and generated Help catalog.

Unknown future codes use a localized generic primary label while retaining the
raw code in an explicit diagnostic/detail surface. Known codes must never use
that fallback.
