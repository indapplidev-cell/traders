from __future__ import annotations

import ast
import importlib.util
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.db.paper_mappings import (
    orm_values_to_paper_command,
    orm_values_to_paper_event,
    orm_values_to_paper_exit_decision,
    orm_values_to_paper_fill,
    orm_values_to_paper_order,
    orm_values_to_paper_position,
    paper_command_to_orm_values,
    paper_event_to_journal_values,
    paper_exit_decision_to_orm_values,
    paper_fill_to_orm_values,
    paper_order_to_orm_values,
    paper_position_to_orm_values,
)
from app.engine_exit.paper_exit import PaperExitDecision
from app.engine_journal.paper_events import PaperDomainEvent
from app.engine_safety.paper_domain import PaperEventType, PaperExitCause, PaperReasonCode
from tests.paper_domain.conftest import (
    make_command,
    make_fill,
    make_open_position,
    make_order,
)
from app.engine_safety.paper_domain import PaperOrderState


NOW = datetime(2026, 7, 29, 6, 0, tzinfo=timezone.utc)


def test_command_domain_orm_domain_round_trip() -> None:
    command = make_command()
    assert orm_values_to_paper_command(paper_command_to_orm_values(command)) == command


def test_order_domain_orm_domain_round_trip() -> None:
    order = make_order(PaperOrderState.FILLED)
    values = paper_order_to_orm_values(order, order_role="ENTRY")
    assert values["mode"] == "PAPER"
    assert values["order_role"] == "ENTRY"
    assert orm_values_to_paper_order(values) == order


def test_fill_domain_orm_domain_round_trip() -> None:
    fill = make_fill()
    values = paper_fill_to_orm_values(fill, fill_role="ENTRY")
    assert values["fill_role"] == "ENTRY"
    assert orm_values_to_paper_fill(values) == fill


def test_position_domain_orm_domain_round_trip() -> None:
    position = make_open_position()
    values = paper_position_to_orm_values(position)
    assert values["created_at"] == position.opened_at
    assert orm_values_to_paper_position(values) == position


def test_exit_decision_domain_orm_domain_round_trip() -> None:
    decision = PaperExitDecision(
        exit_decision_id="exit:1",
        idempotency_key="exit-idem:1",
        position_id="position:1",
        position_version=0,
        cause=PaperExitCause.STOP_LOSS,
        decision_price=Decimal("90"),
        requested_close_quantity=Decimal("2"),
        source_closed_until_ms=1_120,
        decided_at=NOW,
        reason_code=PaperReasonCode.PAPER_EXIT_STOP_LOSS_TRIGGERED,
    )
    assert (
        orm_values_to_paper_exit_decision(
            paper_exit_decision_to_orm_values(decision)
        )
        == decision
    )


def test_event_journal_projection_round_trip() -> None:
    event = PaperDomainEvent(
        event_id="event:1",
        event_type=PaperEventType.PAPER_COMMAND_CREATED,
        occurred_at=NOW,
        aggregate_type="paper_command",
        aggregate_id="command:1",
        correlation_id="command:1",
        causation_id="analysis:1",
        reason_code=PaperReasonCode.PAPER_ORDER_CREATED,
        aggregate_version=0,
    )
    values = paper_event_to_journal_values(event, command_id="command:1")
    assert values["idempotency_key"] == event.event_id
    assert orm_values_to_paper_event(values) == event


def test_mapping_module_has_no_session_clock_random_or_commit_access() -> None:
    path = Path(__file__).parents[2] / "app/db/paper_mappings.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not ({"sqlalchemy", "random", "uuid", "time"} & (imported_roots | imported_from))
    assert not ({"commit", "flush", "execute", "now", "utcnow", "uuid4"} & called_attributes)


def test_migration_has_exact_linear_revision_identity() -> None:
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/0009_paper_trading_persistence_foundation.py"
    )
    spec = importlib.util.spec_from_file_location("paper_persistence_0009", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.revision == "0009_paper_trading_persistence_foundation"
    assert migration.down_revision == "0008_engine_orchestrator_freshness_retry"


def test_migration_upgrade_has_no_existing_table_mutation_or_seed() -> None:
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/0009_paper_trading_persistence_foundation.py"
    )
    source = path.read_text(encoding="utf-8")
    upgrade = source[source.index("def upgrade()") : source.index("def downgrade()")]
    assert "alter_column(" not in upgrade
    assert "add_column(" not in upgrade
    assert "drop_column(" not in upgrade
    assert "op.execute(" not in upgrade
    assert "bulk_insert(" not in upgrade
    assert "server_default=sa.func.now()" not in upgrade
