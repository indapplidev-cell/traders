from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import Connection, inspect, select, text
from sqlalchemy.exc import DataError, IntegrityError

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitDecisionRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
    PaperSimulationPolicyRecord,
)
from app.db.base import Base
from tests.paper_persistence.conftest import MigrationCycle, PAPER_TABLES


NOW = datetime(2026, 7, 29, 6, 0, tzinfo=timezone.utc)


def policy_values(**changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "policy_id": "simulation:v1",
        "policy_version": 1,
        "status": "ACTIVE",
        "price_source": "NEXT_ELIGIBLE_CLOSED_1M_OPEN",
        "timeframe": "1m",
        "latency_candles": 1,
        "slippage_bps": Decimal("2"),
        "fee_bps": Decimal("10"),
        "partial_fill_enabled": False,
        "future_data_allowed": False,
        "intrabar_conflict_policy": "STOP_FIRST_CONSERVATIVE",
        "configuration_fingerprint": "policy-config:v1",
        "created_at": NOW,
        "retired_at": None,
    }
    values.update(changes)
    return values


def command_values(suffix: str = "1", **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "command_id": f"command:{suffix}",
        "idempotency_key": f"command-idem:{suffix}",
        "mode": "PAPER",
        "symbol": "BTCUSDT",
        "side": "LONG",
        "order_type": "MARKET_SIMULATED",
        "requested_quantity": Decimal("2"),
        "requested_notional": Decimal("200"),
        "entry_reference_price": Decimal("100"),
        "stop_price": Decimal("90"),
        "target_price": Decimal("120"),
        "strategy_decision_id": f"strategy:{suffix}",
        "risk_decision_id": f"risk:{suffix}",
        "setup_id": f"setup:{suffix}",
        "pipeline_run_id": f"run:{suffix}",
        "analysis_result_id": f"analysis:{suffix}",
        "closed_until_ms": 1_000,
        "created_at": NOW,
        "valid_until_ms": 2_000,
        "configuration_fingerprint": "config:v1",
        "simulation_policy_id": "simulation:v1",
        "fee_policy_id": "fee:v1",
        "slippage_policy_id": "slippage:v1",
        "latency_policy_id": "latency:v1",
        "final_paper_approval": True,
        "input_health_status": "CURRENT",
        "future_bars_used": False,
        "processing_status": "PENDING",
    }
    values.update(changes)
    return values


def order_values(suffix: str = "1", **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "order_id": f"order:{suffix}",
        "command_id": f"command:{suffix}",
        "idempotency_key": f"order-idem:{suffix}",
        "order_role": "ENTRY",
        "mode": "PAPER",
        "symbol": "BTCUSDT",
        "side": "LONG",
        "order_type": "MARKET_SIMULATED",
        "state": "CREATED",
        "requested_quantity": Decimal("2"),
        "filled_quantity": Decimal("0"),
        "average_fill_price": None,
        "total_fees": Decimal("0"),
        "created_at": NOW,
        "updated_at": NOW,
        "version": 0,
        "reason_code": "PAPER_ORDER_CREATED",
        "applied_fill_id": None,
    }
    values.update(changes)
    return values


def fill_values(suffix: str = "1", **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "fill_id": f"fill:{suffix}",
        "order_id": f"order:{suffix}",
        "idempotency_key": f"fill-idem:{suffix}",
        "fill_role": "ENTRY",
        "symbol": "BTCUSDT",
        "side": "LONG",
        "quantity": Decimal("2"),
        "price": Decimal("101"),
        "fee_amount": Decimal("0.2"),
        "fee_asset": "USDT",
        "filled_at": NOW,
        "source_closed_until_ms": 1_060,
        "simulation_policy_id": "simulation:v1",
        "slippage_policy_id": "slippage:v1",
        "fee_policy_id": "fee:v1",
        "latency_policy_id": "latency:v1",
        "future_bars_used": False,
    }
    values.update(changes)
    return values


