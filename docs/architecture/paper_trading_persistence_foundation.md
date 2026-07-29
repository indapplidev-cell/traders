# PAPER persistence foundation

## Scope

This note records the implementation choices for Alembic revision
`0009_paper_trading_persistence_foundation`. The revision creates only the
normalized PAPER persistence foundation. It does not implement a repository,
worker, orchestrator mutation, fill simulator, API, client, deployment, PAPER
enablement, LIVE enablement, or exchange transport.

## Convention inventory

| AREA | FILE | SYMBOL | CURRENT_CONVENTION | SELECTED_REUSE | RATIONALE |
|---|---|---|---|---|---|
| Metadata | `app/db/base.py` | `Base` | One SQLAlchemy `DeclarativeBase` | `Base.metadata` | Prevents a parallel schema registry |
| Existing ORM | `app/db/models.py` | Current ML records | Typed `Mapped` columns, bounded strings, `Numeric`, `DateTime(timezone=True)` | Typed declarative records | Keeps model discovery consistent |
| Market-data ORM | `app/engine_market_data/db/candle_tables.py` | `CandleTableMixin` | `BigInteger`, `Numeric(38,18)`, timezone-aware timestamps | `NUMERIC(38,18)` price/quantity/money profile | Existing PostgreSQL exact-decimal precedent |
| Orchestrator ORM | `app/engine_orchestrator/orchestrator_models.py` | `OnlinePipelineRun` | Public IDs are bounded strings; internal rows use integer PKs | Bounded domain public IDs | PAPER aggregate identities are already authoritative public IDs |
| Enum persistence | `alembic/versions/0007_engine_orchestrator_online_pipeline.py` | `ck_online_pipeline_run_status` | Bounded `VARCHAR` plus named `CHECK` | Bounded `VARCHAR` plus named `CHECK` | Unknown values fail at the database boundary without global enum-type lifecycle |
| Partial uniqueness | `alembic/versions/0003_constraints_indexes.py` | `uq_ml_model_versions_active_scope` | PostgreSQL partial unique index | Partial unique `(mode,symbol)` for active positions | Directly enforces one active PAPER position |
| Alembic head | `alembic/versions/0008_engine_orchestrator_freshness_retry.py` | `revision` | Explicit linear revisions and deterministic reverse downgrade | `down_revision=0008_engine_orchestrator_freshness_retry` | Adds no branch or existing-table rewrite |
| Alembic metadata | `alembic/env.py` | `target_metadata` | Explicit model imports into `Base.metadata` | Import `app.db.paper_models` | Makes the new records authoritative metadata members |
| Migration tests | `tests/test_engine_market_data_02_alembic_migration.py` | revision checks | Revision modules are inspected directly | Lineage assertions plus live isolated PostgreSQL cycle | Static lineage alone cannot prove PostgreSQL constraints |
| PostgreSQL tests | `tests/integration/test_engine_market_data_04_prod_smoke_postgres.py` | PostgreSQL-only integration boundary | PostgreSQL-specific behavior is tested on PostgreSQL | Task-owned loopback PostgreSQL database | No SQLite substitution for partial indexes, `NUMERIC`, `TIMESTAMPTZ`, or FK behavior |
| PAPER domain | `app/engine_execution/paper_models.py` | `PaperExecutionCommand`, `PaperOrder`, `PaperFill` | Immutable Decimal-only contracts | Pure value mapping, no repository access | Persistence preserves the implemented domain authority |
| PAPER position | `app/engine_position/paper_models.py` | `PaperPosition` | Versioned immutable snapshots | Version column plus state/accounting checks | Repository compare-and-swap remains a later task |
| PAPER exit/journal | `app/engine_exit/paper_exit.py`, `app/engine_journal/paper_events.py` | `PaperExitDecision`, `PaperDomainEvent` | Immutable bounded causal records | Append-only rows by contract | No event-store payload or unbounded JSON |

## Type and identity contract

Public PAPER identities use `VARCHAR(128)`, matching the domain identity
boundary. Symbols and fee assets use `VARCHAR(32)`. The versioned policy uses a
composite primary key `(policy_id, policy_version)`. Domain aggregate IDs are
the table primary keys; no surrogate ID is added.

Numeric profiles are:

| PROFILE | POSTGRESQL TYPE | RANGE CONTRACT |
|---|---|---|
| Price | `NUMERIC(38,18)` | Up to 20 integer and 18 fractional digits |
| Quantity | `NUMERIC(38,18)` | Up to 20 integer and 18 fractional digits |
| Money/PnL/fees | `NUMERIC(38,18)` | Up to 20 integer and 18 fractional digits |
| Ratio/bps | `NUMERIC(20,10)` | Up to 10 integer and 10 fractional digits |

All numeric constraints explicitly reject `NaN`, positive infinity, and
negative infinity. Application-supplied domain times use
`TIMESTAMP WITH TIME ZONE`; no domain timestamp has a database wall-clock
default. Epoch-millisecond boundaries use non-negative `BIGINT`.

