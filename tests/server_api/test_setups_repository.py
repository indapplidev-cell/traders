from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.engine_orchestrator.orchestrator_models import (
    OnlinePipelineResultRow,
    OnlinePipelineRun,
)
from app.server_api.repositories.records import CursorPosition, SetupQuery
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter


NOW = datetime(2026, 7, 27, 7, 0, tzinfo=timezone.utc)


def _adapter(tmp_path, *, rows: int = 4):
    engine = create_engine(f"sqlite:///{tmp_path / 'setups.db'}")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    run_values = []
    result_values = []
    for index in range(rows):
        run_id = f"run-{index:06d}"
        setup_id = f"setup:{index:06d}"
        run_values.append(
            {
                "run_id": run_id,
                "symbol": "BTCUSDT" if index % 2 == 0 else "ETHUSDT",
                "primary_timeframe": "15m",
                "closed_until_ms": 1_700_000_000_000 + index,
                "closed_until_utc": NOW,
                "status": "COMPLETED",
                "trigger_source": "test_fixture",
                "daemon_instance_id": "test",
                "setup_status": "SETUP_CANDIDATE",
                "strategy_status": "NO_ACTION",
                "risk_status": "NOT_EVALUATED",
                "paper_status": "NOT_CREATED",
                "updated_at": NOW,
                "created_at": NOW,
            }
        )
        result_values.append(
            {
                "run_id": run_id,
                "symbol": run_values[-1]["symbol"],
                "primary_timeframe": "15m",
                "closed_until_ms": run_values[-1]["closed_until_ms"],
                "market_data_payload_json": {"large": "m" * 4096},
                "analysis_payload_json": {"large": "a" * 4096},
                "setup_payload_json": {
                    "setup_id": setup_id,
                    "timeframe": "15m",
                    "status": "SETUP_CANDIDATE",
                    "setup_type": "BREAKOUT",
                    "direction_hint": "BULLISH",
                    "setup_quality": "GOOD",
                    "quality_score": 0.8,
                    "confirmation_state": "CONFIRMED",
                    "reason_codes": ["fixture"],
                },
                "strategy_payload_json": {"decision_status": "NO_ACTION"},
                "risk_payload_json": {"risk_status": "NOT_EVALUATED"},
                "paper_payload_json": {
                    "paper_status": "NOT_CREATED",
                    "hypothetical_entry_reference": "100.5",
                    "planned_rr": "2",
                },
                "module_reasons_json": {"large": "r" * 4096},
                "module_warnings_json": {"large": "w" * 4096},
                "safety_counters_json": {"future_bars_used_count": 0},
                "created_at": NOW,
            }
        )
    with engine.begin() as connection:
        if run_values:
            connection.execute(OnlinePipelineRun.__table__.insert(), run_values)
            connection.execute(
                OnlinePipelineResultRow.__table__.insert(), result_values
            )
    return engine, SqlAlchemyReadAdapter(sessionmaker(bind=engine))


def _capture_sql(engine):
    statements = []

    @event.listens_for(engine, "before_cursor_execute")
    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    return statements


def test_list_limit_is_applied_in_sql_before_bounded_summary_projection(tmp_path):
    engine, adapter = _adapter(tmp_path, rows=200)
    statements = _capture_sql(engine)

    page = adapter.list_setups(SetupQuery(limit=1))

    assert len(page.items) == 1
    assert page.has_more is True
    assert len(statements) == 1
    sql = statements[0].lower()
    assert " limit " in sql
    assert "order by" in sql
    assert "strategy_payload_json" not in sql
    assert "risk_payload_json" not in sql
    assert "paper_payload_json" not in sql
    assert "analysis_payload_json" not in sql
    assert "market_data_payload_json" not in sql


def test_list_order_and_cursor_are_stable_with_equal_timestamps(tmp_path):
    _engine, adapter = _adapter(tmp_path, rows=3)

    first = adapter.list_setups(SetupQuery(limit=1))
    first_item = first.items[0]
    second = adapter.list_setups(
        SetupQuery(
            limit=1,
            cursor=CursorPosition(
                first_item.updated_at,
                first_item.cursor_identifier or first_item.setup_id,
            ),
        )
    )

    assert first_item.setup_id == "setup:000002"
    assert second.items[0].setup_id == "setup:000001"
    assert first_item.setup_id != second.items[0].setup_id


def test_list_empty_and_filtered_results_are_bounded(tmp_path):
    _engine, adapter = _adapter(tmp_path, rows=4)

    empty = adapter.list_setups(SetupQuery(limit=100, symbol="SOLUSDT"))
    filtered = adapter.list_setups(
        SetupQuery(limit=100, symbol="BTCUSDT", status="SETUP_CANDIDATE")
    )

    assert empty.items == ()
    assert empty.has_more is False
    assert [item.symbol for item in filtered.items] == ["BTCUSDT", "BTCUSDT"]


def test_detail_uses_one_filtered_query_and_missing_returns_none(tmp_path):
    engine, adapter = _adapter(tmp_path, rows=10)
    statements = _capture_sql(engine)

    existing = adapter.get_setup("setup:000009")
    missing = adapter.get_setup("nonexistent")

    assert existing is not None
    assert existing.setup_id == "setup:000009"
    assert existing.hypothetical_entry is not None
    assert existing.planned_rr is not None
    assert missing is None
    assert len(statements) == 2
    for statement in statements:
        sql = " ".join(statement.lower().split())
        assert " where " in f" {sql} "
        assert " limit " in f" {sql} "
        assert "analysis_payload_json" not in sql
        assert "market_data_payload_json" not in sql
        assert "module_reasons_json" not in sql
        assert "module_warnings_json" not in sql