def position_values(suffix: str = "1", **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "position_id": f"position:{suffix}",
        "mode": "PAPER",
        "symbol": "BTCUSDT",
        "side": "LONG",
        "state": "OPEN",
        "entry_order_id": f"order:{suffix}",
        "entry_fill_id": f"fill:{suffix}",
        "entry_quantity": Decimal("2"),
        "remaining_quantity": Decimal("2"),
        "average_entry_price": Decimal("101"),
        "average_exit_price": None,
        "entry_fees": Decimal("0.2"),
        "exit_fees": Decimal("0"),
        "realized_pnl": Decimal("-0.2"),
        "unrealized_pnl": Decimal("0"),
        "stop_price": Decimal("90"),
        "target_price": Decimal("120"),
        "opened_at": NOW,
        "closed_at": None,
        "last_mark_price": Decimal("101"),
        "last_mark_closed_until_ms": 1_060,
        "version": 0,
        "reason_code": "PAPER_POSITION_OPENED",
        "exit_fill_id": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(changes)
    return values


def exit_values(suffix: str = "1", **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "exit_decision_id": f"exit:{suffix}",
        "idempotency_key": f"exit-idem:{suffix}",
        "position_id": f"position:{suffix}",
        "position_version": 0,
        "cause": "STOP_LOSS",
        "decision_price": Decimal("90"),
        "requested_close_quantity": Decimal("2"),
        "source_closed_until_ms": 1_120,
        "decided_at": NOW,
        "reason_code": "PAPER_EXIT_STOP_LOSS_TRIGGERED",
    }
    values.update(changes)
    return values


def journal_values(suffix: str = "1", **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "journal_entry_id": f"journal:{suffix}",
        "event_type": "PAPER_COMMAND_CREATED",
        "occurred_at": NOW,
        "aggregate_type": "paper_command",
        "aggregate_id": f"command:{suffix}",
        "aggregate_version": 0,
        "correlation_id": f"command:{suffix}",
        "causation_id": f"analysis:{suffix}",
        "idempotency_key": f"journal-idem:{suffix}",
        "reason_code": "PAPER_ORDER_CREATED",
        "command_id": f"command:{suffix}",
        "order_id": None,
        "fill_id": None,
        "position_id": None,
        "exit_decision_id": None,
    }
    values.update(changes)
    return values


def seed_command(connection: Connection, suffix: str = "1", **changes: object) -> None:
    connection.execute(PaperExecutionCommandRecord.__table__.insert(), command_values(suffix, **changes))


def seed_order(connection: Connection, suffix: str = "1", **changes: object) -> None:
    seed_command(connection, suffix)
    connection.execute(PaperOrderRecord.__table__.insert(), order_values(suffix, **changes))


def seed_fill(connection: Connection, suffix: str = "1", **changes: object) -> None:
    seed_order(connection, suffix)
    connection.execute(PaperFillRecord.__table__.insert(), fill_values(suffix, **changes))


def seed_position(connection: Connection, suffix: str = "1", **changes: object) -> None:
    seed_fill(connection, suffix)
    connection.execute(PaperPositionRecord.__table__.insert(), position_values(suffix, **changes))


def assert_rejected(connection: Connection, table: object, values: dict[str, object]) -> None:
    with pytest.raises((IntegrityError, DataError)):
        connection.execute(table.insert(), values)


def test_upgrade_downgrade_reupgrade_cycle(
    postgres_engine_and_cycle: tuple[object, MigrationCycle],
) -> None:
    _, cycle = postgres_engine_and_cycle
    assert cycle.baseline_revision == "0008_engine_orchestrator_freshness_retry"
    assert cycle.upgraded_revision == "0009_paper_trading_persistence_foundation"
    assert cycle.paper_tables_after_upgrade == PAPER_TABLES
    assert cycle.paper_tables_after_downgrade == frozenset()
    assert cycle.preexisting_schema_unchanged
    assert cycle.reupgraded_revision == "0009_paper_trading_persistence_foundation"


def test_all_eight_paper_tables_are_present(postgres_engine_and_cycle: tuple[object, MigrationCycle]) -> None:
    engine, _ = postgres_engine_and_cycle
    assert set(inspect(engine).get_table_names()) >= PAPER_TABLES


def test_live_migration_matches_authoritative_paper_metadata(
    postgres_engine_and_cycle: tuple[object, MigrationCycle],
) -> None:
    engine, _ = postgres_engine_and_cycle
    inspector = inspect(engine)
    for table_name in sorted(PAPER_TABLES):
        table = Base.metadata.tables[table_name]
        assert {column.name for column in table.columns} == {
            column["name"] for column in inspector.get_columns(table_name)
        }
        assert {column.name for column in table.primary_key.columns} == set(
            inspector.get_pk_constraint(table_name)["constrained_columns"]
        )
        assert {
            constraint.name
            for constraint in table.constraints
            if constraint.__class__.__name__ == "UniqueConstraint"
        } == {
            constraint["name"]
            for constraint in inspector.get_unique_constraints(table_name)
        }
        assert {
            constraint.name
            for constraint in table.constraints
            if constraint.__class__.__name__ == "CheckConstraint"
        } == {
            constraint["name"]
            for constraint in inspector.get_check_constraints(table_name)
        }
        assert {index.name for index in table.indexes} == {
            index["name"] for index in inspector.get_indexes(table_name)
            if not index.get("duplicates_constraint")
        }


def test_no_float_monetary_or_quantity_columns(pg_connection: Connection) -> None:
    rows = pg_connection.execute(
        text(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name LIKE 'paper\\_%' ESCAPE '\\'
              AND data_type IN ('real', 'double precision')
            """
        )
    ).all()
    assert rows == []


def test_partial_unique_active_position_index_is_postgresql_enforced(
    pg_connection: Connection,
) -> None:
    definition = pg_connection.execute(
        text(
            """
            SELECT pg_get_indexdef(indexrelid)
            FROM pg_index
            WHERE indexrelid = 'uq_paper_positions_active_mode_symbol'::regclass
            """
        )
    ).scalar_one()
    assert "UNIQUE INDEX" in definition
    assert "WHERE" in definition
    assert "OPEN" in definition and "CLOSING" in definition


def test_all_paper_foreign_keys_are_restrictive(pg_connection: Connection) -> None:
    actions = pg_connection.execute(
        text(
            """
            SELECT confdeltype
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE c.contype = 'f' AND t.relname LIKE 'paper\\_%' ESCAPE '\\'
            """
        )
    ).scalars().all()
    assert actions
    assert set(actions) <= {"a", "r"}


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("mode", "LIVE"),
        ("mode", "OFF"),
        ("final_paper_approval", False),
        ("future_bars_used", True),
        ("requested_quantity", Decimal("0")),
        ("requested_quantity", Decimal("-1")),
        ("entry_reference_price", Decimal("0")),
        ("stop_price", Decimal("-1")),
        ("target_price", Decimal("0")),
        ("closed_until_ms", -1),
        ("input_health_status", "UNKNOWN"),
        ("side", "FLAT"),
        ("order_type", "LIMIT"),
        ("processing_status", "CLAIMED"),
        ("strategy_decision_id", " "),
        ("requested_notional", Decimal("199")),
        ("requested_quantity", Decimal("NaN")),
        ("entry_reference_price", Decimal("Infinity")),
    ],
)
def test_invalid_command_values_are_rejected(
    pg_connection: Connection,
    field: str,
    invalid: object,
) -> None:
    assert_rejected(
        pg_connection,
        PaperExecutionCommandRecord.__table__,
        command_values(**{field: invalid}),
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"side": "LONG", "stop_price": Decimal("100")},
        {"side": "LONG", "target_price": Decimal("99")},
        {
            "side": "SHORT",
            "stop_price": Decimal("90"),
            "target_price": Decimal("120"),
        },
        {"valid_until_ms": 999},
    ],
)
def test_invalid_command_geometry_and_validity_are_rejected(
    pg_connection: Connection,
    changes: dict[str, object],
) -> None:
    assert_rejected(
        pg_connection,
        PaperExecutionCommandRecord.__table__,
        command_values(**changes),
    )


def test_duplicate_command_idempotency_is_rejected(pg_connection: Connection) -> None:
    seed_command(pg_connection)
    assert_rejected(
        pg_connection,
        PaperExecutionCommandRecord.__table__,
        command_values("2", idempotency_key="command-idem:1"),
    )


def test_policy_contract_row_round_trips(pg_connection: Connection) -> None:
    pg_connection.execute(PaperSimulationPolicyRecord.__table__.insert(), policy_values())
    row = pg_connection.execute(select(PaperSimulationPolicyRecord.__table__)).mappings().one()
    assert row["latency_candles"] == 1
    assert row["slippage_bps"] == Decimal("2.0000000000")
    assert row["fee_bps"] == Decimal("10.0000000000")


@pytest.mark.parametrize(
    "changes",
    [
        {"policy_version": 0},
        {"status": "UNKNOWN"},
        {"price_source": "CURRENT_OPEN"},
        {"timeframe": "5m"},
        {"latency_candles": -1},
        {"slippage_bps": Decimal("-0.1")},
        {"fee_bps": Decimal("NaN")},
        {"partial_fill_enabled": True},
        {"future_data_allowed": True},
        {"intrabar_conflict_policy": "TARGET_FIRST"},
        {"status": "RETIRED", "retired_at": None},
    ],
)
def test_invalid_policy_values_are_rejected(
    pg_connection: Connection,
    changes: dict[str, object],
) -> None:
    assert_rejected(
        pg_connection,
        PaperSimulationPolicyRecord.__table__,
        policy_values(**changes),
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "UNKNOWN"},
        {"requested_quantity": Decimal("0")},
        {"filled_quantity": Decimal("-1")},
        {"filled_quantity": Decimal("3")},
        {"total_fees": Decimal("-0.1")},
        {"version": -1},
        {"updated_at": NOW - timedelta(seconds=1)},
        {"state": "FILLED", "filled_quantity": Decimal("0")},
        {
            "state": "FILLED",
            "filled_quantity": Decimal("2"),
            "average_fill_price": None,
            "total_fees": Decimal("0.2"),
            "applied_fill_id": "fill:1",
        },
        {"state": "OPEN", "filled_quantity": Decimal("1")},
    ],
)
def test_invalid_order_values_are_rejected(
    pg_connection: Connection,
    changes: dict[str, object],
) -> None:
    seed_command(pg_connection)
    assert_rejected(pg_connection, PaperOrderRecord.__table__, order_values(**changes))


def test_duplicate_command_order_role_is_rejected(pg_connection: Connection) -> None:
    seed_order(pg_connection)
    assert_rejected(
        pg_connection,
        PaperOrderRecord.__table__,
        order_values("2", command_id="command:1"),
    )


def test_duplicate_order_idempotency_is_rejected(pg_connection: Connection) -> None:
    seed_order(pg_connection)
    seed_command(pg_connection, "2")
    assert_rejected(
        pg_connection,
        PaperOrderRecord.__table__,
        order_values("2", idempotency_key="order-idem:1"),
    )


def test_orphan_order_is_rejected(pg_connection: Connection) -> None:
    assert_rejected(pg_connection, PaperOrderRecord.__table__, order_values())


def order_event_values(suffix: str = "1", **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "order_event_id": f"order-event:{suffix}",
        "order_id": "order:1",
        "event_type": "PAPER_ORDER_CREATED",
        "from_state": None,
        "to_state": "CREATED",
        "aggregate_version": 0,
        "idempotency_key": f"order-event-idem:{suffix}",
        "correlation_id": "command:1",
        "causation_id": "command:1",
        "reason_code": "PAPER_ORDER_CREATED",
        "occurred_at": NOW,
    }
    values.update(changes)
    return values


@pytest.mark.parametrize(
    "changes",
    [
        {"event_type": "UNKNOWN"},
        {"from_state": "UNKNOWN"},
        {"to_state": "UNKNOWN"},
        {"aggregate_version": -1},
        {"correlation_id": " "},
        {"reason_code": "UNKNOWN"},
    ],
)
def test_invalid_order_event_values_are_rejected(
    pg_connection: Connection,
    changes: dict[str, object],
) -> None:
    seed_order(pg_connection)
    assert_rejected(
        pg_connection,
        PaperOrderEventRecord.__table__,
        order_event_values(**changes),
    )


def test_duplicate_order_event_version_is_rejected(pg_connection: Connection) -> None:
    seed_order(pg_connection)
    pg_connection.execute(PaperOrderEventRecord.__table__.insert(), order_event_values())
    assert_rejected(
        pg_connection,
        PaperOrderEventRecord.__table__,
        order_event_values("2"),
    )


def test_orphan_order_event_is_rejected(pg_connection: Connection) -> None:
    assert_rejected(
        pg_connection,
        PaperOrderEventRecord.__table__,
        order_event_values(),
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"fill_role": "PARTIAL"},
        {"side": "FLAT"},
        {"quantity": Decimal("0")},
        {"quantity": Decimal("-1")},
        {"quantity": Decimal("NaN")},
        {"price": Decimal("0")},
        {"price": Decimal("Infinity")},
        {"fee_amount": Decimal("-0.1")},
        {"fee_asset": " "},
        {"source_closed_until_ms": -1},
        {"future_bars_used": True},
    ],
)
def test_invalid_fill_values_are_rejected(
    pg_connection: Connection,
    changes: dict[str, object],
) -> None:
    seed_order(pg_connection)
    assert_rejected(pg_connection, PaperFillRecord.__table__, fill_values(**changes))


def test_duplicate_fill_role_is_rejected(pg_connection: Connection) -> None:
    seed_fill(pg_connection)
    assert_rejected(pg_connection, PaperFillRecord.__table__, fill_values("2", order_id="order:1"))


def test_duplicate_fill_idempotency_is_rejected(pg_connection: Connection) -> None:
    seed_fill(pg_connection)
    seed_order(pg_connection, "2")
    assert_rejected(
        pg_connection,
        PaperFillRecord.__table__,
        fill_values("2", idempotency_key="fill-idem:1"),
    )


def test_orphan_fill_is_rejected(pg_connection: Connection) -> None:
    assert_rejected(pg_connection, PaperFillRecord.__table__, fill_values())


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "UNKNOWN"},
        {"mode": "LIVE"},
        {"entry_quantity": Decimal("0")},
        {"remaining_quantity": Decimal("-1")},
        {"remaining_quantity": Decimal("3")},
        {"average_entry_price": Decimal("0")},
        {"entry_fees": Decimal("-0.1")},
        {"exit_fees": Decimal("-0.1")},
        {"stop_price": Decimal("101")},
        {"version": -1},
        {"last_mark_closed_until_ms": -1},
        {"state": "OPEN", "closed_at": NOW},
        {"state": "OPEN", "average_exit_price": Decimal("110")},
        {"state": "CLOSING", "remaining_quantity": Decimal("0")},
        {"state": "CLOSED", "remaining_quantity": Decimal("1")},
        {
            "state": "CLOSED",
            "remaining_quantity": Decimal("0"),
            "closed_at": None,
            "average_exit_price": Decimal("110"),
            "exit_fill_id": "fill:exit",
        },
        {
            "state": "CLOSED",
            "remaining_quantity": Decimal("0"),
            "closed_at": NOW,
            "average_exit_price": None,
            "exit_fill_id": "fill:exit",
        },
        {
            "state": "CLOSED",
            "remaining_quantity": Decimal("0"),
            "closed_at": NOW,
            "average_exit_price": Decimal("110"),
            "exit_fill_id": "fill:exit",
            "unrealized_pnl": Decimal("1"),
        },
    ],
)
def test_invalid_position_values_are_rejected(
    pg_connection: Connection,
    changes: dict[str, object],
) -> None:
    seed_fill(pg_connection)
    assert_rejected(pg_connection, PaperPositionRecord.__table__, position_values(**changes))


def test_duplicate_active_mode_symbol_is_rejected(pg_connection: Connection) -> None:
    seed_position(pg_connection)
    seed_fill(pg_connection, "2")
    assert_rejected(pg_connection, PaperPositionRecord.__table__, position_values("2"))


def test_closed_history_allows_new_active_position(pg_connection: Connection) -> None:
    seed_fill(pg_connection)
    pg_connection.execute(
        PaperPositionRecord.__table__.insert(),
        position_values(
            state="CLOSED",
            remaining_quantity=Decimal("0"),
            average_exit_price=Decimal("110"),
            closed_at=NOW + timedelta(minutes=1),
            exit_fill_id="fill:exit",
            unrealized_pnl=Decimal("0"),
        ),
    )
    seed_fill(pg_connection, "2")
    pg_connection.execute(PaperPositionRecord.__table__.insert(), position_values("2"))


def test_orphan_position_is_rejected(pg_connection: Connection) -> None:
    assert_rejected(pg_connection, PaperPositionRecord.__table__, position_values())


@pytest.mark.parametrize(
    "changes",
    [
        {"cause": "MANUAL"},
        {"position_version": -1},
        {"decision_price": Decimal("0")},
        {"decision_price": Decimal("NaN")},
        {"requested_close_quantity": Decimal("0")},
        {"source_closed_until_ms": -1},
        {"reason_code": "UNKNOWN"},
    ],
)
def test_invalid_exit_decision_values_are_rejected(
    pg_connection: Connection,
    changes: dict[str, object],
) -> None:
    seed_position(pg_connection)
    assert_rejected(
        pg_connection,
        PaperExitDecisionRecord.__table__,
        exit_values(**changes),
    )


def test_duplicate_exit_position_version_cause_is_rejected(pg_connection: Connection) -> None:
    seed_position(pg_connection)
    pg_connection.execute(PaperExitDecisionRecord.__table__.insert(), exit_values())
    assert_rejected(
        pg_connection,
        PaperExitDecisionRecord.__table__,
        exit_values("2", position_id="position:1"),
    )


def test_duplicate_exit_idempotency_is_rejected(pg_connection: Connection) -> None:
    seed_position(pg_connection)
    pg_connection.execute(PaperExitDecisionRecord.__table__.insert(), exit_values())
    assert_rejected(
        pg_connection,
        PaperExitDecisionRecord.__table__,
        exit_values("2", position_id="position:1", cause="TAKE_PROFIT", idempotency_key="exit-idem:1"),
    )


def test_orphan_exit_decision_is_rejected(pg_connection: Connection) -> None:
    assert_rejected(pg_connection, PaperExitDecisionRecord.__table__, exit_values())


@pytest.mark.parametrize(
    "changes",
    [
        {"event_type": "UNKNOWN"},
        {"aggregate_type": "unbounded"},
        {"aggregate_version": -1},
        {"aggregate_id": " "},
        {"reason_code": "UNKNOWN"},
    ],
)
def test_invalid_journal_values_are_rejected(
    pg_connection: Connection,
    changes: dict[str, object],
) -> None:
    seed_command(pg_connection)
    assert_rejected(
        pg_connection,
        PaperJournalEntryRecord.__table__,
        journal_values(**changes),
    )


def test_duplicate_journal_idempotency_is_rejected(pg_connection: Connection) -> None:
    seed_command(pg_connection)
    pg_connection.execute(PaperJournalEntryRecord.__table__.insert(), journal_values())
    assert_rejected(
        pg_connection,
        PaperJournalEntryRecord.__table__,
        journal_values("2", command_id="command:1", idempotency_key="journal-idem:1"),
    )


def test_orphan_journal_causal_fk_is_rejected(pg_connection: Connection) -> None:
    assert_rejected(
        pg_connection,
        PaperJournalEntryRecord.__table__,
        journal_values(),
    )


@pytest.mark.parametrize("parent", ["command", "order", "fill", "position"])
def test_restrictive_delete_preserves_causal_history(
    pg_connection: Connection,
    parent: str,
) -> None:
    seed_position(pg_connection)
    pg_connection.execute(PaperExitDecisionRecord.__table__.insert(), exit_values())
    tables = {
        "command": (PaperExecutionCommandRecord.__table__, "command_id", "command:1"),
        "order": (PaperOrderRecord.__table__, "order_id", "order:1"),
        "fill": (PaperFillRecord.__table__, "fill_id", "fill:1"),
        "position": (PaperPositionRecord.__table__, "position_id", "position:1"),
    }
    table, column, value = tables[parent]
    with pytest.raises(IntegrityError):
        pg_connection.execute(table.delete().where(table.c[column] == value))


@pytest.mark.parametrize(
    "value",
    [
        Decimal("0.000000000000000001"),
        Decimal("99999999999999999999.999999999999999999"),
        Decimal("123456789.123456789123456789"),
    ],
)
def test_decimal_round_trip_is_lossless(
    pg_connection: Connection,
    value: Decimal,
) -> None:
    seed_command(
        pg_connection,
        requested_quantity=value,
        requested_notional=None,
    )
    stored = pg_connection.execute(
        select(PaperExecutionCommandRecord.requested_quantity)
    ).scalar_one()
    assert stored == value
    assert isinstance(stored, Decimal)


@pytest.mark.parametrize(
    "offset",
    [timezone.utc, timezone(timedelta(hours=3)), timezone(timedelta(hours=-7))],
)
def test_timezone_round_trip_preserves_instant(
    pg_connection: Connection,
    offset: timezone,
) -> None:
    instant = datetime(2026, 7, 29, 9, 15, 42, 123456, tzinfo=offset)
    seed_command(pg_connection, created_at=instant)
    stored = pg_connection.execute(select(PaperExecutionCommandRecord.created_at)).scalar_one()
    assert stored.tzinfo is not None
    assert stored.astimezone(timezone.utc) == instant.astimezone(timezone.utc)
