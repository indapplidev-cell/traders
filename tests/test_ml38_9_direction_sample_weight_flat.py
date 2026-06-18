from types import SimpleNamespace

from app.diagnostics.direction_head_separation_diagnostics import direction_sample_weight_for_row


def test_ml38_9_stable_flat_gets_more_weight_than_noisy_flat() -> None:
    stable_flat = SimpleNamespace(
        direction_label="FLAT",
        future_move_atr=0.05,
        max_favorable_move_atr=0.20,
        max_adverse_move_atr=0.10,
    )
    noisy_flat = SimpleNamespace(
        direction_label="FLAT",
        future_move_atr=0.10,
        max_favorable_move_atr=1.10,
        max_adverse_move_atr=0.90,
    )

    assert direction_sample_weight_for_row(stable_flat) > direction_sample_weight_for_row(noisy_flat)
    assert direction_sample_weight_for_row(stable_flat) >= 1.30
    assert direction_sample_weight_for_row(noisy_flat) <= 0.50


def test_ml38_9_stable_flat_can_match_strong_direction_weight() -> None:
    stable_flat = SimpleNamespace(
        direction_label="FLAT",
        future_move_atr=0.05,
        max_favorable_move_atr=0.20,
        max_adverse_move_atr=0.10,
    )
    strong_up = SimpleNamespace(
        direction_label="UP",
        future_move_atr=1.10,
        max_favorable_move_atr=1.30,
        max_adverse_move_atr=0.20,
    )

    assert direction_sample_weight_for_row(stable_flat) >= direction_sample_weight_for_row(strong_up)
