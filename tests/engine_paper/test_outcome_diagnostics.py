from decimal import Decimal as D
import json

from app.engine_paper.outcome_diagnostics import (
    ClosedTradePath, OutcomeCandle, OutcomeDiagnosticsStore,
    compute_stop_target_diagnostics,
)


def test_closed_long_mae_mfe_stop_target_diagnostics_are_reproducible(tmp_path):
    trade = ClosedTradePath(
        "position:1", "LONG", D("100"), D("99"), D("102"), D("98.8"),
        1000, 4000, "STOP_LOSS",
    )
    candles = (
        OutcomeCandle(1000, D("100.5"), D("99.5")),
        OutcomeCandle(2000, D("101.0"), D("98.8")),
        OutcomeCandle(3000, D("102.2"), D("99.7")),
    )
    result = compute_stop_target_diagnostics(trade, candles)
    assert result.mae == D("1.2")
    assert result.mfe == D("2.2")
    assert result.time_to_mae_ms == 1000
    assert result.time_to_mfe_ms == 2000
    assert result.planned_stop_distance == D("1")
    assert result.actual_stop_slippage == D("0.2")
    assert result.planned_target_distance == D("2")
    assert result.target_reached_after_stop is True
    assert result.max_favorable_before_stop == D("1.0")
    assert result.max_adverse_before_target == D("1.2")
    assert result.holding_time_ms == 3000
    store = OutcomeDiagnosticsStore(tmp_path / "diagnostics.json")
    store.save(result)
    store.save(result)
    assert list(json.loads((tmp_path / "diagnostics.json").read_text())) == ["position:1"]


def test_diagnostics_reject_missing_path_and_never_mutate_trade():
    trade = ClosedTradePath(
        "position:2", "SHORT", D("100"), D("101"), D("98"), D("98"),
        1000, 2000, "TARGET",
    )
    try:
        compute_stop_target_diagnostics(trade, ())
    except ValueError as exc:
        assert "causal candle path" in str(exc)
    else:
        raise AssertionError("missing path was accepted")
    assert trade.actual_exit_price == D("98")
