from __future__ import annotations

from pathlib import Path

import pytest

from traders_ml.parameter_sweep.full_pipeline import FullPipelineCalibrationRequestV2
from traders_ml.parameter_sweep.full_pipeline_ragged import (
    FullPipelineReplayEngineV1,
    HistoricalConservativeCostSource,
    HistoricalCostBucketV1,
    HistoricalCostModelV1,
    _closed_boundary_count,
    _intersect,
    _training_validation_rows,
    _truncate_to_checkpoint,
    fit_cost_model,
)
from traders_ml.parameter_sweep.historical_replay import gate_candidate

ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / "config" / "research" / "full_pipeline_calibration_v2.json"


def test_v2_request_uses_shared_calendar_holdout_and_twenty_symbols():
    request = FullPipelineCalibrationRequestV2.model_validate_json(
        REQUEST.read_text(encoding="utf-8")
    )
    assert len(request.symbols) == 20
    assert request.live_allowed is False
    assert request.warmup_bars == {"1m": 60, "5m": 120, "15m": 64, "1h": 50}
    holdout = next(item for item in request.windows if item.role == "INTERNAL_HOLDOUT")
    assert holdout.locked is True
    assert holdout.end_ms - holdout.start_ms == 10 * 86_400_000


def test_segment_intersection_keeps_only_common_causal_ranges():
    assert _intersect([(0, 10), (20, 40)], [(5, 25), (30, 35)]) == [
        (5, 10), (20, 25), (30, 35),
    ]


def test_closed_boundary_count_respects_alignment_and_exclusive_end():
    step = 300_000
    assert _closed_boundary_count(0, 3 * step - 1, step) == 3
    assert _closed_boundary_count(60_000, 3 * step - 1, step) == 2
    assert _closed_boundary_count(0, step, step) == 1
    assert _closed_boundary_count(step, step, step) == 0


def test_v3_cost_fit_query_excludes_all_validation_and_holdout():
    request = FullPipelineCalibrationRequestV2.model_validate_json(
        REQUEST.read_text(encoding="utf-8"))

    class EmptyRows:
        def mappings(self):
            return iter(())

    class Connection:
        statement = None
        parameters = None

        def execute(self, statement, parameters):
            self.statement = str(statement)
            self.parameters = parameters
            return EmptyRows()

    connection = Connection()
    cutoff = next(window.start_ms for window in request.windows
                  if window.name == "FINAL_VALIDATION")
    model = fit_cost_model(connection, request, cutoff_ms=cutoff,
                           exclude_validation=True)
    assert connection.parameters["end_ms"] == cutoff
    assert connection.parameters["v0_start"] == request.windows[0].start_ms
    assert connection.parameters["v1_start"] == request.windows[1].start_ms
    assert connection.parameters["v2_start"] == request.windows[2].start_ms
    assert "v3_start" not in connection.parameters
    assert "AND NOT" in connection.statement
    assert model.observed_rows == 0


def test_aggregate_cost_bucket_is_modelled_at_decision_time():
    model = HistoricalCostModelV1(
        observed_rows=100,
        buckets={"GLOBAL": HistoricalCostBucketV1(
            key="GLOBAL", sample_size=100, entry_fee_bps=10,
            exit_fee_bps=10, spread_bps=5, entry_slippage_bps=2,
            exit_slippage_bps=2, reserve_bps=3),
                 "SYMBOL:BTCUSDT": HistoricalCostBucketV1(
            key="SYMBOL:BTCUSDT", sample_size=100, entry_fee_bps=10,
            exit_fee_bps=10, spread_bps=5, entry_slippage_bps=2,
            exit_slippage_bps=2, reserve_bps=3)},
    )
    source = HistoricalConservativeCostSource(model)
    source.boundary_ms = 12345
    costs = source.load("BTCUSDT", 100, safety_margin_bps=3)
    assert "MODELLED_CONSERVATIVE" in costs.fee_source


