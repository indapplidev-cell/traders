from __future__ import annotations

import json

import pytest

from traders_ml.parameter_sweep.full_pipeline_ragged import (
    HistoricalCostBucketV1,
    HistoricalCostModelV1,
)
from traders_ml.parameter_sweep.full_pipeline_replay_v3 import (
    FullPipelineReplayEngineV3,
    ReplayPolicyV3,
    replay_signal_shards_v3,
)
from traders_ml.parameter_sweep.full_pipeline_v3 import _sha256


def _model() -> HistoricalCostModelV1:
    return HistoricalCostModelV1(
        observed_rows=0,
        buckets={"GLOBAL": HistoricalCostBucketV1(
            key="GLOBAL", sample_size=0, entry_fee_bps=10, exit_fee_bps=10,
            spread_bps=3, entry_slippage_bps=2, exit_slippage_bps=2,
            reserve_bps=3,
        )},
    )


def _engine(slots: int = 1) -> FullPipelineReplayEngineV3:
    return FullPipelineReplayEngineV3(
        policy=ReplayPolicyV3(max_open_positions=slots,
                              max_new_commands_per_cycle=2,
                              risk_per_trade_bps=20,
                              total_open_risk_limit_bps=40,
                              entry_ttl_ms=180_000,
                              hard_timeout_ms=600_000),
        cost_model=_model(), initial_equity=1000, role_end_ms=1_000_000,
    )


def _decision(symbol: str, score: float = 100, opportunity: str = "one") -> dict:
    return {"symbol": symbol, "statuses": {"paper_status": "PAPER_PLAN_READY"},
            "paper": {"source_setup_id": f"{symbol}:{opportunity}",
                      "source_risk_score": score,
                      "hypothetical_entry_reference": 100,
                      "hypothetical_stop_level": 99,
                      "hypothetical_target_level": 102,
                      "paper_context": {}}}


def test_shared_slots_later_fill_and_separate_cost_ledger() -> None:
    engine = _engine()
    engine.on_boundary(300_000, [_decision("ETHUSDT", 90), _decision("BTCUSDT", 100)])
    assert set(engine.pending) == {"BTCUSDT"}
    assert any(trace["reason"] == "PORTFOLIO_SLOTS_FULL" for trace in engine.traces)
    engine.on_1m_candle("BTCUSDT", {"close_time_ms": 359_999, "high": 100.5,
                                     "low": 99.5, "close": 100.2})
    assert len(engine.positions) == 1
    engine.on_1m_candle("BTCUSDT", {"close_time_ms": 419_999, "high": 102.5,
                                     "low": 99.5, "close": 102.2})
    result = engine.finish_role()
    assert len(result["trades"]) == 1
    ledger = result["trades"][0]["ledger"]
    assert ledger["gross_pnl"] - sum(ledger[key] for key in (
        "entry_fee", "exit_fee", "spread", "entry_slippage",
        "exit_slippage", "depth_impact", "reserve")) == pytest.approx(ledger["net_pnl"])
    assert ledger["provenance"] == "MODELLED_CONSERVATIVE"
    assert result["balance"] == pytest.approx(1000 + ledger["net_pnl"])


def test_no_same_candle_fill_and_repeated_opportunity_is_blocked() -> None:
    engine = _engine(slots=2)
    engine.on_1m_candle("BTCUSDT", {"close_time_ms": 299_999, "high": 101,
                                     "low": 99, "close": 100})
    engine.on_boundary(300_000, [_decision("BTCUSDT")])
    assert not engine.positions
    engine.on_boundary(600_000, [_decision("BTCUSDT")])
    assert any(trace["reason"] == "DUPLICATE_WITHOUT_RESET" for trace in engine.traces)
    assert not engine.positions


def test_stop_wins_when_stop_and_target_touch_same_later_candle() -> None:
    engine = _engine()
    engine.on_boundary(300_000, [_decision("BTCUSDT")])
    engine.on_1m_candle("BTCUSDT", {"close_time_ms": 359_999,
                                     "high": 103, "low": 98, "close": 101})
    assert engine.trades[0]["reason"] == "STOP"


def test_role_boundary_rejects_future_candle() -> None:
    engine = _engine()
    engine.on_boundary(300_000, [_decision("BTCUSDT")])
    with pytest.raises(ValueError, match="OUTSIDE_CHRONOLOGY_OR_ROLE"):
        engine.on_1m_candle("BTCUSDT", {"close_time_ms": 1_059_999,
                                         "high": 101, "low": 99, "close": 100})


def test_shards_merge_native_signals_with_later_candles(tmp_path) -> None:
    shards = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        root = tmp_path / symbol
        root.mkdir()
        signal = root / "signals.jsonl"
        signal.write_text(json.dumps({**_decision(symbol), "boundary_ms": 300_000})
                          + "\n", encoding="utf-8")
        signal.with_suffix(".json").write_text(json.dumps({
            "dataset_hash": "frozen", "symbol": symbol,
            "sha256": _sha256(signal),
        }), encoding="utf-8")
        candles = root / "CANDLES.jsonl"
        candles.write_text("".join(json.dumps({
            "timeframe": "1m", "open_time_ms": time_ms - 59_999,
            "close_time_ms": time_ms, "open": 100, "volume": 1,
            "high": high, "low": low, "close": close,
        }) + "\n" for time_ms, high, low, close in (
            (359999, 100.5, 99.5, 100),
            (419999, 102.5, 99.5, 102),
        )), encoding="utf-8")
        (root / "CANDLES.json").write_text(json.dumps({
            "dataset_hash": "frozen", "allowed_end_ms": 1_000_000,
            "sha256": _sha256(candles),
        }), encoding="utf-8")
        shards[symbol] = signal, candles
    result = replay_signal_shards_v3(
        shards, dataset_hash="frozen", policy=_engine().policy,
        cost_model=_model(), initial_equity=1000,
        role_start_ms=300_000, role_end_ms=1_000_000,
        holdout_start_ms=1_000_000,
        analytical_exit=lambda *_: None,
    )
    assert len(result["trades"]) == 1
    assert result["trades"][0]["filled_ms"] > result["trades"][0]["signal_ms"]
    assert result["holdout_evaluated"] is False
    assert result["analytical_exit_integrated"] is True
    native = replay_signal_shards_v3(
        shards, dataset_hash="frozen", policy=_engine().policy,
        cost_model=_model(), initial_equity=1000,
        role_start_ms=300_000, role_end_ms=1_000_000,
        holdout_start_ms=1_000_000,
    )
    assert len(native["trades"]) == 1
    assert native["status"] == "REPLAY_NOT_VERIFIED"
