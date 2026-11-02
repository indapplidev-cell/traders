from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from traders_ml.parameter_sweep.full_pipeline import (
    CandidateMetrics,
    EndToEndTradeEvaluationV1,
    FullPipelineCalibrationRequestV1,
    FullPipelineCandidateV1,
    PipelineDecisionTraceV1,
    StageDecision,
    build_canary,
    default_registry,
    evaluate_gates,
    fingerprint,
    metrics_from_trades,
)


ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "config" / "research" / "full_pipeline_calibration_v1.json"


def test_request_and_registry_cover_complete_safe_chain():
    request = FullPipelineCalibrationRequestV1.model_validate_json(
        REQUEST.read_text(encoding="utf-8")
    )
    registry = default_registry()
    assert len(request.symbols) == 20
    assert request.direction == "LONG"
    assert request.live_allowed is False
    assert request.search.worker_count == 1
    names = {item.name for item in registry.parameters}
    assert {
        "analysis.altunina", "analysis.schwager", "analysis.nison",
        "strategy.entry_weights", "geometry.stop_max_bps",
        "economics.minimum_planned_rr", "risk.risk_per_trade_bps",
        "risk.max_open_positions", "lifecycle.entry_fill_window_seconds",
        "exit.weights", "costs.actual_commission", "safety.live_allowed",
    } <= names
    risk = next(item for item in registry.parameters if item.name == "risk.risk_per_trade_bps")
    assert max(risk.values) == 10
    assert risk.safety_critical is True
    immutable = {item.name for item in registry.parameters if item.immutable}
    assert "costs.actual_commission" in immutable
    assert "safety.accounting_identity" in immutable


def test_decision_trace_requires_chronological_first_failure():
    common = {
        "trace_id": "trace-1", "configuration_hash": "a" * 64,
        "dataset_hash": "b" * 64, "symbol": "BTCUSDT", "boundary_ms": 1,
    }
    trace = PipelineDecisionTraceV1(
        **common,
        decisions=(
            StageDecision(stage="ANALYSIS", passed=True, reason="PASS"),
            StageDecision(stage="STRUCTURAL_SETUP", passed=False, reason="NO_SETUP"),
        ),
        terminal_stage="STRUCTURAL_SETUP",
    )
    assert trace.future_bars_used is False
    with pytest.raises(ValidationError):
        PipelineDecisionTraceV1(
            **common,
            decisions=(
                StageDecision(stage="STRATEGY_ADMISSION", passed=True, reason="PASS"),
                StageDecision(stage="ANALYSIS", passed=True, reason="PASS"),
            ),
            terminal_stage="STRATEGY_ADMISSION",
        )


def trade(*, trade_id: str, symbol: str, day: int, net: float, gross: float, bps: float):
    costs = gross - net
    return EndToEndTradeEvaluationV1(
        trade_id=trade_id, configuration_hash="c" * 64, symbol=symbol,
        setup_family="BREAKOUT", regime="IMPULSE", entry_boundary_ms=day * 86_400_000,
        exit_boundary_ms=day * 86_400_000 + 60_000,
        entry_price=100, exit_price=101, quantity=1, gross_pnl=gross,
        fees=costs / 4, spread_cost=costs / 4, slippage_cost=costs / 4,
        reserve_cost=costs / 4, net_pnl=net, net_pnl_bps=bps,
        risk_r=net / 0.1, exit_reason="ANALYTICAL_EXIT",
    )


def test_accounting_identity_is_fail_closed():
    with pytest.raises(ValidationError):
        EndToEndTradeEvaluationV1(
            trade_id="bad", configuration_hash="c" * 64, symbol="BTCUSDT",
            setup_family="BREAKOUT", regime="IMPULSE", entry_boundary_ms=1,
            exit_boundary_ms=2, entry_price=100, exit_price=101, quantity=1,
            gross_pnl=1, fees=.1, spread_cost=.1, slippage_cost=.1,
            reserve_cost=.1, net_pnl=.9, net_pnl_bps=9, risk_r=1,
            exit_reason="TARGET",
        )


