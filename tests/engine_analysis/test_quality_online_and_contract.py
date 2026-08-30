from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace

import pytest

from app.engine_analysis import EngineAnalysisCandle, EngineAnalysisRegime, run_engine_analysis
from app.engine_analysis.analysis_snapshot import AnalysisSnapshot, AnalysisSnapshotStatus
from app.engine_analysis.analysis_snapshot_store import AnalysisSnapshotStore
from app.engine_analysis.contextual_diagnostics import ContextualDiagnosticInput, DiagnosticZone, diagnose_context
from app.engine_analysis.impulse_phase_diagnostics import ImpulseDiagnosticInput, diagnose_impulse_phase
from app.engine_analysis.market_data_adapter import MarketDataAdapter
from app.engine_analysis.market_structure_diagnostics import diagnose_market_structure
from app.engine_analysis.online_config import OnlineAnalysisConfig
from app.engine_analysis.online_runner import OnlineAnalysisRunner


def test_impulse_quality_diagnostics_are_causal_and_serializable(candle_factory):
    """Given finalized bars, when impulse quality is diagnosed, then output is causal JSON data."""
    candles = candle_factory("up", 32)
    payload = diagnose_impulse_phase(
        ImpulseDiagnosticInput(
            symbol="BTCUSDT",
            timeframe="15m",
            cutoff=candles[-1].timestamp,
            market_regime="UP",
            final_action="NO_ACTION",
            candles=[item.to_dict() for item in candles],
        )
    )
    assert payload["safety"]["decision_changed"] is False
    assert payload["safety"]["trade_signal_created"] is False
    assert payload["causal_audit"]["future_bars_used"] is False
    json.loads(json.dumps(payload))


def test_market_structure_diagnostics_report_observed_boundary(candle_factory):
    """Given a closed window, when structure diagnostics run, then last-observed boundary is explicit."""
    candles = candle_factory("range", 32)
    payload = diagnose_market_structure([item.to_dict() for item in candles], base_regime="FLAT")
    assert payload["causal_audit"]["last_observed_timestamp"] == candles[-1].timestamp
    assert payload["causal_audit"]["future_bars_used"] is False
    json.loads(json.dumps(payload))


def test_zone_and_conflict_diagnostics_remain_non_actionable():
    """Given zone/MTF conflict, when diagnosed, then evidence is serializable and creates no setup."""
    payload = diagnose_context(
        ContextualDiagnosticInput(
            symbol="BTCUSDT",
            timeframe="15m",
            as_of="2026-01-01T00:00:00Z",
            source_regime="UNKNOWN",
            source_confidence=0.3,
            last_close=100,
            atr=2,
            zones=(DiagnosticZone("RESISTANCE", 100, 101, "test"),),
            timeframe_regimes={"15m": "UP", "1h": "DOWN"},
            conflict_codes=("UNRESOLVED",),
        )
    )
    assert payload["safety"]["trade_signal_created"] is False
    assert payload["safety"]["setup_created"] is False
    json.loads(json.dumps(payload))


def test_online_adapter_propagates_identity_boundary_and_serialization(market_snapshot_factory):
    """Given a healthy DB-style snapshot, when run online, then identity and closed boundary propagate."""
    snapshot = market_snapshot_factory()
    pipeline_calls: list[tuple[str, str, int]] = []

    def pipeline(symbol, timeframe, candles):
        pipeline_calls.append((symbol, timeframe, len(candles)))
        return {"regime": "UP", "confidence": 0.8, "reason_codes": ["CURRENT_CONTRACT"]}

    runner = OnlineAnalysisRunner(
        OnlineAnalysisConfig(required_history_candles=4, max_snapshot_age_ms=0),
        MarketDataAdapter(),
        AnalysisSnapshotStore(),
        pipeline,
    )
    output = runner.analyze_market_data_snapshot(snapshot)
    assert pipeline_calls == [(snapshot.symbol, snapshot.timeframe, 4)]
    assert output.closed_until_ms == snapshot.closed_until_ms
    assert output.source_market_data_snapshot_id == snapshot.snapshot_id
    assert output.status == AnalysisSnapshotStatus.ANALYZED.value
    json.loads(json.dumps(output.__dict__ if hasattr(output, "__dict__") else {name: getattr(output, name) for name in output.__slots__}))


@pytest.mark.parametrize("health", ["DEGRADED", "ERROR", "UNKNOWN"])
def test_invalid_or_degraded_online_input_is_gated(market_snapshot_factory, health):
    """Given unhealthy market data, when online analysis runs, then no pipeline call is made."""
    snapshot = replace(market_snapshot_factory(), health_status=health)
    calls = 0

    def pipeline(*_args):
        nonlocal calls
        calls += 1
        return {}

    runner = OnlineAnalysisRunner(
        OnlineAnalysisConfig(required_history_candles=4, max_snapshot_age_ms=0),
        MarketDataAdapter(), AnalysisSnapshotStore(), pipeline,
    )
    output = runner.analyze_market_data_snapshot(snapshot)
    assert calls == 0
    assert output.status != AnalysisSnapshotStatus.ANALYZED.value


def test_public_models_are_frozen_and_json_round_trip(candle_factory):
    """Given a public result, when serialized, then JSON round-trip is stable and mutation is blocked."""
    candle = EngineAnalysisCandle("2026-01-01T00:00:00+00:00", 1, 2, 0.5, 1.5, 1)
    with pytest.raises(FrozenInstanceError):
        candle.close = 9  # type: ignore[misc]
    payload = run_engine_analysis("BTCUSDT", "15m", candle_factory("up")).to_dict()
    assert json.loads(json.dumps(payload)) == payload


def test_stable_public_imports_and_no_legacy_package():
    """Given the package boundary, when imported, then current enums resolve and legacy runtime does not."""
    assert {item.value for item in EngineAnalysisRegime} == {"UP", "DOWN", "FLAT", "UNKNOWN"}
    with pytest.raises(ModuleNotFoundError):
        __import__("app.market_reader.engine_trend")


def test_analysis_snapshot_missing_quality_is_not_actionable():
    """Given missing quality, when represented online, then the record remains analysis-only."""
    snapshot = AnalysisSnapshot.for_window(
        symbol="BTCUSDT", timeframe="15m", closed_until_ms=1, created_at_ms=2,
        market_data_health="OK", degraded=False, enough_data=True, regime="UNKNOWN",
        confidence=0.1, action="NO_ACTION", entry_quality=None,
    )
    assert snapshot.action == "NO_ACTION"
    assert snapshot.entry_quality is None
    assert snapshot.future_bars_used is False
