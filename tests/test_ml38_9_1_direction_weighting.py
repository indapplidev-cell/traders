from types import SimpleNamespace

from app.diagnostics.direction_head_separation_diagnostics import direction_sample_weight_for_row
from app.training.training_service import TrainingService


def test_ml38_9_1_down_and_stable_flat_get_more_weight_than_clean_up() -> None:
    strong_down = SimpleNamespace(
        direction_label="DOWN",
        future_move_atr=-1.10,
        max_favorable_move_atr=1.30,
        max_adverse_move_atr=0.20,
    )
    stable_flat = SimpleNamespace(
        direction_label="FLAT",
        future_move_atr=0.03,
        max_favorable_move_atr=0.20,
        max_adverse_move_atr=0.10,
    )
    strong_up = SimpleNamespace(
        direction_label="UP",
        future_move_atr=1.10,
        max_favorable_move_atr=1.30,
        max_adverse_move_atr=0.20,
    )

    assert direction_sample_weight_for_row(strong_down) > direction_sample_weight_for_row(strong_up)
    assert direction_sample_weight_for_row(stable_flat) > direction_sample_weight_for_row(strong_up)


def test_ml38_9_1_direction_class_weights_are_capped_and_bias_aware() -> None:
    rows = []
    rows.extend(SimpleNamespace(direction_label="UP") for _ in range(60))
    rows.extend(SimpleNamespace(direction_label="DOWN") for _ in range(25))
    rows.extend(SimpleNamespace(direction_label="FLAT") for _ in range(15))

    weights = TrainingService.compute_direction_class_weights(rows)

    assert len(weights) == 3
    up_weight, down_weight, flat_weight = weights
    assert 0.65 <= up_weight <= 1.85
    assert 0.65 <= down_weight <= 1.85
    assert 0.65 <= flat_weight <= 1.85
    assert flat_weight > down_weight > up_weight
