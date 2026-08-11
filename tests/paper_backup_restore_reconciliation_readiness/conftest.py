from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

import pytest

from app.engine_paper.reconciliation import (
    EXPECTED_SCHEMA_HEAD,
    PAPER_TABLES,
    PaperReconciliationRequest,
    PaperReconciliationScope,
)


def canonical_rows() -> dict[str, list[dict[str, Any]]]:
    commands = [{
        "command_id": "command-1", "idempotency_key": "command-semantic-1",
        "symbol": "BTCUSDT", "final_paper_approval": True,
    }]
    orders = [
        {"order_id": "entry-order-1", "command_id": "command-1", "idempotency_key": "entry-semantic-1", "order_role": "ENTRY", "state": "FILLED", "version": 3},
        {"order_id": "close-order-1", "command_id": "command-1", "idempotency_key": "close-semantic-1", "order_role": "EXIT", "state": "FILLED", "version": 3},
    ]
    fills = [
        {"fill_id": "entry-fill-1", "order_id": "entry-order-1", "idempotency_key": "entry-fill-semantic-1", "fill_role": "ENTRY", "fee_amount": 1},
        {"fill_id": "close-fill-1", "order_id": "close-order-1", "idempotency_key": "close-fill-semantic-1", "fill_role": "EXIT", "fee_amount": 1},
    ]
    positions = [{
        "position_id": "position-1", "state": "CLOSED", "entry_order_id": "entry-order-1",
        "entry_fill_id": "entry-fill-1", "exit_fill_id": "close-fill-1", "exit_fees": 1,
        "realized_pnl": 10, "closed_at": "2026-01-01T00:10:00+00:00", "version": 3,
    }]
    cursors = [{
        "cursor_id": "cursor-1", "position_id": "position-1",
        "position_opened_closed_until_ms": 1_000, "last_evaluated_closed_until_ms": 2_000,
        "version": 2,
    }]
    decisions = [{
        "exit_decision_id": "exit-decision-1", "idempotency_key": "decision-semantic-1",
        "position_id": "position-1", "position_version": 2, "cause": "TAKE_PROFIT",
    }]
    events: list[dict[str, Any]] = []
    for prefix, order_id in (("entry", "entry-order-1"), ("close", "close-order-1")):
        states = (
            ("PAPER_ORDER_CREATED", None, "CREATED"),
            ("PAPER_ORDER_VALIDATED", "CREATED", "VALIDATED"),
            ("PAPER_ORDER_OPENED", "VALIDATED", "OPEN"),
            ("PAPER_ORDER_FILLED", "OPEN", "FILLED"),
        )
        for version, (event_type, from_state, to_state) in enumerate(states):
            events.append({
                "order_event_id": f"{prefix}-event-{version}", "order_id": order_id,
                "event_type": event_type, "from_state": from_state, "to_state": to_state,
                "aggregate_version": version,
            })
    journal_types = [event["event_type"] for event in events]
    journal_types.extend(("PAPER_COMMAND_CREATED", "PAPER_POSITION_OPENED", "PAPER_EXIT_TRIGGERED", "PAPER_POSITION_CLOSED"))
    journal = []
    for index, event_type in enumerate(journal_types):
        order_id = "entry-order-1" if index < 4 else "close-order-1" if index < 8 else None
        journal.append({
            "journal_entry_id": f"journal-{index}", "event_type": event_type,
            "command_id": "command-1", "order_id": order_id,
            "fill_id": "entry-fill-1" if index == 3 else "close-fill-1" if index == 7 else None,
            "position_id": "position-1" if index in (9, 10, 11) else None,
            "exit_decision_id": "exit-decision-1" if index in (10, 11) else None,
        })
    return dict(zip(PAPER_TABLES, (commands, orders, fills, positions, cursors, decisions, events, journal)))


class FakeReader:
    def __init__(self, rows=None, *, schema_head=EXPECTED_SCHEMA_HEAD, read_only=True, fail_table=None):
        self.rows = deepcopy(rows if rows is not None else canonical_rows())
        self._schema_head = schema_head
        self._read_only = read_only
        self.fail_table = fail_table
        self.query_count = 0
        self.paper_table_queries = 0
        self.business_mutations = 0
        self.schema_mutations = 0
        self.closed = False

    def begin_read_only(self):
        self.query_count += 1
        return self._read_only

    def schema_head(self):
        self.query_count += 1
        return self._schema_head

    def read(self, table: str, limit: int) -> Sequence[Mapping[str, Any]]:
        self.query_count += 1
        self.paper_table_queries += 1
        if table == self.fail_table:
            raise RuntimeError("injected")
        return deepcopy(self.rows[table][: limit + 1])

    def close(self):
        self.closed = True


@pytest.fixture
def rows():
    return canonical_rows()


@pytest.fixture
def reconcile_request():
    return PaperReconciliationRequest(
        request_id="request-1", correlation_id="correlation-1",
        target_class="ISOLATED_POSTGRESQL_0012", target_identity="task-owned-db-1",
        expected_schema_head=EXPECTED_SCHEMA_HEAD,
        scope=PaperReconciliationScope(full_isolated_fixture=True),
    )
