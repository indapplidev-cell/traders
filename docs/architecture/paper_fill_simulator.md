# Deterministic PAPER fill simulator

This note records the implemented scope of
`TRADERS_ML_PAPER_TRADING_DETERMINISTIC_FILL_SIMULATOR_01`. The simulator is a
pure domain calculation. It does not select data from a repository, open a
session, persist a fill, transition an order or position, read a clock, use
randomness, or call a network.

## Reuse inventory

| Area | File | Symbol | Exact semantics | Decision |
|---|---|---|---|---|
| Candle interval | `app/engine_market_data/candle.py` | `Candle` | Stored close timestamp is inclusive: `open_time_ms + duration - 1` | Adapted because the existing model accepts float source values |
| Timeframe | `app/engine_market_data/timeframe.py` | `timeframe_to_milliseconds`, `is_aligned_to_timeframe` | `1m = 60000ms`; opens are epoch-aligned | Reused |
| Close boundary | `app/engine_market_data/freshness_monitor.py` | `close_boundary_ms` | Exclusive boundary is `open_time_ms + duration` | Reused |
| Command boundary | `app/engine_orchestrator/closed_window_detector.py` | `ClosedWindowDetector` | `closed_until_ms = close_time_ms + 1` | Reused as authoritative exclusive convention |
| Command/order/fill | `app/engine_execution/paper_models.py` | `PaperExecutionCommand`, `PaperOrder`, `PaperFill` | Frozen Decimal-only domain contracts | Reused |
| Side/state | `app/engine_safety/paper_domain.py` | `PaperSide`, `PaperOrderState`, validators | Strict enums, bounded identities, exact Decimal validation | Reused |
| Identity | `app/engine_execution/paper_idempotency.py` | `_key`, `PAPER_IDEMPOTENCY_VERSION` | Length-prefixed public causal tuple and SHA-256 under v1 namespace | Adapted with simulator-specific public tuple |
| Persistence precision | `app/db/paper_models.py` | `PRICE_*`, `QUANTITY_*`, `MONEY_*` | PostgreSQL `NUMERIC(38,18)` | Reused as output compatibility gate |
| ORM compatibility | `app/db/paper_mappings.py` | `paper_fill_to_orm_values` | Pure mapping without session access | Reused in compatibility tests |
| Repository boundary | `app/engine_paper/repositories.py` | entry/close atomic methods | Persistence owns transaction and lifecycle mutation | Not called |

`PaperFillCandle` is a narrow immutable adapter because the general market
`Candle` deliberately normalizes floats through their string representation.
The execution boundary instead requires caller-supplied finite positive
`Decimal` OHLC values and rejects float inputs.

## Boundary contract

The authoritative market-data representation is half-open when expressed as a
closed-through boundary:

```text
inclusive stored close_time_ms = open_time_ms + duration_ms - 1
exclusive close boundary       = open_time_ms + duration_ms
closed_until_ms                = close_time_ms + 1
```

Therefore an aligned command's exclusive boundary is also the numeric open of
the immediately following interval:

```text
EXPECTED_CANDLE_OPEN_MS =
    command.closed_until_ms

EXPECTED_CANDLE_CLOSE_BOUNDARY_MS =
    close_boundary_ms(EXPECTED_CANDLE_OPEN_MS, "1m")
```

The implementation does not add `59999` or choose a nearest timestamp.
Unaligned command boundaries and candle opens fail closed. Equality at the
snapshot close boundary is eligible. One millisecond before it is not yet
eligible.

Only the exact expected candle may fill. A later closed candle proves a gap; a
later or otherwise out-of-snapshot candle is future data. Previous, incomplete,
duplicate, conflicting, or missing candles never become fallback prices.

## Policy and precision

`PaperFillSimulationPolicy` validates the exact foundation values:

```text
price source              = NEXT_ELIGIBLE_CLOSED_1M_OPEN
timeframe                 = 1m
latency                   = 1 closed candle
slippage                  = 2 bps
fee                       = 10 bps per fill
partial fills             = false
future data               = false
intrabar conflict policy  = STOP_FIRST_CONSERVATIVE
```

Price and fee quantums are explicit finite positive Decimal inputs. They must
themselves fit `NUMERIC(38,18)`. Quantity, final price, and final fee are checked
for lossless `NUMERIC(38,18)` persistence compatibility; the simulator never
relies on persistence to round them.

All arithmetic uses an isolated local Decimal context. Rounding to a supplied
quantum supports decimal increments such as `0.01` and `0.05`.

## Role, slippage, and fee

| Paper side | Fill role | Simulated action |
|---|---|---|
| LONG | ENTRY | BUY |
| LONG | CLOSE | SELL |
| SHORT | ENTRY | SELL |
| SHORT | CLOSE | BUY |

The action is private to the simulator's adverse-price calculation.
`PaperFill.side` remains the existing position side.

```text
BUY raw price  = candle.open_price * (1 + slippage_bps / 10000)
SELL raw price = candle.open_price * (1 - slippage_bps / 10000)

BUY rounding   = ROUND_CEILING to price_quantum
SELL rounding  = ROUND_FLOOR to price_quantum

raw fee        = final rounded fill price * quantity * fee_bps / 10000
fee rounding   = ROUND_CEILING to fee_quantum
fee asset      = explicit request.quote_asset
```

The fee never changes quantity, and the symbol suffix is never parsed to infer
the quote asset.

## Validity and identity

The conservative validity rule is inclusive:

```text
command.valid_until_ms >= selected candle exclusive close boundary
```

The simulator knows the selected candle only after that boundary. Equality
passes; one millisecond earlier returns `COMMAND_EXPIRED`.

Fill ID and fill idempotency key share this canonical public causal tuple:

```text
contract_version
order_id
fill_role
source_open_time_ms
source_close_boundary_ms
simulation_policy_id
slippage_policy_id
fee_policy_id
latency_policy_id
```

Both use the existing v1 length-prefixed hashing contract. They exclude object
serialization, input ordering, diagnostics, secrets, wall clock, randomness,
database ordering, and repository state. `filled_at` is the selected candle's
exclusive close boundary converted from the Unix epoch in UTC.

## Result boundary

`FillSimulationResult` contains a stable outcome, bounded machine reason code,
bounded safe message, optional field path, resolved action, selected candle,
and either exactly one existing immutable `PaperFill` for `FILLED` or no fill.
It cannot represent a success without a fill or a failure with a fill.

The bounded request accepts at most 64 immutable candidate candles. Sorting is
canonical and input ordering has no effect. Identical duplicates return
`DUPLICATE_CANDLE`; different OHLC for the same interval returns
`CANDLE_CONFLICT`.

The output is compatible with later repository persistence, including the
existing persistence role mapping `CLOSE -> EXIT`, but this module imports and
calls no repository or SQLAlchemy session.
