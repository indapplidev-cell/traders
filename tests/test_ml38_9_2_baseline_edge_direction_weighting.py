from types import SimpleNamespace

from app.diagnostics.direction_head_separation_diagnostics import (
    baseline_edge_sample_weight_for_row,
)


def test_baseline_edge_weight_boosts_clear_directional_opportunity() -> None:
    row = SimpleNamespace(
        direction_label="UP",
        future_move_atr=0.7,
        max_favorable_move_atr=0.8,
        max_adverse_move_atr=0.2,
        tp_before_sl=True,
    )

    assert baseline_edge_sample_weight_for_row(row, base_weight=1.0) > 1.0


def test_baseline_edge_weight_keeps_clean_flat_relevant() -> None:
    row = SimpleNamespace(
        direction_label="FLAT",
        future_move_atr=0.1,
        max_favorable_move_atr=0.2,
        max_adverse_move_atr=0.2,
        tp_before_sl=None,
    )

    assert baseline_edge_sample_weight_for_row(row, base_weight=1.0) > 1.0
