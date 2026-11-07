"""Causality and accounting invariants for the v3 research cache."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.config.trade_parameters import load_trade_parameters
from app.engine_analysis.analysis_snapshot import AnalysisSnapshot
from app.engine_market_data.candle import Candle
from traders_ml.parameter_sweep import full_pipeline_candidate_v3
from traders_ml.parameter_sweep.full_pipeline import fingerprint
from traders_ml.parameter_sweep.full_pipeline_candidate_v3 import _frozen_candles
from traders_ml.parameter_sweep.full_pipeline_v3 import (
    CausalBoundaryFeaturesV3,
    HistoricalCostLedgerV3,
    _compact_stage_payloads,
    _sha256,
    resolve_research_parameter_set_v3,
)


def test_costs_are_separate_and_reconcile() -> None:
    ledger = HistoricalCostLedgerV3.from_bps(
        boundary_ms=1000, provenance="MODELLED_CONSERVATIVE", evidence_ms=999,
        notional=1000, gross_pnl=5,
        entry_fee_bps=10, exit_fee_bps=10, spread_bps=3,
        entry_slippage_bps=2, exit_slippage_bps=4,
        depth_impact_bps=1, reserve_bps=3,
    )
    assert ledger.entry_fee == 1
    assert ledger.exit_fee == 1
    assert ledger.entry_slippage == pytest.approx(.2)
    assert ledger.exit_slippage == pytest.approx(.4)
    assert ledger.net_pnl == pytest.approx(1.7)
    assert ledger.gross_pnl - sum((ledger.entry_fee, ledger.exit_fee, ledger.spread,
        ledger.entry_slippage, ledger.exit_slippage, ledger.depth_impact,
        ledger.reserve)) == pytest.approx(ledger.net_pnl)


def test_compact_candidate_signal_receipt_and_resume(tmp_path, monkeypatch) -> None:
    root = tmp_path / "cache"
    partition = root / "symbols" / "BTCUSDT" / "1000"
    partition.mkdir(parents=True)
    (partition / "DONE.json").write_text(json.dumps({"sha256": "a" * 64,
                                                      "boundaries": 2}), encoding="utf-8")
    candidate_hash = resolve_research_parameter_set_v3(
        load_trade_parameters().resolve_scalping_v2_parameter_set(), {}).resolved_config_hash
    decisions = [SimpleNamespace(
        symbol="BTCUSDT", boundary_ms=1000 + index * 300_000,
        statuses={"paper_status": "NO_PLAN"}, first_rejection="NO_SETUP",
        decision_hash="b" * 64, analysis_parameter_hash=candidate_hash,
        paper={},
    ) for index in range(2)]
    monkeypatch.setattr(full_pipeline_candidate_v3, "native_candidate_decisions_v3",
                        lambda *args, **kwargs: iter(decisions))
    request = Path(__file__).resolve().parents[1] / "config/research/full_pipeline_calibration_v2.json"
    dataset = Path(__file__).resolve().parents[1] / "artifacts/full_pipeline_calibration/ragged_freeze_20261102_v1"
    output = tmp_path / "signals.jsonl"
    receipt = full_pipeline_candidate_v3.write_native_candidate_signals_v3(
        request, dataset, root, partition, {}, output)
    assert receipt["boundaries"] == 2
    assert receipt["holdout_evaluated"] is False
    assert len(output.read_text(encoding="utf-8").splitlines()) == 2
    assert full_pipeline_candidate_v3.write_native_candidate_signals_v3(
        request, dataset, root, partition, {}, output) == receipt
    output.with_suffix(".json").unlink()
    assert full_pipeline_candidate_v3.write_native_candidate_signals_v3(
        request, dataset, root, partition, {}, output) == receipt
    changed_receipt = {**receipt, "analysis_reuse_mode": "ENRICHED_BASELINE_ANALYSIS"}
    output.with_suffix(".json").write_text(json.dumps(changed_receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="RESUME_IDENTITY_MISMATCH"):
        full_pipeline_candidate_v3.write_native_candidate_signals_v3(
            request, dataset, root, partition, {}, output)


def test_future_cost_snapshot_is_rejected() -> None:
    with pytest.raises(ValidationError, match="FUTURE_COST_EVIDENCE"):
        HistoricalCostLedgerV3.from_bps(
            boundary_ms=1000, provenance="OBSERVED", evidence_ms=1001,
            notional=100, gross_pnl=1, entry_fee_bps=10, exit_fee_bps=10,
            spread_bps=1, entry_slippage_bps=1, exit_slippage_bps=1,
            depth_impact_bps=0, reserve_bps=3,
        )


def test_future_candle_ref_is_rejected() -> None:
    with pytest.raises(ValidationError, match="FUTURE_CANDLE_IN_FEATURE_CACHE"):
        CausalBoundaryFeaturesV3(
            symbol="BTCUSDT", segment_start_ms=1, boundary_ms=1000,
            dataset_hash="a" * 64, analysis_parameter_hash="b" * 64,
            candle_refs={"5m": {"close_time_ms": 1000}},
            market_data={}, analysis={}, setup={}, strategy={}, risk={}, paper={},
            statuses={}, feature_completeness={}, decision_hash="c" * 64,
        )


def test_research_candidate_is_native_and_does_not_change_baseline() -> None:
    baseline = load_trade_parameters().resolve_scalping_v2_parameter_set()
    old = baseline.parameters.signal.strategy_minimum_score
    candidate = resolve_research_parameter_set_v3(
        baseline, {"strategy_minimum_score": old + 1},
    )
    assert candidate.parameters.signal.strategy_minimum_score == old + 1
    assert baseline.parameters.signal.strategy_minimum_score == old
    assert candidate.resolved_config_hash != baseline.resolved_config_hash
    weights = baseline.parameters.signal.entry_score_weights.model_dump()
    weights["structure"] -= 1
    weights["context"] += 1
    weighted = resolve_research_parameter_set_v3(
        baseline, {"entry_score_weights": weights,
                   "analytical_exit_exit_threshold": 60},
    )
    assert weighted.parameters.signal.entry_score_weights.structure == weights["structure"]
    assert weighted.parameters.exit_policy.analytical_exit.exit_threshold == 60
    assert baseline.parameters.exit_policy.analytical_exit.exit_threshold != 60
    with pytest.raises(ValueError, match="UNSUPPORTED_NATIVE_PARAMETER"):
        resolve_research_parameter_set_v3(baseline, {"entry_slippage_bps": 0})


def test_enriched_analysis_reuse_is_limited_to_downstream_parameters() -> None:
    safe = full_pipeline_candidate_v3._analysis_reuse_safe_v3
    assert safe({"min_net_edge_bps": 8})
    assert safe({"atr_multiplier": 0.35, "analytical_exit_exit_threshold": 60})
    assert not safe({"entry_score_weights": {}})
    assert not safe({"min_net_edge_bps": 8, "strategy_minimum_score": 55})
    assert not safe({"unknown": 1})


def test_cached_analysis_requires_exact_boundary_and_is_consumed_once() -> None:
    snapshot = AnalysisSnapshot.for_window(
        symbol="BTCUSDT", timeframe="5m", closed_until_ms=300_000,
        created_at_ms=300_000, market_data_health="OK", degraded=False,
        enough_data=True, analysis_context={"causal": True},
    )
    source = CausalBoundaryFeaturesV3(
        symbol="BTCUSDT", segment_start_ms=1, boundary_ms=300_000,
        dataset_hash="a" * 64, analysis_parameter_hash="b" * 64,
        candle_refs={}, market_data={}, analysis=asdict(snapshot),
        setup={}, strategy={}, risk={}, paper={}, statuses={},
        feature_completeness={"analysis": True}, decision_hash="c" * 64,
    )
    cached = full_pipeline_candidate_v3._CachedAnalysisRunnerV3()
    cached.set_boundary(source)
    with pytest.raises(ValueError, match="INPUT_MISMATCH"):
        cached.analyze_market_data_snapshot(SimpleNamespace(
            symbol="BTCUSDT", timeframe="5m", closed_until_ms=600_000))
    assert cached.analyze_market_data_snapshot(SimpleNamespace(
        symbol="BTCUSDT", timeframe="5m", closed_until_ms=300_000)) == snapshot
    with pytest.raises(ValueError, match="INPUT_MISMATCH"):
        cached.analyze_market_data_snapshot(SimpleNamespace(
            symbol="BTCUSDT", timeframe="5m", closed_until_ms=300_000))


def test_compaction_preserves_unique_stage_evidence() -> None:
    payload = {
        "analysis": {"frozen_parameter_snapshot": {"large": "repeat"},
                     "analysis_context": {"technical_indicators": {"rsi": 52}}},
        "setup": {"frozen_parameter_snapshot": {"large": "repeat"},
                  "context": {"technical_indicators": {"rsi": 52}, "setup_type": "BREAKOUT"}},
        "strategy": {"frozen_parameter_snapshot": {"large": "repeat"}, "strategy_score": 55},
        "risk": {"frozen_parameter_snapshot": {"large": "repeat"}},
        "paper": {"frozen_parameter_snapshot": {"large": "repeat"}},
    }
    compact = _compact_stage_payloads(payload)
    assert compact["analysis"]["analysis_context"]["technical_indicators"] == {"rsi": 52}
    assert compact["setup"]["context"] == {"setup_type": "BREAKOUT"}
    assert compact["strategy"]["strategy_score"] == 55
    assert all("frozen_parameter_snapshot" not in compact[stage]
               for stage in ("analysis", "setup", "strategy", "risk", "paper"))


def test_candidate_candles_are_frozen_and_checked(tmp_path) -> None:
    partition = tmp_path / "BTCUSDT" / "0"
    partition.mkdir(parents=True)
    candle = Candle(symbol="BTCUSDT", timeframe="1m", open_time_ms=0,
                    close_time_ms=59999, open=100, high=101, low=99,
                    close=100, volume=1, quote_volume=100, trades_count=1,
                    is_closed=True, source="test")
    row = {"timeframe": "1m", "open_time_ms": 0, "close_time_ms": 59999,
           "open": "100", "high": "101", "low": "99", "close": "100",
           "volume": "1", "quote_volume": "100", "trades_count": 1,
           "checksum": fingerprint(candle.market_values())}
    source = partition / "CANDLES.jsonl"
    source.write_text(json.dumps(row) + "\n", encoding="utf-8")
    receipt = {"dataset_hash": "a" * 64, "allowed_end_ms": 60000,
               "sha256": _sha256(source)}
    (partition / "CANDLES.json").write_text(json.dumps(receipt), encoding="utf-8")
    loaded = _frozen_candles(partition, "a" * 64)
    assert loaded["1m"][0].market_values() == candle.market_values()
    source.write_text(json.dumps({**row, "close": "101"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CANDIDATE_FROZEN_CANDLES_CORRUPT"):
        _frozen_candles(partition, "a" * 64)
