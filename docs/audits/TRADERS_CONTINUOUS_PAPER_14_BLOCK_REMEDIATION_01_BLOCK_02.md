# Continuous PAPER remediation — block 02

## Verdict

`SEQUENTIAL_TRADES_WITHOUT_REARM = PASS`

The production Readonly API was observed at 2026-09-04T15:06Z. No signal,
position close, control transition, or exchange request was created by this
acceptance check.

```text
FIRST_POSITION_ID = paper:first-canary:position:6fb080621705f22106140fe7c882f9d3c4ddd158c5adf455ec451cf801e94dc4
FIRST_POSITION_SYMBOL = AVAXUSDT
FIRST_POSITION_FINAL_STATUS = CLOSED
FIRST_POSITION_CLOSED_AT = 2026-09-04T14:51:00Z
CONTROL_STATE_AFTER_FIRST_CLOSE = CONTINUOUS_ARMED
CONTROL_GENERATION_AFTER_FIRST_CLOSE = 12
MANUAL_REARM_BETWEEN_TRADES = NO

SECOND_NATURAL_CANDIDATE_ID = paper:production-approval-candidate:v1:f5086a49d3ac2d4eda4a7325a83e3d4c317066d6eac03f482e06fa328a6c51ff
SECOND_COMMAND_ID = paper:ingestion-command:v1:2c64e327be1c2ba09164dbcc66ce0f086e4c0d103d58d79bdcd2db29987b3321
SECOND_POSITION_ID = paper:first-canary:position:437d108385c198958847006aa19391acfa54f8d27df96de1a144bbd60f1ca215
SECOND_POSITION_SYMBOL = ETHUSDT
SECOND_POSITION_STATUS = OPEN
SECOND_POSITION_OPENED_AT = 2026-09-04T15:06:00Z
SECOND_SELECTOR_STATE = SELECTED
SECOND_SELECTOR_RANK = 1

AUTHORITY_MODE = CONTINUOUS
CONTROL_STATE = CONTINUOUS_ARMED
CONTROL_GENERATION = 12
COMMANDS_USED_TODAY = 2
RISK_USED_TODAY_BPS = 20
LIVE_ALLOWED = false
SEQUENTIAL_TRADES_WITHOUT_REARM = PASS
```

The isolated PostgreSQL E2E contract covers close, reconciliation, capacity
release, another selector tick, and a second position without an ARM/START
call. The fixture additionally asserts that generation and
`CONTINUOUS_ARMED` remain unchanged across both trades.
