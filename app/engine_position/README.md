# ENGINE-POSITION-01

ENGINE-POSITION-01 does not manage exchange positions. LIVE position management is always disabled.
Position is a local immutable domain model. No Binance credentials are read. No network exchange
client exists in this module. No PostgreSQL migration is introduced. The online orchestrator does
not call this module yet.

The boundary accepts an `ExecutionIntent` and matching acknowledged
`ExecutionAcknowledgement`. `LIVE` is rejected before all other validation with
`LIVE_POSITION_MANAGEMENT_DISABLED`; environment variables and the CLI cannot override it. The
acknowledgement has no upstream acknowledgement ID, so the local link is
`ack:v1:sha256(canonical stable acknowledgement identity)`. The identity contains only
`execution_intent_id`, `idempotency_key`, `mode`, and `status`; timestamps, warnings, reason codes,
and metadata are excluded.

## Lifecycle

| From | Allowed destinations |
|---|---|
| `PENDING_OPEN` | `OPEN`, `REJECTED`, `CANCELLED`, `DISABLED` |
| `OPEN` | `PARTIALLY_CLOSED`, `CLOSED` |
| `PARTIALLY_CLOSED` | `PARTIALLY_CLOSED`, `CLOSED` |
| terminal states | none |

`PAPER` needs an explicit local `PositionFillEvent` to open. `DRY_RUN` defaults to
`PENDING_OPEN`; callers may explicitly request a synthetic local fill whose source and metadata are
`LOCAL_DRY_RUN`. It has no external order or trade ID. Initial fill must equal the requested initial
quantity. A smaller fill is rejected with `PARTIAL_OPEN_FILL_UNSUPPORTED`, keeping
`open_quantity + closed_quantity = initial_quantity` unambiguous. Scale-in after opening is
unsupported. Only `PENDING_OPEN` can be cancelled; an opened position must be closed through a
close event so quantity and realized PnL cannot be hidden.

Events are consumed in supplied order and never sorted. IDs are applied once, position IDs must
match, event time cannot precede current state/open time, and mark boundaries cannot move backward.
Terminal states reject every later event. Every transition creates a new frozen state. Nested
metadata is recursively frozen.

## Identity, store, and concurrency

`position_key` is `position:v1:<sha256>` over canonical JSON containing execution intent ID,
execution idempotency key, symbol, mode, source timeframe/window, setup ID, strategy decision ID,
and risk decision ID. Timestamps and metadata are excluded. `InMemoryPositionStore` protects create,
read and reduce-and-swap operations with one reentrant lock, so create is atomic, duplicate keys do
not overwrite, events cannot lose updates, and only one concurrent create wins. Returned objects are
lossless immutable copies. There is no database repository.

## PnL and Decimal policy

All quantities, prices, fees and PnL use `Decimal`; float input is rejected by position contracts.
No quantization is applied, so the active Decimal context supplies the explicit precision/rounding
policy (default Python context: 28 significant digits, `ROUND_HALF_EVEN`). Callers may quantize at a
separate presentation boundary.

- LONG unrealized: `(mark - average_entry) * open_quantity`
- SHORT unrealized: `(average_entry - mark) * open_quantity`
- LONG realized: `(close - average_entry) * close_quantity`
- SHORT realized: `(average_entry - close) * close_quantity`
- net realized: cumulative gross realized minus cumulative fees

Partial close reduces open quantity without changing average entry. Over-close and negative fees are
rejected atomically. Closed unrealized PnL is zero.

Serialization schema version is 1. Decimal is encoded as a string, timestamps as UTC ISO-8601,
enums as stable strings, and canonical JSON sorts keys. Unknown schema versions are rejected.
