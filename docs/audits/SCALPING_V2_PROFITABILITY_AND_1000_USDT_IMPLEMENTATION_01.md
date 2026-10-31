# Scalping v2 profitability and 1000 USDT implementation 01

## Verdict

`PARTIAL_PASS_SAFE_IMPLEMENTATION; NO_PARAMETER_PROMOTION; NO_SESSION_ROTATION`

The offline research path now rejects a frozen finalist unless its holdout has
at least 100 trades, covers at least five UTC days, has win rate strictly above
50%, Profit Factor at least 1.20, positive expectancy, and positive net PnL.
The search remains bounded and uses a 1000 USDT starting balance.

Production PAPER baseline preparation now has explicit immutable contracts:

- `LIFECYCLE-01` -> `baseline:production-paper-v1`, 100.00 USDT;
- `LIFECYCLE-02` -> `baseline:production-paper-v2`, 1000.00 USDT.

An unknown session fails closed. Readiness checks only the requested identity,
so an archived baseline cannot accidentally satisfy the active session.

## Research changes

- calibration and holdout minimum samples: 100;
- validation minimum: 100 trades and five independent UTC days;
- promising and promotion Profit Factor floor: 1.20;
- promotion win-rate floor: strictly greater than 50%;
- planned RR search: 0.6, 0.8, 1.0, 1.2;
- stop search: 36 through 65 bps;
- target search: 40 through 60 bps.

These are research ranges and promotion gates. They do not alter the active
`scalping-v2-set-2` trading parameters.

## Safety boundary

The production session was not rotated. Existing command/order/fill/position
tables do not carry `accounting_session_id`; rotating inside the current
database would mix historical economics. The repository also deliberately
denies baseline creation after economic activity. A later activation therefore
requires either a session-aware schema migration across every economic writer
and reader or a separately bound clean PAPER database with the old database
retained read-only.

No production database mutation, migration, container restart, deployment,
LIVE change, synthetic trade, or Binance order call was performed.

## Verification

- focused baseline/research/security tests: 58 passed;
- final focused authority/holdout/baseline/security tests: 48 passed;
- compileall: passed;
- diff whitespace validation: passed;
- PostgreSQL integration scope: not run because its isolated test URL was not
  configured; the production database was not substituted;
- broader research run disclosed unrelated existing failures in stale baseline
  expectations and Windows Tk text encoding.

## Current decision

There is no evidence yet for a strategy with win rate above 50% and positive
economics. Therefore no parameter set is promoted. The next safe stage is to
obtain a compatible dataset, execute the frozen chronological sweep, and only
then consider a new parameter set and session rotation.
