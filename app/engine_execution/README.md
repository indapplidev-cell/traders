# Safe execution intent layer

`engine_execution` sits after `engine_risk` and before a safe local gateway. It converts an
approved strategy decision, approved risk decision, already calculated setup or plan, and a
closed-window identity into an immutable `ExecutionIntent`.

`ExecutionIntent` is not an exchange order, approval to open a position, or evidence of a
fill. `MARKET_INTENT` and `LIMIT_INTENT` are descriptions only.

**ENGINE-EXECUTION-01 does not place exchange orders.**

## Approval policy and modes

Approval uses exact complete-string pairs; substring and suffix matching are forbidden.

| Strategy status | Risk status | `approval_scope` | PAPER | DRY_RUN | LIVE |
|---|---|---|---|---|---|
| `APPROVED` | `RISK_APPROVED` | `PRODUCTION_APPROVED` | allowed | allowed | disabled |
| `ALLOW_RESEARCH_TRADE_PLAN` | `RISK_PRE_APPROVED_RESEARCH` | `RESEARCH_ONLY` | allowed | allowed | disabled |

Mixed production/research pairs are rejected with `CONTRACT_MISMATCH`. The
`PRODUCTION_APPROVED` value classifies the input contract; it does not authorize exchange
execution.

Research approval statuses are accepted only for PAPER and DRY_RUN.
They do not authorize LIVE execution.

LIVE execution is always disabled. It is the first builder safety gate and returns only
`LIVE_EXECUTION_DISABLED`, regardless of other input errors. No configuration switch can
override this behavior.

## Idempotency and duplicates

The key is `execution:v1:<sha256>` over sorted canonical JSON containing symbol, source
timeframe, source closed-until milliseconds, setup ID, strategy decision ID, risk decision
ID, and execution mode. Creation time and metadata do not affect the key. Decimal values use
lossless text and enums use stable strings.

The in-memory registry protects registration with a lock and is safe for concurrent focused
use. Exactly one concurrent registration is new; later registrations are `DUPLICATE`.
Duplicate intents are not submitted to the paper runner again.

## Gateways

- `DryRunExecutionGateway` validates and acknowledges locally.
- `PaperExecutionGateway` delegates to the existing `engine_paper.PaperRunner`. It does not
  recalculate entry, stop, target, or quantity. Runner exceptions become safe rejected
  acknowledgements.
- `DisabledLiveExecutionGateway` always returns `LIVE_EXECUTION_DISABLED`.

PAPER and DRY_RUN acknowledgements always have `external_order_id = null`; fake exchange
identifiers are never generated.

## Serialization and integration boundary

Serialization uses `execution_schema_version = 1`, UTC ISO-8601 timestamps, stable enum
strings, lossless Decimal strings, and sorted-key canonical JSON. Nested mappings and
sequences are frozen, including after a serialization round trip.

No Binance credentials are read. No network exchange client exists in this module. No
PostgreSQL migration is introduced. The online orchestrator does not call this module yet.
The module adds no database connection, background service, or runtime integration.
