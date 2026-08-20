from __future__ import annotations

import os
import threading
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker

from app.engine_market_data.candle import Candle
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon
from app.engine_orchestrator.freshness_gate import FreshnessClassification
from app.engine_orchestrator.orchestrator_models import (
    OnlinePipelineResultRow,
    OnlinePipelineRun,
)
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import PipelineResultStore
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_orchestrator.profile_owner import (
    OwnerAlreadyActiveError,
    PostgresProfileOwner,
    ProfileOwnershipLostError,
    advisory_lock_key,
)
from app.engine_orchestrator.runtime_parameters import (
    RUNTIME_PROFILE_PARAMETERS,
    RuntimeProfileParameters,
    resolve_runtime_parameters,
)
from app.engine_analysis.analysis_contract import AnalysisWindowConfig
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo, component, outputs


def profile_config(profile_id: str) -> OrchestratorConfig:
    timeframe = "5m" if profile_id == "trade-5m-v1" else "15m"
    return OrchestratorConfig(
        symbols=("BTCUSDT",),
        trade_profile_id=profile_id,
        primary_timeframe=timeframe,
        required_timeframes=(timeframe,),
        minimum_windows={timeframe: 1},
    )


def profiled_runner(profile_id: str) -> PipelineRunner:
    analysis, setup, strategy, risk, paper = outputs(
        setup_status="SETUP_CANDIDATE",
        strategy_status="ALLOW_RESEARCH_TRADE_PLAN",
        risk_status="RISK_PRE_APPROVED_RESEARCH",
    )
    return PipelineRunner(
        profile_config(profile_id), CandleRepo(),
        analysis_runner=component(analysis), setup_runner=component(setup),
        strategy_runner=component(strategy), risk_runner=component(risk),
        paper_runner=component(paper),
    )


def test_parameter_resolution_is_explicit_immutable_and_has_no_fallback():
    fifteen = resolve_runtime_parameters("trade-15m-v1")
    five = resolve_runtime_parameters("trade-5m-v1")
    assert fifteen.parameter_set_id != five.parameter_set_id
    assert fifteen.profile_id == "trade-15m-v1"
    assert five.profile_id == "trade-5m-v1"
    assert five.atr_lookback_candles == 24
    assert five.impulse_lookback_candles == 12
    assert five.structure_lookback_candles == 48
    assert five.confirmation_window_candles == 3
    assert five.volume_baseline_candles == 36
    assert five.regime_lookback_candles == 72
    assert five.minimum_planned_rr == 1.5
    assert five.paper_command_creation_enabled is False
    assert five.position_opening_enabled is False
    with pytest.raises(FrozenInstanceError):
        five.atr_lookback_candles = 14  # type: ignore[misc]
    with pytest.raises(TypeError):
        RUNTIME_PROFILE_PARAMETERS["trade-5m-v1"] = fifteen  # type: ignore[index]
    with pytest.raises(ValueError, match="missing"):
        resolve_runtime_parameters("trade-5m-v1", registry={})
    with pytest.raises(ValueError):
        RuntimeProfileParameters(
            **{
                **{name: getattr(five, name) for name in five.__dataclass_fields__},
                "analysis_history_candles": 0,
            }
        )


def test_same_input_consumes_distinct_immutable_parameter_identities():
    fifteen = profiled_runner("trade-15m-v1").run("BTCUSDT", BOUNDARY)
    five = profiled_runner("trade-5m-v1").run("BTCUSDT", BOUNDARY)
    assert fifteen.runtime_parameter_set_id == resolve_runtime_parameters(
        "trade-15m-v1"
    ).parameter_set_id
    assert five.runtime_parameter_set_id == resolve_runtime_parameters(
        "trade-5m-v1"
    ).parameter_set_id
    assert fifteen.runtime_parameter_set_id != five.runtime_parameter_set_id
    assert fifteen.analysis_payload["runtime_parameter_set_id"] == fifteen.runtime_parameter_set_id
    for payload in (
        five.analysis_payload,
        five.setup_payload,
        five.strategy_payload,
        five.risk_payload,
        five.paper_payload,
    ):
        assert payload["runtime_parameter_set_id"] == five.runtime_parameter_set_id
    assert five.paper_payload["validity_policy"]["valid_until_ms"] == BOUNDARY + 300_000
    assert five.paper_payload["validity_policy"]["validity_boundaries"] == 1
    assert five.paper_payload["causal_levels"]["minimum_planned_rr"] == 1.5
    assert five.paper_payload["cost_efficiency_diagnostic"]["safety_margin_bps"] == 3.0
    assert five.paper_status == "SHADOW_SEARCH"
    assert five.safety_counters.has_violation is False


