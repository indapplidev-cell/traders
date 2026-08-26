from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.engine_orchestrator.closed_window_detector import ClosedWindowDetector
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_orchestrator.parallel_profiles import ParallelTradeProfileCoordinator
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_orchestrator.trade_profile import (
    DEFAULT_TRADE_PROFILE_ID,
    TRADE_15M_PROFILE,
    TRADE_5M_CONTEXT_MINIMUM_WINDOWS,
    TRADE_5M_PROFILE,
)
from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo, component, outputs


def five_minute_config() -> OrchestratorConfig:
    return OrchestratorConfig(
        symbols=("BTCUSDT",), trade_profile_id="trade-5m-v1", primary_timeframe="5m",
        required_timeframes=("5m", "15m", "1h", "4h"),
        minimum_windows={"5m": 1, "15m": 1, "1h": 1, "4h": 1},
    )


def test_profiles_are_explicit_and_15m_default_is_unchanged():
    config = OrchestratorConfig()
    assert config.trade_profile_id == DEFAULT_TRADE_PROFILE_ID
    assert config.primary_timeframe == "15m"
    assert TRADE_15M_PROFILE.minimum_planned_rr == TRADE_5M_PROFILE.minimum_planned_rr == 1.5
    assert TRADE_5M_PROFILE.analysis_history_candles != TRADE_15M_PROFILE.analysis_history_candles
    assert TRADE_5M_PROFILE.atr_lookback_candles != TRADE_15M_PROFILE.atr_lookback_candles
    assert TRADE_5M_PROFILE.mode == "PRODUCTION_SEARCH"
    assert TRADE_5M_PROFILE.paper_command_creation_enabled is True
    assert TRADE_5M_PROFILE.position_opening_enabled is True
    assert TRADE_5M_PROFILE.trade_profile_id == "trade-5m-v1"
    assert TRADE_5M_PROFILE.trade_mode == "SCALPING"
    assert TRADE_5M_PROFILE.display_i18n_key == "trading.profile.trade_5m.title"
    assert TRADE_5M_PROFILE.primary_timeframe == "5m"
    assert TRADE_5M_PROFILE.entry_timeframes == ("1m", "5m")
    assert TRADE_5M_PROFILE.context_timeframes == ("15m", "1h")
    assert dict(TRADE_5M_PROFILE.market_data_windows) == {
        "1m": 60, "5m": 120, "15m": 64, "1h": 50,
    }
    assert TRADE_5M_PROFILE.analysis_history_candles == 120
    assert TRADE_5M_PROFILE.book_depth_limit == 100
    assert TRADE_5M_PROFILE.microstructure_max_age_ms == 5_000
    assert dict(TRADE_5M_CONTEXT_MINIMUM_WINDOWS) == dict(
        TRADE_5M_PROFILE.market_data_windows
    )
    assert TRADE_15M_PROFILE.trade_mode == "TRADE_15M"


def test_reserve_only_classifies_the_profile_window_unique_constraint_as_duplicate():
    duplicate = IntegrityError(
        "insert", {},
        SimpleNamespace(diag=SimpleNamespace(
            constraint_name="uq_online_pipeline_profile_window"
        )),
    )
    contract_failure = IntegrityError(
        "insert", {},
        SimpleNamespace(diag=SimpleNamespace(
            constraint_name="ck_online_pipeline_trade_profile"
        )),
    )
    assert PipelineResultStore._is_duplicate_window_error(duplicate) is True
    assert PipelineResultStore._is_duplicate_window_error(contract_failure) is False


def test_closed_5m_detector_uses_profile_in_dedupe_identity():
    seen = []

    class Store:
        def has_window(self, symbol, timeframe, boundary, *, trade_profile_id):
            seen.append((trade_profile_id, symbol, timeframe, boundary))
            return False

    detector = ClosedWindowDetector(
        CandleRepo(), Store(), primary_timeframe="5m", trade_profile_id="trade-5m-v1"
    )
    windows = detector.get_unprocessed_closed_windows("BTCUSDT")
    assert len(windows) == 1
    assert seen[0][:3] == ("trade-5m-v1", "BTCUSDT", "5m")


