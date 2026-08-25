from __future__ import annotations

from types import SimpleNamespace

from app.engine_analysis.analysis_snapshot import AnalysisSnapshot
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.engine_setup.setup_candidate import SetupCandidate
from app.engine_setup.setup_diagnostics import SetupDiagnostics
from app.engine_setup.causal_planning_context import setup_causal_context
from app.engine_setup.setup_detector import SetupDetector
from app.engine_strategy.strategy_filter import StrategyFilter


BOUNDARY = 1_800_000_000_000


def test_directional_context_preserves_full_local_structural_15m_1h_hierarchy():
    source = {
        "causal_support_level": 99.0,
        "causal_resistance_level": 100.1,
        "causal_resistance_candidates": [
            {"price": 100.1, "source_type": "LOCAL_5M", "timeframe": "5m"},
            {"price": 101.0, "source_type": "LOCAL_5M", "timeframe": "5m"},
            {"price": 102.0, "source_type": "STRUCTURAL", "timeframe": "5m"},
        ],
        "higher_timeframe_target_candidates": [
            {"price": 103.0, "source_type": "15M", "timeframe": "15m", "side": "resistance"},
            {"price": 104.0, "source_type": "1H", "timeframe": "1h", "side": "resistance"},
            {"price": 95.0, "source_type": "15M", "timeframe": "15m", "side": "support"},
        ],
    }
    value = setup_causal_context(
        source, direction="BULLISH", setup_type="BREAKOUT_CONTINUATION"
    )
    assert [item["source_type"] for item in value["causal_target_candidates"]] == [
        "LOCAL_5M", "LOCAL_5M", "STRUCTURAL", "15M", "1H",
    ]
    assert value["causal_invalidation_level"] == 99.0
    assert value["causal_target_level"] == 100.1


def test_target_candidates_survive_strategy_context_parser():
    targets = [
        {"price": 100.2, "source_type": "LOCAL_5M", "timeframe": "5m", "validated": True},
        {"price": 102.0, "source_type": "STRUCTURAL", "timeframe": "5m", "validated": True},
    ]
    candidate = SetupCandidate(
        setup_id="setup:target:1", symbol="BTCUSDT", timeframe="5m",
        closed_until_ms=BOUNDARY, created_at_ms=BOUNDARY,
        source_analysis_snapshot_id="analysis:target:1", source_regime="UP",
        source_confidence=.8, source_action="NO_ACTION",
        source_entry_quality="ACCEPTABLE", status="SETUP_CANDIDATE",
        setup_type="BREAKOUT_CONTINUATION", direction_hint="BULLISH",
        confirmation_state="CONFIRMED_BY_ANALYSIS", setup_quality="ACCEPTABLE",
        quality_score=72.0,
        diagnostics=SetupDiagnostics(
            has_structural_trigger=True, has_directional_context=True,
            is_actionable_setup_candidate=True, semantic_bucket="CANDIDATE_STRUCTURE",
        ),
        context={
            "causal_target_candidates": targets,
            "causal_support_level": 99.0,
            "causal_resistance_level": 100.2,
        },
    )
    strategy = StrategyFilter().evaluate(candidate)
    assert strategy.context["causal_target_candidates"] == targets


def test_no_setup_persists_distance_and_real_near_miss_components():
    snapshot = AnalysisSnapshot.for_window(
        symbol="BTCUSDT", timeframe="5m", closed_until_ms=BOUNDARY,
        created_at_ms=BOUNDARY, market_data_health="OK", degraded=False,
        enough_data=True, regime="FLAT", confidence=.5, action="NO_ACTION",
        impulse_phase="NO_IMPULSE", entry_quality="WEAK",
        reason_codes=[], analysis_context={"atr_value": 1.0},
    )
    setup = SetupDetector().detect(snapshot)
    assert setup.status == "NO_SETUP"
    assert setup.diagnostics.distance_to_setup_condition is not None
    assert setup.diagnostics.missing_setup_conditions
    assert setup.diagnostics.liquidity_presence is False
    assert setup.diagnostics.volatility_suitability == "OBSERVED_NOT_THRESHOLD_CLASSIFIED"


def test_15m_pipeline_is_not_enriched_by_5m_target_context():
    runner = object.__new__(PipelineRunner)
    runner.config = SimpleNamespace(trade_profile_id="trade-15m-v1")
    analysis = SimpleNamespace(analysis_context={})
    runner._enrich_5m_target_context(analysis, {})
    assert analysis.analysis_context == {}


def test_5m_pipeline_enrichment_uses_only_closed_15m_and_1h_levels(monkeypatch):
    runner = object.__new__(PipelineRunner)
    runner.config = SimpleNamespace(trade_profile_id="trade-5m-v1")
    runner.runtime_parameters = SimpleNamespace(
        regime_lookback_candles=64, analysis_decision_candles=24,
        confirmation_window_candles=3, atr_lookback_candles=14,
        impulse_lookback_candles=48, structure_lookback_candles=48,
        volume_baseline_candles=40, breakout_volume_baseline_candles=20,
    )
    analysis = SimpleNamespace(analysis_context={}, closed_until_ms=BOUNDARY)
    snapshots = {
        "15m": SimpleNamespace(symbol="BTCUSDT"),
        "1h": SimpleNamespace(symbol="BTCUSDT"),
    }
    monkeypatch.setattr(
        "app.engine_orchestrator.pipeline_runner.MarketDataAdapter.adapt",
        lambda _self, snapshot: tuple(range(64)),
    )

    def output(_symbol, timeframe, _candles, *, config):
        return SimpleNamespace(json_payload={"analysis_context": {
            "technical_indicators": {"atr_14": 2.0},
            "causal_support_candidates": [{
                "price": 99.0, "source_type": timeframe.upper(),
                "timeframe": timeframe, "validated": True,
            }],
            "causal_resistance_candidates": [{
                "price": 101.0, "source_type": timeframe.upper(),
                "timeframe": timeframe, "validated": True,
            }],
        }})

    monkeypatch.setattr("app.engine_orchestrator.pipeline_runner.run_engine_analysis", output)
    runner._enrich_5m_target_context(analysis, snapshots)
    values = analysis.analysis_context["higher_timeframe_target_candidates"]
    assert len(values) == 4
    assert {item["timeframe"] for item in values} == {"15m", "1h"}
    assert all(item["known_at_ms"] == BOUNDARY for item in values)


def test_replay_script_is_read_only_and_never_inspects_environment():
    source = open("scripts/replay_5m_causal_target_hierarchy.py", encoding="utf-8").read()
    upper = source.upper()
    assert "DOCKER" in upper and "PSQL" in upper
    assert "CONTAINER INSPECT" not in upper
    assert ".CONFIG.ENV" not in upper
    assert all(token not in upper for token in ("UPDATE ", "DELETE ", "INSERT ", "ALTER "))
    assert "CLOSE_TIME_MS <" in upper
    assert "FUTURE_DATA_USED_IN_DECISION" in upper
    assert "ENTRY +" not in upper and "ATR SYNTHETIC TARGET" not in upper