The following fields are deliberately `LOGICAL_FOREIGN_KEY_ONLY` because no
compatible, unambiguous upstream primary key is available at this boundary:

- strategy, risk, setup, pipeline-run, and analysis-result causal IDs;
- simulation, fee, slippage, and latency policy identities carried by commands
  and fills;
- the order's applied fill ID and the position's exit fill ID, which would
  otherwise create circular insertion dependencies.

All safe PAPER-to-PAPER foreign keys use `ON DELETE RESTRICT`. There are no
wallet, account, balance, credential, exchange-key, raw payload, or JSON
columns.

## Tables and authority

| TABLE | AUTHORITY | MUTABILITY CONTRACT |
|---|---|---|
| `paper_simulation_policies` | Versioned simulation policy identity | Immutable after reference |
| `paper_execution_commands` | Full authoritative `PaperExecutionCommand` | Immutable domain content; queue readiness is inactive |
| `paper_orders` | Current order aggregate snapshot | Versioned mutable aggregate |
| `paper_order_events` | Order transition audit rows | Append-only |
| `paper_fills` | Full-fill facts | Immutable |
| `paper_positions` | Current position aggregate snapshot | Versioned mutable aggregate |
| `paper_exit_decisions` | Exit decision facts | Immutable |
| `paper_journal_entries` | Bounded audit projection | Append-only, not an event store |

`paper_execution_commands.processing_status` is inactive durable-queue
readiness only. Revision 0009 contains no claim/update worker and starts every
row at `PENDING`.

## Domain versus database enforcement

| RULE | FOUNDATION ENFORCEMENT |
|---|---|
| PAPER-only command/order/position mode | Database `CHECK` |
| Approval true and future data false | Database `CHECK` |
| Positive finite prices/quantities, non-negative finite fees | Database `CHECK` |
| Requested notional equals authoritative quantity times reference price | Database `CHECK` when notional is present |
| LONG/SHORT stop-entry-target geometry | Database `CHECK` |
| Full FILLED order accounting | Database `CHECK` |
| Position OPEN/CLOSING/CLOSED accounting | Database `CHECK` |
| One active position per mode and symbol | PostgreSQL partial unique index |
| Bounded modes/states/types/causes/events/reasons | `VARCHAR` plus database `CHECK` |
| Idempotency keys and aggregate versions | Database `UNIQUE` constraints |
| `fill.quantity == order.requested_quantity` | Future repository transaction; cannot be a valid row-local `CHECK` |
| Exit quantity/version equals current position snapshot | Future repository transaction with row lock/version compare |
| Exact aggregate version `+1` | Future repository compare-and-swap transaction |
| Duplicate causal action returns existing result without mutation | Future repository workflow using unique keys |
| Terminal aggregate cannot reopen | Domain state machine plus future repository compare-and-swap |
| Immutable/append-only rows | Domain contract plus future repository permissions; no new production trigger |

## Index evaluation

Indexes already supplied by primary keys or unique constraints are not
duplicated.

| INDEX | QUERY | RATIONALE | WRITE_COST |
|---|---|---|---|
| `ix_paper_commands_processing_created` | Oldest command by processing state | Future bounded durable queue scan | One composite index entry per command/status update |
| `ix_paper_commands_pipeline_run_id` | Commands for a pipeline run | Causal audit lookup | One index entry per command |
| `ix_paper_commands_analysis_result_id` | Commands for an analysis result | Causal audit lookup | One index entry per command |
| `uq_paper_orders_command_role` | Orders for a command | Unique prefix already serves `command_id` lookup | Required uniqueness; no duplicate index |
| `ix_paper_orders_state_created_at` | Orders by state and creation time | Operational state scan | One index entry per order/state update |
| `uq_paper_fills_order_role` | Fills for an order | Unique prefix already serves `order_id` lookup | Required uniqueness; no duplicate index |
| `uq_paper_positions_active_mode_symbol` | Active position for mode/symbol | Enforces the multiplicity invariant | Partial entry only for OPEN/CLOSING rows |
| `ix_paper_positions_state_symbol` | Positions by state and symbol | State/symbol read model | One index entry per position/state update |
| `ix_paper_positions_updated_at` | Recently changed positions | Bounded reconciliation scan | One index entry per position update |
| `uq_paper_exit_position_version_cause` | Exit decisions for a position | Unique prefix already serves `position_id` lookup | Required uniqueness; no duplicate index |
| `ix_paper_journal_occurred_at` | Time-ordered journal projection | Bounded audit timeline | One index entry per journal row |
| `ix_paper_journal_aggregate` | Journal for an aggregate | Aggregate audit lookup | One composite entry per journal row |
| `ix_paper_journal_correlation_id` | Correlated causal chain | Cross-aggregate audit lookup | One index entry per journal row |

`paper_order_events(order_id, aggregate_version)` already provides the
order-event lookup path. Policy lookup is covered by its composite primary
key.

## Migration boundary

Revision 0009 creates the eight tables in dependency order and drops them in
reverse dependency order. It alters no existing table, rewrites no existing
table, seeds no policy, performs no data backfill, and is not approved for
production application.
