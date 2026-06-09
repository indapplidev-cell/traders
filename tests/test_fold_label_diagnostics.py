from types import SimpleNamespace

from app.diagnostics.fold_label_diagnostics import FoldLabelDiagnostics


def test_fold_label_diagnostics_detects_imbalance_and_missing_class() -> None:
    diagnostics = FoldLabelDiagnostics()
    fold = {
        "fold_index": 1,
        "train_start": "2025-01-01T00:00:00+00:00",
        "train_end": "2025-02-01T00:00:00+00:00",
        "validation_start": "2025-02-01T00:00:00+00:00",
        "validation_end": "2025-02-11T00:00:00+00:00",
        "test_start": "2025-02-11T00:00:00+00:00",
        "test_end": "2025-02-21T00:00:00+00:00",
        "train_rows_data": [_row("UP"), _row("UP"), _row("UP"), _row("DOWN")],
        "validation_rows_data": [_row("FLAT"), _row("FLAT"), _row("UP")],
        "test_rows_data": [_row("UP"), _row("DOWN"), _row("FLAT")],
    }

    report = diagnostics.build_report(
        symbol="BTCUSDT",
        interval="15m",
        feature_version="fv1",
        label_version="lv1",
        folds=[fold],
    )

    assert report["labels_are_balanced_by_fold"] is False
    assert "train_up_ratio_gte_0_60" in report["warnings"]
    assert "flat_ratio_gte_0_50" in report["warnings"]
    assert "class_missing" in report["warnings"]


def _row(direction_label: str) -> SimpleNamespace:
    return SimpleNamespace(direction_label=direction_label)
