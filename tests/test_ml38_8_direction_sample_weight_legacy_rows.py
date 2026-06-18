from __future__ import annotations

from types import SimpleNamespace

from app.diagnostics.direction_head_separation_diagnostics import (
    direction_sample_weight_for_row,
)


def test_direction_sample_weight_handles_row_without_max_favorable_move_atr() -> None:
    row = SimpleNamespace(
        direction_label="UP",
        future_move_atr=1.0,
        max_adverse_move_atr=0.35,
        features_json={"x": 1.0},
    )

    weight = direction_sample_weight_for_row(row)

    assert isinstance(weight, float)
    assert weight > 0.0
