from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db.paper_models import PaperPlanExecutionOutcomeRecord
from app.engine_orchestrator.orchestrator_models import (
    OnlinePipelineResultRow,
    OnlinePipelineRun,
)
from app.engine_paper.plan_execution_outcome import PaperPlanExecutionOutcomeStore


BOUNDARY = 1_900_000_000_000
TEST_DATABASE = "traders_scalping_fix_test"


def _engine():
    url = os.getenv("SCALPING_FIX_TEST_DATABASE_URL")
    if not url:
        pytest.skip("isolated reconciliation PostgreSQL URL is not configured")
    if make_url(url).database != TEST_DATABASE:
        pytest.fail(f"task-owned {TEST_DATABASE} PostgreSQL is required")
    return create_engine(url, pool_size=4)


def test_concurrent_reconciliation_commits_one_terminal_projection():
    engine = _engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    run_id = "run:concurrent-pre-selector-terminal"
    started = datetime.fromtimestamp((BOUNDARY + 310_000) / 1000, timezone.utc)
    finished = datetime.fromtimestamp((BOUNDARY + 350_000) / 1000, timezone.utc)
    with factory() as session, session.begin():
        session.add(OnlinePipelineRun(
            run_id=run_id, trade_profile_id="trade-5m-v2",
            profile_mode="PRODUCTION_SEARCH", symbol="SOLUSDT",
            primary_timeframe="5m", closed_until_ms=BOUNDARY,
            closed_until_utc=datetime.fromtimestamp(BOUNDARY / 1000, timezone.utc),
            status="COMPLETED", started_at=started, finished_at=finished,
            duration_ms=40_000, trigger_source="postgres_closed_candle",
            daemon_instance_id="test-daemon", paper_status="PAPER_PLAN_READY",
            final_result="PAPER_PLAN_READY",
        ))
        session.flush()
        session.add(OnlinePipelineResultRow(
            run_id=run_id, trade_profile_id="trade-5m-v2",
            profile_mode="PRODUCTION_SEARCH", symbol="SOLUSDT",
            primary_timeframe="5m", closed_until_ms=BOUNDARY,
            market_data_payload_json={}, analysis_payload_json={},
            setup_payload_json={}, strategy_payload_json={}, risk_payload_json={},
            paper_payload_json={
                "paper_plan_id": "paper:concurrent-pre-selector-terminal",
                "created_at_ms": BOUNDARY + 350_000,
                "final_approval_generation": {
                    "status": "REJECTED",
                    "reason_code": "PAPER_SAFETY_SOURCE_STALE",
                },
            },
            module_reasons_json={}, module_warnings_json={},
            safety_counters_json={}, created_at=finished,
        ))

    observed = datetime.fromtimestamp((BOUNDARY + 400_000) / 1000, timezone.utc)

    def reconcile():
        return PaperPlanExecutionOutcomeStore(factory).reconcile_terminal_plans(
            symbols=("SOLUSDT",), universe_id="trading-universe-v3",
            control_generation=31, observed_at=observed,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(lambda _: reconcile(), range(2)))

    assert sum(value["projected"] for value in results) == 1
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(
            PaperPlanExecutionOutcomeRecord
        )) == 1
        row = session.get(PaperPlanExecutionOutcomeRecord, run_id)
        assert row.selected_winner is False and row.command_id is None
        assert row.final_approval_id is None and row.candidate_id is None
    engine.dispose()
