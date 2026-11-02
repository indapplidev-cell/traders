from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import json

import yaml

import pytest

from traders_ml.parameter_sweep.bull_run_weights import (
    AcceptanceGates,
    BullRunEvent,
    CalibrationRequest,
    Candle5m,
    CausalObservation,
    EntryScoreWeights,
    ExitPathPoint,
    ExitScoreWeights,
    ScoreThresholds,
    SplitWindow,
    WeightConfiguration,
    acceptance_failures,
    candidate_configurations,
    entry_score,
    label_bull_runs,
    replay_configuration,
    run,
    run_search,
    trade_metrics,
)
from traders_ml.parameter_sweep.result_search import fingerprint


BASE = 1_780_000_000_000


def candle(index: int, close: float, *, symbol: str = "BTCUSDT", cost: float | None = 4.0):
    open_time = BASE + index * 300_000
    return Candle5m(
        symbol=symbol, open_time_ms=open_time, close_time_ms=open_time + 299_999,
        open=close, high=close * 1.001, low=close * 0.999, close=close,
        atr=1.0, round_trip_cost_bps=cost,
    )


def point(index: int, price: float, *, opposed: float = 0.0, strong: bool = False):
    open_time = BASE + index * 60_000
    return ExitPathPoint(
        open_time_ms=open_time, close_time_ms=open_time + 59_999,
        open=price, high=price * 1.0001, low=price * 0.9999, close=price,
        graphical_structure=opposed, technical_indicators=opposed,
        momentum_volume=opposed, strong_reversal=strong,
    )


def observation(identity: str = "o1", *, boundary: int = BASE, future: bool = False,
                direction: str = "BULLISH", components: float = 100.0,
                path: tuple[ExitPathPoint, ...] | None = None):
    first_index = (boundary - BASE) // 60_000 + 1
    return CausalObservation(
        observation_id=identity, symbol="BTCUSDT", boundary_ms=boundary,
        direction=direction, future_bars_used=future,
        entry_components={name: components for name in (
            "structure", "context", "momentum", "volume", "entry_quality",
            "liquidity", "confirmation",
        )},
        entry_penalty=0, entry_cap=100, entry_price=100, stop_price=98,
        target_price=103, entry_fee_bps=1, exit_fee_bps=1,
        entry_slippage_bps=1, exit_slippage_bps=1, spread_bps=2,
        adverse_fill_reserve_bps=2,
        exit_path=path or (
            point(first_index, 100.2),
            point(first_index + 1, 100.5, opposed=1.0, strong=True),
        ),
    )


def request(*, trials: int = 8):
    return CalibrationRequest(
        symbols=("BTCUSDT",), period_start_ms=BASE, period_end_ms=BASE + 900_000,
        splits=(
            SplitWindow(name="SEARCH", start_ms=BASE, end_ms=BASE + 300_000),
            SplitWindow(name="VALIDATION", start_ms=BASE + 300_000, end_ms=BASE + 600_000),
            SplitWindow(name="HOLDOUT", start_ms=BASE + 600_000, end_ms=BASE + 900_000),
        ), max_trials=trials, finalist_count=2,
        gates=AcceptanceGates(minimum_closed_trades=1, minimum_independent_days=1,
                              maximum_symbol_profit_share=1.0),
    )


def test_weight_and_threshold_contracts_are_fail_closed():
    assert EntryScoreWeights().model_dump() == {
        "structure": 25.0, "context": 15.0, "momentum": 15.0, "volume": 15.0,
        "entry_quality": 10.0, "liquidity": 10.0, "confirmation": 10.0,
    }
    with pytest.raises(ValueError, match="sum to 100"):
        EntryScoreWeights(structure=20)
    with pytest.raises(ValueError, match="less than or equal to 45"):
        ExitScoreWeights(graphical_structure=50, technical_indicators=30,
                         momentum_volume=10, holding_economics=10)
    with pytest.raises(ValueError, match="at_risk < exit"):
        ScoreThresholds(at_risk=70, exit=70, strong_reversal=80)


def test_labels_profitable_non_overlapping_executable_close_moves():
    values = [candle(index, close) for index, close in enumerate((100, 99, 101, 100, 103, 102))]
    events, diagnostics = label_bull_runs(values, minimum_edge_bps=8)
    assert diagnostics["blocked_symbols"] == []
    assert events
    assert all(event.net_excursion_bps > 8 for event in events)
    assert all(left.peak_open_time_ms < right.entry_open_time_ms
               for left, right in zip(events, events[1:]))
    assert all(event.source_checksums for event in events)


def test_labels_reject_missing_cost_and_block_gaps():
    values = [candle(0, 100), candle(1, 99, cost=None), candle(2, 103)]
    events, diagnostics = label_bull_runs(values)
    assert events == []
    assert diagnostics["symbols"]["BTCUSDT"]["missing_cost_starts"] == 1
    gapped = [candle(0, 100), candle(2, 103)]
    events, diagnostics = label_bull_runs(gapped)
    assert events == []
    assert diagnostics["blocked_symbols"] == ["BTCUSDT"]


def test_entry_score_is_weighted_and_capped_without_bypassing_invalidations():
    item = observation(components=80)
    assert entry_score(item, EntryScoreWeights()) == 80
    capped = item.model_copy(update={"entry_cap": 64.999, "entry_penalty": 10})
    assert entry_score(capped, EntryScoreWeights()) == 64.999
    future = item.model_copy(update={"future_bars_used": True})
    trades, diagnostics = replay_configuration([future], [], WeightConfiguration())
    assert trades == []
    assert diagnostics["rejections"] == {"FUTURE_BARS_REJECTED": 1}


