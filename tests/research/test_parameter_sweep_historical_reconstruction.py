from __future__ import annotations

from decimal import Decimal

import pytest

from app.engine_market_data.candle import Candle
from traders_ml.parameter_sweep.historical_reconstruction import (
    CausalCandleRepository,
    SOURCE_PERSISTED,
    SOURCE_RECONSTRUCTED,
    canonical_observation,
    compare_observations,
    merge_hybrid_observations,
)


def _candle(symbol: str, timeframe: str, opened: int, duration: int) -> Candle:
    return Candle(
        symbol=symbol, timeframe=timeframe, open_time_ms=opened,
        close_time_ms=opened + duration - 1,
        open=Decimal("1"), high=Decimal("2"), low=Decimal("0.5"),
        close=Decimal("1.5"), volume=Decimal("10"), quote_volume=Decimal("15"),
        trades_count=2, is_closed=True, source="fixture",
    )


def _observation(boundary: int, *, source: str, eligible: bool = False) -> dict[str, object]:
    return {
        "closed_until_ms": boundary, "symbol": "DOGEUSDT", "profile": "trade-5m-v2",
        "timeframe": "5m", "source_type": source,
        "setup_type": "SCALP_BREAKOUT", "setup_status": "SETUP_CANDIDATE",
        "direction": "BULLISH", "strategy_status": "ALLOW_RESEARCH_TRADE_PLAN",
        "eligibility_status": eligible, "terminal_stage": "NET_COST_GATE",
        "rejection_reason": "PAPER_REJECT_NET_EDGE_NOT_POSITIVE",
        "strategy_score": 70.0, "entry_reference": 1.0, "stop_reference": .99,
        "target_reference": 1.02, "gross_rr": 2.0, "net_rr": 1.1,
        "dynamic_required_rr": .6, "entry_fee_bps": 7.5, "exit_fee_bps": 7.5,
        "spread_bps": 1.0, "entry_slippage_bps": 2.0,
        "exit_slippage_bps": 2.0, "depth_impact_bps": .1,
        "p_win_raw": .5, "p_win_conservative": .4, "expected_ev_r": .04,
    }


@pytest.mark.parametrize(("timeframe", "duration"), (("1m", 60_000), ("5m", 300_000)))
def test_candle_repository_never_returns_future_or_other_symbol_data(timeframe, duration):
    rows = {
        timeframe: [
            _candle("DOGEUSDT", timeframe, duration, duration),
            _candle("DOGEUSDT", timeframe, duration * 2, duration),
        ]
    }
    repository = CausalCandleRepository("DOGEUSDT", rows)

    selected = repository.get_candles(
        "DOGEUSDT", timeframe, end_time_ms=duration, limit=10,
    )

    assert [row.open_time_ms for row in selected] == [duration]
    assert all(row.open_time_ms <= duration for row in selected)
    assert repository.causality_violations == []
    assert repository.get_candles("BTCUSDT", timeframe, end_time_ms=duration) == []
    assert repository.causality_violations[0]["type"] == "CROSS_SYMBOL_READ"


def test_persisted_observation_has_priority_and_overlap_is_not_duplicated():
    reconstructed = [_observation(100, source=SOURCE_RECONSTRUCTED), _observation(200, source=SOURCE_RECONSTRUCTED)]
    persisted = [_observation(200, source=SOURCE_PERSISTED), _observation(300, source=SOURCE_PERSISTED)]

    rows, duplicates = merge_hybrid_observations(
        persisted, reconstructed, certified=True, symbol="DOGEUSDT",
    )

    assert [row["closed_until_ms"] for row in rows] == [100, 200, 300]
    assert rows[1]["source_type"] == SOURCE_PERSISTED
    assert duplicates == 1


def test_uncertified_reconstruction_is_never_included():
    rows, duplicates = merge_hybrid_observations(
        [], [_observation(100, source=SOURCE_RECONSTRUCTED)],
        certified=False, symbol="DOGEUSDT",
    )
    assert rows == []
    assert duplicates == 0


def test_critical_eligibility_mismatch_fails_parity():
    persisted = [_observation(100, source=SOURCE_PERSISTED, eligible=True)]
    reconstructed = [_observation(100, source=SOURCE_RECONSTRUCTED, eligible=False)]

    summary, mismatches = compare_observations(
        persisted, reconstructed, total_overlap_boundaries=1,
    )

    assert summary["critical_field_mismatches"] == 1
    assert any(row["field"] == "eligibility_status" for row in mismatches)


def test_exact_semantic_and_numeric_overlap_can_be_certified_by_caller():
    persisted = [_observation(100, source=SOURCE_PERSISTED)]
    reconstructed = [_observation(100, source=SOURCE_RECONSTRUCTED)]

    summary, mismatches = compare_observations(
        persisted, reconstructed, total_overlap_boundaries=1,
    )

    assert summary["complete_overlap_compared"] is True
    assert summary["critical_field_mismatches"] == 0
    assert summary["numeric_mismatch_count"] == 0
    assert mismatches == []


def test_30_day_fixture_merges_old_reconstructed_and_recent_persisted_once():
    day = 86_400_000
    reconstructed = [_observation(index * day, source=SOURCE_RECONSTRUCTED) for index in range(31)]
    persisted = [_observation(index * day, source=SOURCE_PERSISTED) for index in range(22, 31)]

    rows, duplicates = merge_hybrid_observations(
        persisted, reconstructed, certified=True, symbol="DOGEUSDT",
    )

    assert len(rows) == 31
    assert rows[-1]["closed_until_ms"] - rows[0]["closed_until_ms"] == 30 * day
    assert sum(row["source_type"] == SOURCE_RECONSTRUCTED for row in rows) == 22
    assert sum(row["source_type"] == SOURCE_PERSISTED for row in rows) == 9
    assert duplicates == 9
    assert {row["symbol"] for row in rows} == {"DOGEUSDT"}


def test_cross_symbol_hybrid_fails_closed():
    contaminated = _observation(100, source=SOURCE_RECONSTRUCTED)
    contaminated["symbol"] = "BTCUSDT"
    with pytest.raises(ValueError, match="CROSS_SYMBOL_CONTAMINATION"):
        merge_hybrid_observations([], [contaminated], certified=True, symbol="DOGEUSDT")


def test_canonical_contract_marks_unavailable_causal_inputs_explicitly():
    row = {
        "symbol": "DOGEUSDT", "trade_profile_id": "trade-5m-v2",
        "primary_timeframe": "5m", "closed_until_ms": 100,
        "analysis_payload_json": {},
        "setup_payload_json": {"status": "NO_SETUP", "setup_type": "NO_SETUP"},
        "strategy_payload_json": {}, "risk_payload_json": {}, "paper_payload_json": {},
    }
    canonical = canonical_observation(row, source_type=SOURCE_PERSISTED)
    assert canonical["schema"] == "historical-causal-observation:v1"
    assert canonical["causally_unavailable"]["spread_bps"] == "CAUSAL_INPUT_UNAVAILABLE"
    assert canonical["source_type"] == SOURCE_PERSISTED
