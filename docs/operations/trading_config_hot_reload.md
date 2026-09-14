# Trading parameter hot reload

Production services bind `config/trading` read-only at
`/service/config/trading`. The copy shipped in an image is a bootstrap fallback;
the bind-mounted `trade_parameters.yaml` is the production runtime authority.

Normal parameter-value workflow:

1. Edit `config/trading/trade_parameters.yaml` on the host.
2. Save the file.
3. Wait for the next closed 5-minute decision boundary.
4. Refresh Traders if necessary.

No build, container/service restart, manual activation, hash, revision, or
parameter-set version update is required for a value-only change.

The server polls at the bounded intervals declared in the YAML `reload` block.
It waits for a stable file, performs duplicate-key, typed, semantic,
inheritance, override, and cross-field validation, then stages one immutable
candidate. The candidate is swapped atomically at the next 5-minute boundary.
Malformed or temporarily missing files leave the last-known-good snapshot
active and are retried after the next file change.

Read-only diagnostics are available at `GET /api/v1/trading/config`. They show
the active and pending generations, detection/validation/activation timestamps,
the current error, the active parameter set, and every effective value with its
YAML source layer/path. The funnel endpoint includes the same active status in
`data.config_status`; decision rows retain the exact configuration epoch that
was used by their cycle.

The feature does not enable LIVE execution and does not change the 15-minute
profile or any trading formula.