def test_replay_uses_next_boundary_exit_and_exact_cost_identity():
    config = WeightConfiguration(thresholds=ScoreThresholds(
        entry=80, at_risk=50, exit=60, strong_reversal=70,
    ))
    item = observation(path=(point(1, 100.2, opposed=1.0, strong=True), point(2, 100.4)))
    trades, _ = replay_configuration([item], [], config)
    assert len(trades) == 1
    trade = trades[0]
    assert trade.exit_reason == "STRONG_REVERSAL"
    assert trade.exit_boundary_ms == BASE + 2 * 60_000
    assert trade.net_pnl_bps == pytest.approx(
        trade.gross_pnl_bps - trade.fees_bps - trade.slippage_spread_reserve_bps
    )
    assert trade.net_pnl == pytest.approx(trade.gross_pnl - trade.fees - trade.impact_cost)


def test_future_changes_do_not_change_prior_causal_trade():
    config = WeightConfiguration(thresholds=ScoreThresholds(
        entry=80, at_risk=50, exit=60, strong_reversal=70,
    ))
    prefix = (point(1, 100.2, opposed=1.0, strong=True), point(2, 100.4))
    first, _ = replay_configuration([observation(path=prefix + (point(3, 50),))], [], config)
    second, _ = replay_configuration([observation(path=prefix + (point(3, 500),))], [], config)
    assert first[0].to_dict() == second[0].to_dict()


def test_replay_preserves_symbol_and_portfolio_capacity():
    rows = [observation("first", boundary=BASE), observation("same", boundary=BASE + 30_000)]
    trades, diagnostics = replay_configuration(rows, [], WeightConfiguration())
    assert len(trades) == 1
    assert diagnostics["rejections"]["SYMBOL_POSITION_ALREADY_OPEN"] == 1


def test_metrics_and_acceptance_include_false_entry_and_concentration_gates():
    trades, _ = replay_configuration([observation()], [], WeightConfiguration())
    metrics = trade_metrics(trades)
    failures = acceptance_failures(metrics, metrics, AcceptanceGates(
        minimum_closed_trades=1, minimum_independent_days=1,
        minimum_profit_factor=0.1, minimum_win_rate_exclusive=0,
        maximum_symbol_profit_share=0.5,
    ))
    assert "NEGATIVE_WINDOW_PNL" not in failures
    assert "SYMBOL_PROFIT_CONCENTRATION" in failures


def test_search_is_deterministic_and_holdout_is_opened_after_freeze():
    req = request()
    rows = [
        observation("search", boundary=BASE),
        observation("validation", boundary=BASE + 300_000),
        observation("holdout", boundary=BASE + 600_000),
    ]
    one = run_search(req, rows, [])
    two = run_search(req, rows, [])
    assert one == two
    assert one["holdout_opened_after_finalist_freeze"] is True
    assert one["finalists_frozen_hash"]


def test_candidate_generation_is_bounded_unique_and_seeded():
    req = request(trials=25)
    first = candidate_configurations(req)
    second = candidate_configurations(req)
    assert [item.identity for item in first] == [item.identity for item in second]
    assert len(first) == 25
    assert len({item.identity for item in first}) == 25


def test_search_uses_seeded_single_worker_tpe_after_sensitivity_stage():
    req = request(trials=72)
    rows = [
        observation("search", boundary=BASE),
        observation("validation", boundary=BASE + 300_000),
        observation("holdout", boundary=BASE + 600_000),
    ]
    result = run_search(req, rows, [])
    assert result["optimizer"] == "OPTUNA_TPE_SINGLE_WORKER"
    assert result["optimizer_workers"] == 1
    assert result["optimizer_seed"] == req.seed
    assert result["evaluated_count"] == 72


def test_end_to_end_publishes_strict_integrity_and_inactive_candidate(tmp_path: Path):
    req = request()
    request_path = tmp_path / "request.json"
    request_path.write_text(req.model_dump_json(), encoding="utf-8")
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    candles = [candle(index, close).model_dump(mode="json") for index, close in enumerate((100, 99, 101))]
    rows = [
        observation("search", boundary=BASE).model_dump(mode="json"),
        observation("validation", boundary=BASE + 300_000).model_dump(mode="json"),
        observation("holdout", boundary=BASE + 600_000).model_dump(mode="json"),
    ]
    candle_bytes = b"".join(json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                            for row in candles)
    row_bytes = b"".join(json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                         for row in rows)
    (dataset / "CANDLES_5M.jsonl").write_bytes(candle_bytes)
    (dataset / "CAUSAL_OBSERVATIONS.jsonl").write_bytes(row_bytes)
    manifest = {
        "schema": "bull-run-causal-observations/1", "symbols": ["BTCUSDT"],
        "evidence_quality": "HISTORICAL_VERIFIED",
        "candles_sha256": sha256(candle_bytes).hexdigest(),
        "observations_sha256": sha256(row_bytes).hexdigest(),
    }
    manifest["fingerprint"] = fingerprint(manifest)
    (dataset / "DATASET_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "output"
    result = run(request_path, dataset, output)
    assert result["outcome"] in {"ELIGIBLE_CANDIDATE", "NO_ELIGIBLE_CANDIDATE"}
    candidate = yaml.safe_load((output / "INACTIVE_CANDIDATE.yaml").read_text(encoding="utf-8"))
    assert candidate["active"] is False
    integrity = json.loads((output / "INTEGRITY.json").read_text(encoding="utf-8"))
    assert integrity["production_mutations"] == 0
    assert integrity["live_enabled"] is False
    assert (output / "REPORT.md").exists()