def test_default_5m_components_receive_one_authoritative_object_stage_by_stage():
    runner = PipelineRunner(profile_config("trade-5m-v1"), CandleRepo())
    parameters = runner.runtime_parameters
    analysis = runner.analysis_runner.config
    assert analysis.runtime_parameter_set_id == parameters.parameter_set_id
    assert (
        analysis.atr_lookback_candles,
        analysis.impulse_lookback_candles,
        analysis.structure_lookback_candles,
        analysis.confirmation_window_candles,
        analysis.volume_baseline_candles,
        analysis.regime_lookback_candles,
    ) == (24, 12, 48, 3, 36, 72)
    assert runner.setup_runner.runtime_parameters is parameters
    assert runner.setup_runner.detector.runtime_parameters is parameters
    assert runner.strategy_runner.runtime_parameters is parameters
    assert runner.strategy_runner.strategy_filter.runtime_parameters is parameters
    assert runner.risk_runner.runtime_parameters is parameters
    assert runner.risk_runner.policy.runtime_parameters is parameters
    assert runner.strategy_runner.strategy_filter.config.minimum_allowed_quality == "ACCEPTABLE"
    assert runner.risk_runner.policy.config.minimum_strategy_score == 65.0


def test_15m_effective_parameters_preserve_pre_remediation_engine_defaults():
    runner = PipelineRunner(profile_config("trade-15m-v1"), CandleRepo())
    analysis = runner.analysis_runner.config
    defaults = AnalysisWindowConfig()
    assert analysis.atr_lookback_candles == defaults.atr_lookback_candles == 14
    assert analysis.impulse_lookback_candles == defaults.impulse_lookback_candles == 96
    assert analysis.structure_lookback_candles == defaults.structure_lookback_candles == 96
    assert analysis.analysis_decision_candles == defaults.decision_candles == 24
    assert analysis.confirmation_window_candles == defaults.confirmation_candles == 3
    assert analysis.volume_baseline_candles == defaults.volume_baseline_candles == 93
    assert analysis.breakout_volume_baseline_candles == (
        defaults.breakout_volume_baseline_candles
    ) == 20
    assert analysis.regime_lookback_candles == defaults.context_candles == 96
    assert runner.strategy_runner.strategy_filter.config.minimum_allowed_quality == "ACCEPTABLE"
    assert runner.risk_runner.policy.config.policy_version == "ENGINE_RISK_01_RESEARCH_POLICY_V1"
    assert runner.risk_runner.policy.config.minimum_strategy_score == 65.0


def test_5m_startup_order_validates_then_acquires_before_daemon_loop():
    source = Path("scripts/engine_orchestrator_online_pipeline.py").read_text(encoding="utf-8")
    assert source.index("runtime_parameters = config.runtime_parameters") < source.index(
        "validate_5m_schema_capabilities(sessions)"
    ) < source.index("owner.acquire()") < source.index("daemon.run(")


def test_real_5m_stage_chain_consumes_parameters_and_cannot_reach_paper():
    class DeterministicCandles:
        def get_candles(self, symbol, timeframe, *, end_time_ms, limit):
            assert timeframe == "5m" and limit == 288
            duration = 300_000
            first = end_time_ms - (limit - 1) * duration
            rows = []
            for index in range(limit):
                opened = first + index * duration
                price = 100.0 + index * 0.02
                rows.append(Candle(
                    symbol=symbol, timeframe=timeframe,
                    open_time_ms=opened, close_time_ms=opened + duration - 1,
                    open=price, high=price + 0.4, low=price - 0.3,
                    close=price + 0.1, volume=100 + index,
                    is_closed=True, source="isolated-fixture",
                ))
            return rows

    config = profile_config("trade-5m-v1")
    config = OrchestratorConfig(
        symbols=config.symbols, trade_profile_id=config.trade_profile_id,
        primary_timeframe=config.primary_timeframe,
        required_timeframes=config.required_timeframes,
        minimum_windows={"5m": 288},
    )
    runner = PipelineRunner(config, DeterministicCandles())
    result = runner.run("BTCUSDT", BOUNDARY)
    expected = runner.runtime_parameters.parameter_set_id
    assert result.status == "COMPLETED"
    assert result.error_code is None
    assert result.runtime_parameter_set_id == expected
    assert result.analysis_payload["analysis_context"]["runtime_parameter_set_id"] == expected
    assert result.analysis_payload["analysis_context"]["analysis_runtime_parameters"][
        "atr_lookback_candles"
    ] == 24
    assert result.setup_payload["context"]["runtime_parameter_set_id"] == expected
    assert result.strategy_payload["context"]["runtime_parameter_set_id"] == expected
    assert result.risk_payload["risk_context"]["runtime_parameter_set_id"] == expected
    assert result.paper_payload["runtime_parameter_set_id"] == expected
    assert result.paper_payload["paper_command_creation_enabled"] is False
    assert result.paper_payload["position_opening_enabled"] is False
    assert result.safety_counters.has_violation is False