def test_conservative_cost_model_uses_symbol_then_global_fallback():
    global_bucket = HistoricalCostBucketV1(
        key="GLOBAL", sample_size=100, entry_fee_bps=10, exit_fee_bps=10,
        spread_bps=4, entry_slippage_bps=2, exit_slippage_bps=2, reserve_bps=3,
    )
    btc = HistoricalCostBucketV1(
        key="SYMBOL:BTCUSDT", sample_size=25, entry_fee_bps=10, exit_fee_bps=10,
        spread_bps=2, entry_slippage_bps=2, exit_slippage_bps=2, reserve_bps=3,
    )
    model = HistoricalCostModelV1(
        observed_rows=125, buckets={"GLOBAL": global_bucket, "SYMBOL:BTCUSDT": btc},
    )
    assert model.resolve("BTCUSDT")[0].spread_bps == 2
    assert model.resolve("BTCUSDT")[1] == "OBSERVED"
    assert model.resolve("NEWUSDT")[0].spread_bps == 4
    assert model.resolve("NEWUSDT")[1] == "MODELLED_CONSERVATIVE"
    assert model.resolve("NEWUSDT")[0].round_trip_bps == 31


def test_replay_windows_cannot_overlap():
    engine = FullPipelineReplayEngineV1([{"boundary_ms": 10}])
    with pytest.raises(ValueError, match="OVERLAPPING_REPLAY_WINDOWS"):
        engine.split([
            {"name": "a", "start_ms": 0, "end_ms": 20},
            {"name": "b", "start_ms": 5, "end_ms": 15},
        ])


def test_training_excludes_validation_and_clips_future_execution_path():
    request = FullPipelineCalibrationRequestV2.model_validate_json(
        REQUEST.read_text(encoding="utf-8")
    )
    final = next(window for window in request.windows if window.name == "FINAL_VALIDATION")
    earlier = next(window for window in request.windows if window.name == "FOLD_3_VALIDATION")
    holdout = next(window for window in request.windows if window.role == "INTERNAL_HOLDOUT")
    rows = [
        {"boundary_ms": final.start_ms - 60_000,
         "market_path_1m": [{"close_time_ms": final.start_ms - 1},
                            {"close_time_ms": final.start_ms + 60_000}]},
        {"boundary_ms": earlier.start_ms, "market_path_1m": []},
        {"boundary_ms": final.start_ms,
         "market_path_1m": [{"close_time_ms": final.end_ms - 1},
                            {"close_time_ms": final.end_ms + 60_000}]},
        {"boundary_ms": holdout.start_ms, "market_path_1m": []},
    ]
    training, validation = _training_validation_rows(rows, request.windows)
    assert [row["boundary_ms"] for row in training] == [final.start_ms - 60_000]
    assert [row["boundary_ms"] for row in validation] == [final.start_ms]
    assert len(training[0]["market_path_1m"]) == 1
    assert len(validation[0]["market_path_1m"]) == 1


def test_strategy_threshold_is_part_of_end_to_end_gate():
    row = {
        "strategy_score": 49, "stop_distance_bps": 20, "target_distance_bps": 40,
        "effective_total_cost_bps": 25, "net_rr": 1.2, "net_edge_bps": 15,
        "probability_sample_size": 0, "causal_reset_conditions": 1,
    }
    config = {
        "strategy_minimum_score": 50, "stop_max_bps": 36, "target_min_bps": 40,
        "minimum_planned_rr": 1.0, "min_net_edge_bps": 8,
        "bucket_min_sample": 20, "min_positive_ev_r": 0,
        "causal_reset_min_conditions": 1, "adverse_fill_reserve_bps": 3,
        "entry_slippage_bps": 2,
    }
    assert gate_candidate(row, config) == (False, "REJECT_STRUCTURAL")
    row["strategy_score"] = 50
    assert gate_candidate(row, config) == (True, "PASSED")


def test_resume_truncates_uncommitted_jsonl_tail(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text(
        '{"boundary_ms":100,"value":"kept"}\n'
        '{"boundary_ms":200,"value":"uncommitted"}\n',
        encoding="utf-8",
    )
    _truncate_to_checkpoint(path, 100)
    assert path.read_text(encoding="utf-8").splitlines() == [
        '{"boundary_ms": 100, "value": "kept"}'
    ]