def test_metrics_and_gates_use_end_to_end_net_results():
    request = FullPipelineCalibrationRequestV1.model_validate_json(
        REQUEST.read_text(encoding="utf-8")
    )
    trades = [
        trade(trade_id=f"t{index}", symbol=f"S{index % 10}USDT", day=index % 10,
              net=1.0, gross=1.1, bps=10.0)
        for index in range(300)
    ]
    metrics = metrics_from_trades(
        trades, initial_equity=1000, baseline_max_drawdown_fraction=.05,
        profitable_walk_forward_folds=4, neighbor_stability_pass=True,
        stress_multiplier=request.gates.stress_cost_multiplier,
    )
    gates = evaluate_gates(metrics, request.gates)
    assert metrics.closed_trades == 300
    assert metrics.expectancy_bps == 10
    assert all(gates.values())


def test_canary_is_generated_only_for_eligible_verified_candidate(tmp_path):
    request = FullPipelineCalibrationRequestV1.model_validate_json(
        REQUEST.read_text(encoding="utf-8")
    )
    metrics = CandidateMetrics(
        closed_trades=300, independent_days=10, symbols=10, net_pnl=100,
        expectancy_bps=10, profit_factor=2, win_rate=.6,
        max_drawdown_fraction=.01, maximum_symbol_profit_share=.1,
        maximum_day_profit_share=.1, profitable_walk_forward_folds=4,
        stress_net_pnl=50, stress_profit_factor=1.5,
        baseline_max_drawdown_fraction=.02, neighbor_stability_pass=True,
    )
    gates = evaluate_gates(metrics, request.gates)
    parameters = {"strategy.minimum_score": 55}
    candidate = FullPipelineCandidateV1(
        candidate_id="candidate-1", request_hash=request.identity,
        dataset_hash="d" * 64, registry_hash=default_registry().identity,
        configuration_hash=fingerprint(parameters), seed=request.seed,
        parameters=parameters, metrics=metrics, gate_results=gates,
        status="ELIGIBLE",
    )
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(candidate.model_dump(mode="json")), encoding="utf-8")
    manifest = build_canary(path, tmp_path / "canary", "scalping-v2-set-2")
    assert manifest.activation_status == "READY_FOR_PAPER_CANARY"
    assert manifest.live_allowed is False


def test_ineligible_candidate_cannot_generate_canary(tmp_path):
    request = FullPipelineCalibrationRequestV1.model_validate_json(
        REQUEST.read_text(encoding="utf-8")
    )
    metrics = CandidateMetrics(
        closed_trades=1, independent_days=1, symbols=1, net_pnl=-1,
        expectancy_bps=-10, profit_factor=0, win_rate=0,
        max_drawdown_fraction=.01, maximum_symbol_profit_share=1,
        maximum_day_profit_share=1, profitable_walk_forward_folds=0,
        stress_net_pnl=-1, stress_profit_factor=0,
        baseline_max_drawdown_fraction=.02, neighbor_stability_pass=False,
    )
    gates = evaluate_gates(metrics, request.gates)
    parameters = {"strategy.minimum_score": 55}
    candidate = FullPipelineCandidateV1(
        candidate_id="rejected", request_hash=request.identity,
        dataset_hash="d" * 64, registry_hash=default_registry().identity,
        configuration_hash=fingerprint(parameters), seed=request.seed,
        parameters=parameters, metrics=metrics, gate_results=gates,
        status="NO_ELIGIBLE_CANDIDATE",
    )
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(candidate.model_dump(mode="json")), encoding="utf-8")
    with pytest.raises(ValueError, match="PAPER_CANARY_BLOCKED"):
        build_canary(path, tmp_path / "canary", "scalping-v2-set-2")