class AcceptingOwner:
    def assert_active(self, _session):
        return None


def test_5m_run_creation_and_progression_fail_closed_without_owner():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    store = PipelineResultStore(sessions)
    with pytest.raises(ProfileOwnershipLostError):
        store.reserve(
            "BTCUSDT", "5m", BOUNDARY, daemon_instance_id="ownerless",
            trigger_source="isolated", trade_profile_id="trade-5m-v1",
        )
    assert store.count(trade_profile_id="trade-5m-v1") == 0


def test_5m_retryable_freshness_is_deferred_before_authoritative_run_creation(tmp_path):
    """A legacy 15m retry scanner must never see a claimable 5m WAITING row."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    store = PipelineResultStore(sessions, owner_guard=AcceptingOwner())

    class Detector:
        def get_unprocessed_closed_windows(self, _symbol):
            return [SimpleNamespace(timeframe="5m", closed_until_ms=BOUNDARY)]

    class WaitingGate:
        def check(self, *_args, **_kwargs):
            return SimpleNamespace(
                status="BOUNDARY_NOT_READY",
                classification=FreshnessClassification.WAITING_RETRYABLE.value,
                reasons=("1h:BEHIND",),
            )

    daemon = OrchestratorDaemon(
        OrchestratorConfig(
            symbols=("BTCUSDT",), trade_profile_id="trade-5m-v1",
            primary_timeframe="5m", required_timeframes=("5m",),
            minimum_windows={"5m": 1},
            health_report_path=tmp_path / "health-5m.json",
        ),
        Detector(), WaitingGate(), object(), store,
    )
    observations = daemon.run_cycle()
    assert observations == [{
        "symbol": "BTCUSDT", "timeframe": "5m",
        "closed_until_ms": BOUNDARY,
        "freshness_status": "BOUNDARY_NOT_READY",
        "freshness_classification": FreshnessClassification.WAITING_RETRYABLE.value,
        "freshness_reasons": ["1h:BEHIND"],
        "pipeline_status": "DEFERRED_BEFORE_RESERVATION",
    }]
    assert store.count(trade_profile_id="trade-5m-v1") == 0


@pytest.fixture
def owner_postgres():
    raw = os.environ.get("ORCHESTRATOR_OWNER_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("ORCHESTRATOR_OWNER_TEST_DATABASE_URL is not configured")
    engine = create_engine(raw, hide_parameters=True, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        pytest.fail("owner acceptance requires isolated PostgreSQL")
    OnlinePipelineRun.__table__.create(engine, checkfirst=True)
    OnlinePipelineResultRow.__table__.create(engine, checkfirst=True)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as session:
        session.execute(delete(OnlinePipelineResultRow))
        session.execute(delete(OnlinePipelineRun))
        session.commit()
    yield sessions
    engine.dispose()


def test_postgres_owner_lifecycle_second_denial_stale_fencing_and_takeover(owner_postgres):
    owner_a = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
    owner_b_denied = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
    owner_a.acquire()
    assert owner_a.owner_instance_id != owner_b_denied.owner_instance_id
    status = owner_a.status()
    assert status.owner_state == "ACQUIRED"
    assert status.heartbeat_model == "LIVE_DEDICATED_DB_SESSION"
    assert status.expiry_model == "SESSION_DEATH_RELEASES_LOCK"
    owner_a.assert_active()
    assert owner_a.session.in_transaction() is False
    with pytest.raises(OwnerAlreadyActiveError, match="OWNER_ALREADY_ACTIVE"):
        owner_b_denied.acquire()
    with owner_postgres() as session:
        assert session.scalar(select(OnlinePipelineRun).where(
            OnlinePipelineRun.trade_profile_id == "trade-5m-v1"
        )) is None
    store_a = PipelineResultStore(owner_a.session, owner_guard=owner_a)
    run_id = store_a.reserve(
        "BTCUSDT", "5m", BOUNDARY, daemon_instance_id=owner_a.owner_instance_id,
        trigger_source="isolated", trade_profile_id="trade-5m-v1",
    )
    assert run_id is not None
    owner_a.invalidate_session_for_test()

    owner_b = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
    owner_b.acquire()
    owner_b.assert_active()
    with pytest.raises(ProfileOwnershipLostError):
        store_a.reserve(
            "ETHUSDT", "5m", BOUNDARY, daemon_instance_id=owner_a.owner_instance_id,
            trigger_source="stale", trade_profile_id="trade-5m-v1",
        )
    store_b = PipelineResultStore(
        owner_b.session, owner_guard=owner_b, stale_run_after_seconds=1,
        clock=lambda: datetime.now(timezone.utc) + timedelta(seconds=5),
    )
    claimed = store_b.claim_due_waiting(
        daemon_instance_id=owner_b.owner_instance_id,
        trade_profile_id="trade-5m-v1", limit=10,
    )
    assert [item.run_id for item in claimed] == [run_id]
    assert store_b.reserve(
        "BTCUSDT", "5m", BOUNDARY, daemon_instance_id=owner_b.owner_instance_id,
        trigger_source="duplicate", trade_profile_id="trade-5m-v1",
    ) is None
    owner_b.close()


def test_postgres_crash_windows_are_fenced_and_idempotent(owner_postgres):
    parameters = resolve_runtime_parameters("trade-5m-v1")

    # Crash after acquisition: session death releases without any run mutation.
    acquired = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
    acquired.acquire()
    acquired.invalidate_session_for_test()
    takeover = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
    takeover.acquire()
    takeover.close()

    # Crash after run creation / before authoritative progression.
    owner_a = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
    owner_a.acquire()
    store_a = PipelineResultStore(owner_a.session, owner_guard=owner_a)
    run_id = store_a.reserve(
        "ETHUSDT", "5m", BOUNDARY, daemon_instance_id=owner_a.owner_instance_id,
        trigger_source="crash-after-run", trade_profile_id="trade-5m-v1",
    )
    claim = store_a.get_claim(run_id)
    owner_a.invalidate_session_for_test()
    owner_b = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
    owner_b.acquire()
    store_b = PipelineResultStore(
        owner_b.session, owner_guard=owner_b, stale_run_after_seconds=1,
        clock=lambda: datetime.now(timezone.utc) + timedelta(seconds=5),
    )
    recovered = store_b.claim_due_waiting(
        daemon_instance_id=owner_b.owner_instance_id,
        trade_profile_id="trade-5m-v1", limit=10,
    )
    assert [item.run_id for item in recovered] == [claim.run_id]
    with pytest.raises(ProfileOwnershipLostError):
        store_a.mark_running(
            claim, daemon_instance_id=owner_a.owner_instance_id,
            checked_at=datetime.now(timezone.utc), payload={},
        )
    recovered_claim = recovered[0]
    assert store_b.mark_running(
        recovered_claim, daemon_instance_id=owner_b.owner_instance_id,
        checked_at=datetime.now(timezone.utc), payload={},
    )
    result = PipelineResult(
        "ETHUSDT", "5m", BOUNDARY, trade_profile_id="trade-5m-v1",
        runtime_parameter_set_id=parameters.parameter_set_id,
        paper_status="SHADOW_SEARCH",
        paper_payload={
            "runtime_parameter_set_id": parameters.parameter_set_id,
            "paper_command_creation_enabled": False,
            "position_opening_enabled": False,
        },
    )
    assert store_b.finish(run_id, result, freshness_status="READY")
    assert store_b.finish(run_id, result, freshness_status="READY") is False
    assert store_b.reserve(
        "ETHUSDT", "5m", BOUNDARY, daemon_instance_id=owner_b.owner_instance_id,
        trigger_source="duplicate-after-result", trade_profile_id="trade-5m-v1",
    ) is None
    owner_b.invalidate_session_for_test()

    # Crash after result/cursor completion: takeover observes a durable terminal
    # prefix and cannot repeat the completed authoritative boundary.
    owner_c = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
    owner_c.acquire()
    store_c = PipelineResultStore(
        owner_c.session, owner_guard=owner_c, stale_run_after_seconds=1,
        clock=lambda: datetime.now(timezone.utc) + timedelta(seconds=10),
    )
    assert store_c.claim_due_waiting(
        daemon_instance_id=owner_c.owner_instance_id,
        trade_profile_id="trade-5m-v1", limit=10,
    ) == []
    assert store_c.reserve(
        "ETHUSDT", "5m", BOUNDARY, daemon_instance_id=owner_c.owner_instance_id,
        trigger_source="post-crash-duplicate", trade_profile_id="trade-5m-v1",
    ) is None
    with pytest.raises(ValueError, match="parameter identity"):
        bad = PipelineResult(
            "ETHUSDT", "5m", BOUNDARY, trade_profile_id="trade-5m-v1",
            runtime_parameter_set_id="trade-5m-v1-runtime-v1-invalid",
        )
        store_c.finish(run_id, bad, freshness_status="READY")
    owner_c.close()


def test_postgres_high_contention_has_exactly_one_owner(owner_postgres):
    attempts = 4
    barrier = threading.Barrier(attempts)
    winner_release = threading.Event()
    results: list[str] = []
    lock = threading.Lock()

    def contender() -> None:
        owner = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
        barrier.wait()
        try:
            owner.acquire()
        except OwnerAlreadyActiveError:
            with lock:
                results.append("DENIED")
            return
        with lock:
            results.append("WINNER")
        winner_release.wait(timeout=10)
        owner.close()

    threads = [threading.Thread(target=contender) for _ in range(attempts)]
    for thread in threads:
        thread.start()
    while True:
        with lock:
            if len(results) == attempts:
                break
        winner_release.wait(timeout=0.01)
    winner_release.set()
    for thread in threads:
        thread.join(timeout=10)
    assert results.count("WINNER") == 1
    assert results.count("DENIED") == attempts - 1


def test_5m_owner_key_is_profile_specific_and_does_not_block_15m(owner_postgres):
    assert advisory_lock_key("trade-5m-v1") != advisory_lock_key("trade-15m-v1")
    owner = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
    owner.acquire()
    store_15m = PipelineResultStore(owner_postgres)
    run_15m = store_15m.reserve(
        "BTCUSDT", "15m", BOUNDARY, daemon_instance_id="15m-unchanged",
        trigger_source="isolated",
    )
    store_5m = PipelineResultStore(owner.session, owner_guard=owner)
    run_5m = store_5m.reserve(
        "BTCUSDT", "5m", BOUNDARY, daemon_instance_id=owner.owner_instance_id,
        trigger_source="isolated", trade_profile_id="trade-5m-v1",
    )
    assert run_15m and run_5m and run_15m != run_5m
    with owner_postgres() as session:
        rows = list(session.scalars(select(OnlinePipelineRun)))
        assert {row.trade_profile_id for row in rows} == {"trade-15m-v1", "trade-5m-v1"}
    owner.close()


def test_isolated_shared_boundary_exact10_profiles_are_distinct(owner_postgres):
    symbols = PREPARED_NEXT_TRADING_UNIVERSE.symbols
    assert len(symbols) == 10
    owner = PostgresProfileOwner(owner_postgres, "trade-5m-v1")
    owner.acquire()
    store_15m = PipelineResultStore(owner_postgres)
    store_5m = PipelineResultStore(owner.session, owner_guard=owner)
    runs_15m = {
        store_15m.reserve(
            symbol, "15m", BOUNDARY, daemon_instance_id="15m-exact10",
            trigger_source="isolated",
        )
        for symbol in symbols
    }
    runs_5m = {
        store_5m.reserve(
            symbol, "5m", BOUNDARY, daemon_instance_id=owner.owner_instance_id,
            trigger_source="isolated", trade_profile_id="trade-5m-v1",
        )
        for symbol in symbols
    }
    assert None not in runs_15m and None not in runs_5m
    assert len(runs_15m) == len(runs_5m) == 10
    assert runs_15m.isdisjoint(runs_5m)
    with owner_postgres() as session:
        rows = list(session.scalars(select(OnlinePipelineRun)))
        assert sum(row.trade_profile_id == "trade-15m-v1" for row in rows) == 10
        assert sum(row.trade_profile_id == "trade-5m-v1" for row in rows) == 10
        cursor_ids = {
            (row.trade_profile_id, row.symbol, row.primary_timeframe, row.closed_until_ms)
            for row in rows
        }
        assert len(cursor_ids) == 20
    owner.close()
