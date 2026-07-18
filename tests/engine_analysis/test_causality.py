from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace

import pytest

from app.engine_analysis import run_engine_analysis
from app.engine_analysis.data_source_boundary import CandleDataRequest, build_candle_data_batch
from app.engine_analysis.market_data_adapter import MarketDataAdapter
from app.engine_analysis.online_errors import InvalidMarketDataSnapshotError


def test_same_closed_input_is_deterministic(candle_factory):
    """Given one closed series, when analyzed twice, then payload and reason order are stable."""
    candles = candle_factory("up")
    first = run_engine_analysis("BTCUSDT", "15m", candles).to_dict()
    second = run_engine_analysis("BTCUSDT", "15m", candles).to_dict()
    assert first == second


def test_analysis_does_not_mutate_input_list(candle_factory):
    """Given caller-owned candles, when analysis runs, then the original sequence is unchanged."""
    candles = candle_factory("range")
    before = list(candles)
    run_engine_analysis("BTCUSDT", "15m", candles)
    assert candles == before


def test_adapter_accepts_only_closed_candles(market_snapshot_factory):
    """Given an open candle, when adapted, then the closed-candle contract rejects the snapshot."""
    snapshot = market_snapshot_factory()
    snapshot.candles[-1] = replace(snapshot.candles[-1], is_closed=False)
    with pytest.raises(InvalidMarketDataSnapshotError, match="open candle"):
        MarketDataAdapter().adapt(snapshot)


def test_snapshot_boundary_rejects_future_close(market_snapshot_factory):
    """Given a bar closing after the boundary, when adapted, then no future bar enters analysis."""
    snapshot = market_snapshot_factory(closed_until_ms=1)
    with pytest.raises(InvalidMarketDataSnapshotError, match="after closed_until_ms"):
        MarketDataAdapter().adapt(snapshot)


def test_higher_timeframe_bar_is_unavailable_before_close(market_snapshot_factory):
    """Given a 1h candle before its close, when adapted, then the higher-TF candle is unavailable."""
    snapshot = market_snapshot_factory(count=1, timeframe="1h", closed_until_ms=3_599_998)
    with pytest.raises(InvalidMarketDataSnapshotError, match="after closed_until_ms"):
        MarketDataAdapter().adapt(snapshot)


def test_adapter_preserves_snapshot_and_identity(market_snapshot_factory):
    """Given a valid snapshot, when adapted, then symbol/timeframe source data is not mutated."""
    snapshot = market_snapshot_factory()
    before = deepcopy(asdict(snapshot))
    candles = MarketDataAdapter().adapt(snapshot)
    assert asdict(snapshot) == before
    assert len(candles) == len(snapshot.candles)
    assert candles[-1].timestamp.endswith("+00:00")


def test_boundary_builder_copies_rows_and_preserves_end(candle_factory):
    """Given mapping rows at a boundary, when batched, then rows stay unchanged and end is stable."""
    rows = [item.to_dict() | {"symbol": "BTCUSDT", "interval": "15m"} for item in candle_factory("up", 8)]
    before = deepcopy(rows)
    batch = build_candle_data_batch(CandleDataRequest("BTCUSDT", "15m", 8), rows, min_candle_count=8)
    assert rows == before
    assert batch.metadata["period_end"] == rows[-1]["timestamp"]
    assert batch.candles[-1].timestamp == rows[-1]["timestamp"]
