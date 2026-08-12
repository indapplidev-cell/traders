# Authoritative first-canary correlation

Revision `0013_paper_first_canary_correlation` adds one durable
`paper_first_canary_sessions` record per first-canary attempt. The server
generates an opaque UUID `canary_id` while reserving ARM. The reservation is
written before the file-backed safety transition and is completed with the
authoritative transition identity and generation. A replay can therefore
recover both a completed ARM and the narrow boundary where the safety state was
published before the HTTP or correlation completion result was observed.

The active-session partial unique index permits at most one non-terminal
session for the production PAPER environment. ARM request identity,
fingerprint, transition identity, and START request identity are unique and
durable. Exact status is available by primary key; a missing ID never falls
back to the current or latest session.

Command creation accepts an optional authoritative `canary_id`. For a first
canary, insertion of the command/journal and assignment of `command_id` occur
inside the same PAPER unit of work. Entry fill persistence derives the session
from that exact command and assigns the exact `position_id` inside the same
transaction. Replays preserve the first identity. A second identity or an
out-of-scope symbol fails safe and never replaces the original link.

The canary detail contract returns the exact `position_id`. The existing
GET-only report-by-position route therefore resolves the authoritative report
without timestamp, symbol, latest-row, or account-delta matching. Reconciliation
status is projected from the existing PAPER/accounting services; no financial
formula is duplicated. `COMPLETED` requires an exact CLOSED position, an
available report, healthy PAPER and accounting reconciliation, and final
control state `DISABLED`.

No-trade START is represented as `NO_ELIGIBLE_APPROVAL` with zero commands and
positions. It remains a healthy non-executed session rather than an executed
trade completion. Emergency Stop continues to call only the existing
file-backed safety authority and does not require the correlation database.

Reporting readiness now exposes `current_mutation_ready` as a real boolean.
It is true only when the required 0013 schema, PITR/WAL, production adapters,
baseline, both reconciliations, PAPER principal/runtime configuration,
kill-switch health and eligible DISABLED control state, bounded canary scope,
and LIVE denial all pass. Current production-like revision 0008 remains false.

Future production schema preparation is forward-only:

```text
0008 → 0009 → 0010 → 0011 → 0012 → 0013
```

This source remediation does not deploy or migrate production, enable PAPER or
LIVE, create an operator credential, or call Binance.
