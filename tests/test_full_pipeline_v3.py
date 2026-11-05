"""Causality and accounting invariants for the v3 research cache."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.trade_parameters import load_trade_parameters
from traders_ml.parameter_sweep.full_pipeline_v3 import (
    CausalBoundaryFeaturesV3,
    HistoricalCostLedgerV3,
    _compact_stage_payloads,
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
    with pytest.raises(ValueError, match="UNSUPPORTED_NATIVE_PARAMETER"):
        resolve_research_parameter_set_v3(baseline, {"entry_slippage_bps": 0})


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