def test_5m_production_runner_invokes_plan_stage_and_is_closed_only():
    analysis, setup, strategy, risk, paper = outputs(
        setup_status="SETUP_CANDIDATE",
        strategy_status="ALLOW_RESEARCH_TRADE_PLAN",
        risk_status="RISK_PRE_APPROVED_RESEARCH",
        paper_status="PAPER_PLAN_READY",
    )

    repository = CandleRepo()
    runner = PipelineRunner(
        five_minute_config(), repository,
        analysis_runner=component(analysis), setup_runner=component(setup),
        strategy_runner=component(strategy), risk_runner=component(risk),
        paper_runner=component(paper),
    )
    result = runner.run("BTCUSDT", BOUNDARY)
    assert result.trade_profile_id == "trade-5m-v1"
    assert result.trigger_timeframe == "5m"
    assert result.profile_mode == "PRODUCTION_SEARCH"
    assert result.paper_status == "PAPER_PLAN_READY"
    assert result.paper_payload["paper_status"] == "PAPER_PLAN_READY"
    assert result.paper_payload["runtime_parameter_set_id"] == result.runtime_parameter_set_id
    assert all(call[2]["end_time_ms"] < BOUNDARY for call in repository.calls)


def test_profile_cursor_and_noneligible_materialization_are_isolated():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    now = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
    class IsolatedOwner:
        def assert_active(self, _session):
            return None

    store = PipelineResultStore(sessions, clock=lambda: now, owner_guard=IsolatedOwner())
    fifteen_id = store.reserve(
        "BTCUSDT", "15m", BOUNDARY, daemon_instance_id="15m", trigger_source="test"
    )
    five_id = store.reserve(
        "BTCUSDT", "5m", BOUNDARY, daemon_instance_id="5m", trigger_source="test",
        trade_profile_id="trade-5m-v1",
    )
    assert fifteen_id and five_id and fifteen_id != five_id
    assert store.has_window("BTCUSDT", "15m", BOUNDARY)
    assert store.has_window("BTCUSDT", "5m", BOUNDARY, trade_profile_id="trade-5m-v1")
    claim = store.get_claim(five_id)
    assert claim.trade_profile_id == "trade-5m-v1"
    assert store.mark_running(claim, daemon_instance_id="5m", checked_at=now, payload={})
    result = PipelineResult(
        "BTCUSDT", "5m", BOUNDARY, trade_profile_id="trade-5m-v1",
        runtime_parameter_set_id=resolve_runtime_parameters("trade-5m-v1").parameter_set_id,
        paper_status="NO_PLAN", paper_payload={},
    )
    assert store.finish(five_id, result, freshness_status="READY")
    with sessions() as session:
        five = session.scalar(select(OnlinePipelineRun).where(OnlinePipelineRun.run_id == five_id))
        fifteen = session.scalar(select(OnlinePipelineRun).where(OnlinePipelineRun.run_id == fifteen_id))
        assert five.status == "COMPLETED"
        assert fifteen.status == "CHECKING_FRESHNESS"
        assert five.is_executable is False and five.order_approved is False


def test_deterministic_5m_fault_is_contained_and_15m_completes():
    calls = []

    class Daemon:
        def __init__(self, name, fails=False):
            self.name, self.fails = name, fails

        def run_cycle(self):
            calls.append(self.name)
            if self.fails:
                raise RuntimeError("injected-5m-failure")
            return [SimpleNamespace(symbol="BTCUSDT")]

    result = ParallelTradeProfileCoordinator({
        "trade-15m-v1": Daemon("15m"),
        "trade-5m-v1": Daemon("5m", fails=True),
    }).run_cycle()
    assert set(calls) == {"15m", "5m"}
    assert result["trade-15m-v1"].healthy is True
    assert result["trade-15m-v1"].batch_size == 1
    assert result["trade-5m-v1"].healthy is False
    assert "injected-5m-failure" in result["trade-5m-v1"].error_code
