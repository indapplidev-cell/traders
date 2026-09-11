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
