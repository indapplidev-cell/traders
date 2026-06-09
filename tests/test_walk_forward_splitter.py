from datetime import datetime, timedelta, timezone

from app.validation.walk_forward_splitter import WalkForwardConfig, WalkForwardSplitter


def test_walk_forward_splitter_builds_non_overlapping_windows() -> None:
    splitter = WalkForwardSplitter()
    rows = [
        type("Row", (), {"candle_open_time": datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)})()
        for index in range(90)
    ]
    config = WalkForwardConfig(
        mode="expanding",
        train_days=45,
        validation_days=10,
        test_days=10,
        step_days=10,
        min_train_rows=10,
    )

    folds = splitter.build_plan(rows, config)

    assert len(folds) >= 3
    for fold in folds:
        assert fold["train_end"] <= fold["validation_start"]
        assert fold["validation_end"] <= fold["test_start"]
