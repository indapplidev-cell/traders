from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db.paper_models import ScalpingStalePositionShadowRecord
from app.engine_paper.fill_simulator import PaperFillCandle
from app.engine_paper.scalping_shadow import ShadowCostInputs
from app.engine_paper.stale_position_shadow import PostgresStalePositionShadowService
from app.engine_position.paper_models import PaperPosition
from app.engine_safety.paper_domain import (
    ExecutionMode, PaperPositionState, PaperReasonCode, PaperSide,
)


def _position(opened_at: datetime) -> PaperPosition:
    return PaperPosition(
        position_id="isolated-stale-position", mode=ExecutionMode.PAPER,
        symbol="BTCUSDT", side=PaperSide.LONG, state=PaperPositionState.OPEN,
        entry_order_id="isolated-entry-order", entry_fill_id="isolated-entry-fill",
        entry_quantity=Decimal("1"), remaining_quantity=Decimal("1"),
        average_entry_price=Decimal("100"), average_exit_price=None,
        entry_fees=Decimal("0.09"), exit_fees=Decimal("0"),
        realized_pnl=Decimal("0"), unrealized_pnl=Decimal("0"),
        stop_price=Decimal("99"), target_price=Decimal("102"),
        opened_at=opened_at, closed_at=None, last_mark_price=Decimal("100"),
        last_mark_closed_until_ms=int(opened_at.timestamp() * 1000), version=0,
        reason_code=PaperReasonCode.PAPER_POSITION_OPENED,
    )


def _candle(opened_at: datetime, minute: int, close: str) -> PaperFillCandle:
    open_ms = int((opened_at + timedelta(minutes=minute - 1)).timestamp() * 1000)
    return PaperFillCandle(
        symbol="BTCUSDT", timeframe="1m", open_time_ms=open_ms,
        close_boundary_ms=open_ms + 60_000,
        open_price=Decimal(close), high_price=Decimal(close) + Decimal("0.1"),
        low_price=Decimal(close) - Decimal("0.1"), close_price=Decimal(close),
        is_closed=True, observed_closed_until_ms=open_ms + 60_000,
    )


class CostSource:
    real_order_calls = 0

    def load(self, symbol, entry, *, safety_margin_bps):
        assert symbol == "BTCUSDT" and safety_margin_bps == 0
        return ShadowCostInputs(
            entry_fee_bps=Decimal("9"), exit_fee_bps=Decimal("9"),
            entry_slippage_bps=Decimal("2"), exit_slippage_bps=Decimal("2"),
            adverse_fill_reserve_bps=Decimal("3"), spread_bps=Decimal("2"),
            depth_impact_bps=Decimal("0"), fee_source="BINANCE_ACCOUNT_COMMISSION_SNAPSHOT",
            commission_authoritative=True, spread_authoritative=True,
            depth_authoritative=True, economic_input_timestamp_ms=1_000,
            decision_cutoff_timestamp_ms=1_000, commission_provenance={
                "source": "BINANCE_ACCOUNT_COMMISSION", "real_account_data": True,
            },
        )


@pytest.mark.integration
def test_open_soft_hard_shadow_lifecycle_persists_without_execution_mutation(tmp_path):
    raw = os.environ.get("STALE_POSITION_E2E_DATABASE_URL")
    if not raw:
        pytest.skip("STALE_POSITION_E2E_DATABASE_URL is not configured")
    url = make_url(raw)
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or not (url.database or "").startswith("stale_shadow_test_")
        or not (url.username or "").startswith("stale_shadow_test_")
    ):
        pytest.fail("task-owned loopback stale_shadow_test_ PostgreSQL is required")
    engine = create_engine(raw, hide_parameters=True)
    with engine.begin() as connection:
        identity = connection.execute(text(
            "SELECT current_database(), current_user, "
            "current_setting('server_version_num')::int / 10000"
        )).one()
        role = connection.execute(text(
            "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
            "FROM pg_roles WHERE rolname=current_user"
        )).one()
        assert identity == (url.database, url.username, 16)
        assert not any(role)
        connection.execute(text(
            "DROP TABLE IF EXISTS scalping_stale_position_shadow_diagnostics CASCADE"
        ))
        connection.execute(text("DROP TABLE IF EXISTS paper_execution_commands CASCADE"))
        connection.execute(text("DROP TABLE IF EXISTS paper_accounting_events CASCADE"))
        connection.execute(text("DROP TABLE IF EXISTS paper_positions CASCADE"))
        connection.execute(text(
            "CREATE TABLE paper_positions (position_id varchar(128) PRIMARY KEY)"
        ))
        connection.execute(text(
            "CREATE TABLE paper_execution_commands (command_id varchar(128) PRIMARY KEY)"
        ))
        connection.execute(text(
            "CREATE TABLE paper_accounting_events (event_id varchar(128) PRIMARY KEY)"
        ))
        ScalpingStalePositionShadowRecord.__table__.create(connection)
        connection.execute(text(
            "INSERT INTO paper_positions(position_id) VALUES ('isolated-stale-position')"
        ))
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    opened = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)
    position = _position(opened)
    costs = CostSource()
    service = PostgresStalePositionShadowService(
        sessions, costs, status_path=tmp_path / "stale-position-shadow.json"
    )
    soft = service.evaluate_and_persist(
        position, tuple(_candle(opened, minute, "100.1") for minute in range(1, 11))
    )
    assert soft is not None and soft.shadow_decision == "EXTENSION_ALLOWED"
    assert position.state is PaperPositionState.OPEN and position.version == 0
    hard = service.evaluate_and_persist(
        position, tuple(_candle(opened, minute, "100.1") for minute in range(1, 16))
    )
    assert hard is not None and hard.shadow_decision == "HYPOTHETICAL_EXIT"
    assert position.state is PaperPositionState.OPEN and position.version == 0
    with sessions() as session:
        rows = tuple(session.scalars(select(ScalpingStalePositionShadowRecord)))
        persisted_positions = session.scalar(text("SELECT count(*) FROM paper_positions"))
        persisted_commands = session.scalar(text(
            "SELECT count(*) FROM paper_execution_commands"
        ))
        persisted_accounting_events = session.scalar(text(
            "SELECT count(*) FROM paper_accounting_events"
        ))
    assert len(rows) == 2 and persisted_positions == 1
    assert persisted_commands == 0 and persisted_accounting_events == 0
    assert rows[-1].shadow_exit_reason == "TIME_STOP_SHADOW_HARD_LIMIT"
    assert costs.real_order_calls == 0
    assert Path(tmp_path / "stale-position-shadow.json").exists()
    engine.dispose()
