from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.analytics.strategy_performance import StrategyPerformanceService
from app.db.models import RunnerSession, RuntimeTick, TradeDecisionRecord, RunnerSessionMetric


def test_get_session_performance_counts(sqlite_session) -> None:
    now = datetime.now(UTC)
    runner_session = RunnerSession(
        strategy_name="simple_trend",
        strategy_version="1.0",
        symbol="BTCUSDT",
        interval="15m",
        status="STOPPED",
        started_at=now,
        stopped_at=now,
        ticks_requested=3,
        ticks_completed=2,
        last_error=None,
    )
    sqlite_session.add(runner_session)
    sqlite_session.flush()

    decision1 = TradeDecisionRecord(
        symbol="BTCUSDT",
        interval="15m",
        strategy_name="simple_trend",
        strategy_version="1.0",
        confidence=Decimal("0.75"),
        strategy_decision="BUY",
        strategy_reason="test",
        final_decision="BUY",
        final_reason="executed",
        regime="BULL",
        price=Decimal("100"),
        risk_approved=True,
        risk_reason="",
        execution_action="BUY",
        execution_message="",
        created_at=now,
    )
    decision2 = TradeDecisionRecord(
        symbol="BTCUSDT",
        interval="15m",
        strategy_name="simple_trend",
        strategy_version="1.0",
        confidence=Decimal("0.55"),
        strategy_decision="SELL",
        strategy_reason="test",
        final_decision="HOLD",
        final_reason="risk blocked",
        regime="BEAR",
        price=Decimal("105"),
        risk_approved=False,
        risk_reason="risk blocked",
        execution_action="SKIPPED",
        execution_message="",
        created_at=now,
    )
    sqlite_session.add_all([decision1, decision2])
    sqlite_session.flush()

    tick1 = RuntimeTick(
        runner_session_id=runner_session.id,
        tick_number=1,
        symbol="BTCUSDT",
        interval="15m",
        strategy_action="BUY",
        final_action="BUY",
        risk_approved=True,
        risk_reason=None,
        execution_action="BUY",
        journal_id=decision1.id,
        market_regime="BULL",
        candles_used=10,
        started_at=now,
        finished_at=now,
        error=None,
    )
    tick2 = RuntimeTick(
        runner_session_id=runner_session.id,
        tick_number=2,
        symbol="BTCUSDT",
        interval="15m",
        strategy_action="SELL",
        final_action="HOLD",
        risk_approved=False,
        risk_reason="risk blocked",
        execution_action="SKIPPED",
        journal_id=decision2.id,
        market_regime="BEAR",
        candles_used=12,
        started_at=now,
        finished_at=now,
        error=None,
    )
    sqlite_session.add_all([tick1, tick2])
    sqlite_session.commit()

    report = StrategyPerformanceService().get_session_performance(runner_session.id)

    assert report.runtime_quality.ticks_requested == 3
    assert report.runtime_quality.ticks_completed == 2
    assert report.runtime_quality.audit_ticks_count == 2
    assert report.strategy_action_counts.buy == 1
    assert report.strategy_action_counts.sell == 1
    assert report.final_action_counts.buy == 1
    assert report.final_action_counts.hold == 1
    assert report.risk_metrics.approved_count == 1
    assert report.risk_metrics.rejected_count == 1
    assert report.risk_metrics.rejection_reasons.get("risk blocked") == 1
    assert report.execution_metrics.skipped_count == 1
    assert report.execution_metrics.buy_executed_count == 1
    assert report.market_regime_metrics.regimes["BULL"] == 1
    assert report.market_regime_metrics.regimes["BEAR"] == 1
    assert report.candles_used_min == 10
    assert report.candles_used_max == 12
    assert report.candles_used_average == 11
    assert report.journal_ids == [decision1.id, decision2.id]
    assert report.runtime_quality.error_ticks_count == 0


def test_get_session_performance_no_ticks_returns_zero_metrics(sqlite_session) -> None:
    now = datetime.now(UTC)
    runner_session = RunnerSession(
        strategy_name="simple_trend",
        strategy_version="1.0",
        symbol="BTCUSDT",
        interval="15m",
        status="STOPPED",
        started_at=now,
        stopped_at=now,
        ticks_requested=5,
        ticks_completed=0,
        last_error=None,
    )
    sqlite_session.add(runner_session)
    sqlite_session.commit()

    report = StrategyPerformanceService().get_session_performance(runner_session.id)

    assert report.runtime_quality.audit_ticks_count == 0
    assert report.risk_metrics.rejected_count == 0
    assert report.execution_metrics.execution_actions == {}
    assert report.confidence_metrics.count == 0
    assert report.errors == []


def test_get_session_performance_raises_for_missing_session(sqlite_session) -> None:
    try:
        StrategyPerformanceService().get_session_performance(999)
        assert False, "Expected ValueError for missing session"
    except ValueError as exc:
        assert "Runner session 999 not found" in str(exc)


def test_persist_session_metrics_updates_existing_record(sqlite_session) -> None:
    now = datetime.now(UTC)
    runner_session = RunnerSession(
        strategy_name="simple_trend",
        strategy_version="1.0",
        symbol="BTCUSDT",
        interval="15m",
        status="FAILED",
        started_at=now,
        stopped_at=now,
        ticks_requested=1,
        ticks_completed=0,
        last_error="error",
    )
    sqlite_session.add(runner_session)
    sqlite_session.commit()

    service = StrategyPerformanceService()
    metric_first = service.persist_session_metrics(runner_session.id, "BTCUSDT")
    metric_second = service.persist_session_metrics(runner_session.id, "BTCUSDT")

    assert metric_first.id == metric_second.id
    assert metric_first.runner_session_id == runner_session.id
    assert metric_second.data_quality in {"UNAVAILABLE", "PARTIAL", "COMPLETE"}

    metrics = sqlite_session.execute(
        select(RunnerSessionMetric).where(RunnerSessionMetric.runner_session_id == runner_session.id)
    ).scalars().all()
    assert len(metrics) == 1
