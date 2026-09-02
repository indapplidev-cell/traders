# TRADERS Windows Docker console popup remediation 01

## Final verdict

`PASS_VISIBLE_CONSOLE_LOOP_STOPPED`

## Proven root cause

- The current-user Startup launcher `TradersML-WALAckDaemon.vbs` started the
  `pythonw.exe` WAL ACK daemon after Windows logon.
- The daemon polled Docker through the console-subsystem `docker.exe` roughly
  once per second without Windows no-console creation flags.
- Every poll therefore created a short-lived `conhost.exe`; these were the
  repeatedly appearing terminal windows.
- The open Docker Desktop dashboard added a separate, much slower
  `docker stats --all --no-trunc --no-stream` poll.

## Remediation

- Windows subprocess calls used by the WAL ACK daemon and shared production
  backup helper now set `CREATE_NO_WINDOW`.
- The daemon lock writes its owner PID before returning the newly created lock,
  closing the simultaneous-start empty-lock race.
- The pre-fix daemon was stopped and the remediated hidden daemon was started.
- Docker Desktop's dashboard was closed; the engine and containers were not
  stopped. The durable fix does not depend on the dashboard or integrated
  terminal preference.
- Current-user Startup fallback was regenerated from the remediated source for
  subsequent Windows logons.

## Verification

- Before remediation: 15 `docker.exe` plus 15 Docker-parented `conhost.exe`
  processes observed in 15 seconds.
- After stopping the duplicate daemon and closing the dashboard: zero new
  `docker.exe` processes in 20 seconds.
- Remediated daemon child `conhost.exe` instances were observed only with
  `MainWindowHandle=0` (no visible console).
- Fresh post-commit observation captured 13 new `docker.exe` calls and their
  console hosts in 10 seconds with zero visible windows.
- The two `pythonw.exe` processes in the fresh process tree are one virtualenv
  launcher/interpreter chain. The daemon PID file and running-state snapshot
  identify only the interpreter PID; this is not a duplicate daemon.
- Focused Windows daemon tests: `9 passed, 7 deselected`.
- Compile check: PASS for both changed scripts.
- The full historical operator-safety file produced `15 passed, 1 failed`; the
  one failure is its branch-history invariant against an old baseline and does
  not exercise this remediation.
- Eight Docker containers remained running; health-checked Readonly API,
  Operator Control API, and PostgreSQL remained healthy with restart count 0
  at diagnosis time.

## Safety state

- LIVE remains disabled.
- No database, schema, trading, control, command, order, fill, position, or
  balance mutation was performed.
- The host WAL ACK daemon is running for the current Windows session through
  the remediated hidden launcher; the same launcher remains active for later
  Windows logons.
