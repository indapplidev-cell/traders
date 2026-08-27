# TRADERS server 5m Funnel Readonly memory remediation 01 — FINAL

## Verdict

`PASS`. The production 5m Funnel route now completes both cold and expired-cache
refresh requests in about four seconds without a Readonly API restart. The
deployment replaced only the Readonly API; PostgreSQL, market-data, 15m, 5m,
the scalping calibration collector, and Control were not restarted.

## Forensic finding

The 5m projection loads a bounded 490 run/result-pair horizon. The production
rows contain about 16.8 MB of PostgreSQL payload before Python ORM and JSON
expansion. The previous cache refresh retained the expired object graph while
materializing its replacement. With the Readonly process already at roughly
448.6 MiB under a 512 MiB limit, this produced the observed hard restarts and
client timeouts. The old Readonly container had `restart_count=80`; its logs
showed repeated startups without graceful shutdown, traceback, database pool,
or statement-timeout evidence.

## Remediation

- Evict and dereference an expired cache generation before executing the
  replacement query, while retaining the existing lock and single-flight rule.
- Use SQLAlchemy `load_only` for the exact run/result columns consumed by the
  Funnel projection and loaded production-approval classifier.
- Add a regression proving the stale generation is absent when the replacement
  query begins.

Implementation commit:
`e07185f3c17e7e2634675ee53aae36bd68229321`.

## Validation

```text
focused Funnel/export: 24 passed
all tests/server_api: 140 passed, 7 skipped
production approval/ranking: 1472 passed
compileall: PASS

production 15m: HTTP 200, 0.590232 s
production 5m cold: HTTP 200, 4.476855 s
production 5m warm: HTTP 200, 0.050277 s
production 5m after 31 s TTL expiry: HTTP 200, 4.010636 s
Readonly memory after expired refresh: 429.9 MiB / 512 MiB
Readonly restart count after deployment and canary: 0
Readonly post-deployment log errors/500/503: 0
```

The full repository suite was also run as an informational baseline. It yielded
30,803 passes and 30 skips; unrelated integration groups reported 441 failures
and 342 setup errors because their dedicated PostgreSQL test URLs were absent
and a legacy contract still expects schema `0014` while the source is already at
`0015`. The impacted suites above pass independently and completely.

## Runtime continuity

The following protected container identities were identical before and after
the Readonly-only deployment, all with restart count zero:

- PostgreSQL: `7ff21f1478acb3376beb2594d683a50062f4cc93c4227767d6cf464dc51bfd11`
- market-data: `c861e15001eec716d4a0a0d3943242886e5b895b4e895d92132bec9dd3527a11`
- 15m orchestrator: `ea397b8672239d8313e79e6b00262eadd7cfe8c6a92464575c6c14fdb19e89fb`
- 5m orchestrator: `7e9d821deff222c50caa4361b4fb2f7b3a7da950b584c5763d98148f92c89d75`
- scalping collector: `1a3a3a2866d84abd18661fd72b9e4b7d9f5dd242d2731a459c4c4218200e7013`
- Control: `e2ad3a9262d941f5580c08bae43317b4c2253391c40b9806fca1087992d4f2c8`

The collector remained `RUNNING`, singleton owner count 1, and progressed from
the earlier 3-boundary acceptance snapshot to 81 boundaries / 810 records with
zero missing, duplicates, errors, or future leakage. Its last boundary
`1787804700000` matches the current 5m Funnel health projection. Control remains
ARMED generation 6 in production PAPER; LIVE remains disabled.
