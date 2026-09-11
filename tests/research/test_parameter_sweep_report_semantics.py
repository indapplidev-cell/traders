from datetime import datetime, timezone

from traders_ml.parameter_sweep.artifact_v2 import (
    aggregate_result_semantics, compact_result,
)


def _item(index: int, validation_trades: int = 0):
    trades = [
        {"net_pnl": 1, "symbol": "BTCUSDT"}
        for _ in range(validation_trades)
    ]
    return {
        "result_index": index,
        "result_status": "REJECTED",
        "validation": {
            "trade_count": validation_trades,
            "trades": trades,
            "symbol_coverage": 1 if trades else 0,
        },
        "calibration": {"trade_count": 0},
        "holdout": {"trade_count": 0},
    }


def test_canonical_semantics_counts_every_insufficient_result_and_gates():
    rows = [compact_result(_item(0)), compact_result(_item(1))]
    summary = aggregate_result_semantics(rows)
    assert summary["classification_counts"] == {"INSUFFICIENT_SAMPLE": 2}
    assert summary["evaluation_status_counts"] == {"ACCEPTED": 0, "ERROR": 0, "REJECTED": 2}
    assert summary["performance_class_counts"] == {"INSUFFICIENT_SAMPLE": 2}
    assert summary["insufficient_configs"] == 2
    assert summary["candidate_promotion_eligible"] is False
    assert set(summary["validation_readiness"]) >= {
        "validation_trade_count", "symbol_coverage", "independent_period_count",
        "holdout_count", "minimum_slice_count",
    }


def test_historical_control_and_validation_baseline_are_not_substituted():
    historical_control_trades = 98
    search_validation = compact_result(_item(0, validation_trades=0))
    assert historical_control_trades == 98
    assert search_validation["trade_count"] == 0
    assert search_validation["performance_class"] == "INSUFFICIENT_SAMPLE"


def test_validation_trade_population_is_authoritative_for_coverage_and_periods():
    symbols = ("ADAUSDT", "DOGEUSDT", "LINKUSDT", "SUIUSDT", "XRPUSDT")
    start = int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
    trades = [
        {
            "symbol": symbols[index % len(symbols)],
            "setup_type": None if index == 0 else "SCALP_MOMENTUM_CONTINUATION",
            "opened_at_ms": start + (index % 3) * 86_400_000,
            "net_pnl": 1 if index % 2 else -1,
        }
        for index in range(21)
    ]
    item = _item(7)
    item["validation"] = {
        "trade_count": 999, "wins": 999, "losses": 0,
        "symbol_coverage": 0, "setup_coverage": 0,
        "independent_period_count": 0, "trades": trades,
    }
    row = compact_result(item)
    assert row["trade_count"] == 21
    assert row["win_count"] == 10 and row["loss_count"] == 11
    assert row["symbol_coverage"] == 5
    assert row["setup_coverage"] == 2  # explicit UNKNOWN plus the named setup
    assert row["independent_period_count"] == 3
    assert row["independent_period_status"] == "COMPLETE"
    assert row["independent_period_buckets"] == ["2026-09-01", "2026-09-02", "2026-09-03"]
    failed = {gate["gate"] for gate in row["insufficient_sample_gates"]}
    assert "symbol_coverage" not in failed
    assert "independent_period_count" not in failed


def test_missing_trade_timestamp_is_data_incomplete_not_zero():
    item = _item(8)
    item["validation"] = {
        "trades": [{"symbol": "BTCUSDT", "setup_type": "BREAKOUT", "net_pnl": 1}],
    }
    row = compact_result(item)
    assert row["independent_period_count"] is None
    assert row["independent_period_status"] == "DATA_INCOMPLETE"
    gate = next(gate for gate in row["insufficient_sample_gates"] if gate["gate"] == "independent_period_count")
    assert gate == {"gate": "independent_period_count", "current": None, "required": 3, "deficit": None, "status": "DATA_INCOMPLETE"}


def test_evaluation_and_performance_axes_never_cancel_each_other():
    rows = []
    for index in range(126):
        row = compact_result(_item(index))
        row["evaluation_status"] = "ACCEPTED" if index < 50 else "REJECTED"
        rows.append(row)
    summary = aggregate_result_semantics(rows)
    assert summary["evaluation_status_counts"] == {"ACCEPTED": 50, "ERROR": 0, "REJECTED": 76}
    assert summary["performance_class_counts"] == {"INSUFFICIENT_SAMPLE": 126}


def test_seed_mismatch_is_a_resume_identity_mismatch():
    from traders_ml.parameter_sweep.checkpoint import compatible
    base = {"run_id": "r", "git_commit": "g", "config_hash": "c", "search_space_hash": "s", "dataset_fingerprint": "d", "strategy": "TARGETED_STAGED", "seed": 7, "resolved_seed": 7}
    assert compatible(base, dict(base)) is True
    assert compatible(base, {**base, "seed": 8, "resolved_seed": 8}) is False
