from datetime import datetime, timezone

import pytest

from app.diagnostics.label_grid_sensitivity_recompute import (
    DEFAULT_FLAT_BOUNDARIES,
    DEFAULT_HORIZONS,
    DEFAULT_THRESHOLD_PAIRS,
    build_read_only_label_grid_sensitivity_recompute,
    classify_label_grid_row,
    compute_forward_path_labels,
    compute_label_distribution,
    load_candles_read_only,
)
from app.experiments.multi_symbol_feature_regime_reporter import (
    MultiSymbolFeatureRegimeReporter,
)


def _row(**overrides):
    row = {
        "row_count": 400,
        "up_count": 60,
        "down_count": 60,
        "flat_count": 280,
        "directional_count": 120,
        "up_pct": 15.0,
        "down_pct": 15.0,
        "flat_pct": 70.0,
        "directional_pct": 30.0,
        "flat_to_directional_ratio": 280 / 120,
        "up_down_balance": 1.0,
        "label_noise_risk": "LOW",
    }
    row.update(overrides)
    return row


def _candles(count: int = 40) -> list[dict]:
    return [
        {
            "open_time": datetime(2026, 4, 1, tzinfo=timezone.utc),
            "open": 100 + index * 0.1,
            "high": 101 + index * 0.1,
            "low": 99 + index * 0.1,
            "close": 100.2 + index * 0.1,
            "volume": 1,
        }
        for index in range(count)
    ]


def test_compute_label_distribution_counts_percentages_and_ratio() -> None:
    distribution = compute_label_distribution(["UP"] * 40 + ["DOWN"] * 20 + ["FLAT"] * 40)

    assert distribution["up_count"] == 40
    assert distribution["down_count"] == 20
    assert distribution["flat_count"] == 40
    assert distribution["directional_count"] == 60
    assert distribution["up_pct"] == pytest.approx(40.0)
    assert distribution["down_pct"] == pytest.approx(20.0)
    assert distribution["flat_pct"] == pytest.approx(40.0)
    assert distribution["flat_to_directional_ratio"] == pytest.approx(40 / 60)


def test_small_directional_sample_and_high_flat_pressure() -> None:
    row = _row(
        row_count=1000, up_count=30, down_count=20, flat_count=950,
        directional_count=50, flat_pct=95.0, directional_pct=5.0,
        up_down_balance=2 / 3,
    )
    distribution = compute_label_distribution(["UP"] * 30 + ["DOWN"] * 20 + ["FLAT"] * 950)

    assert classify_label_grid_row(row) == "DIRECTIONAL_SAMPLE_TOO_SMALL"
    assert distribution["expected_baseline_pressure"] == "HIGH"
    assert distribution["sample_warning"] == "directional_sample_below_100"


def test_balanced_directional_samples_can_be_promising() -> None:
    assert classify_label_grid_row(_row()) == "PROMISING_DIAGNOSTIC_ZONE"


def test_low_flat_percentage_is_too_noisy() -> None:
    assert classify_label_grid_row(_row(flat_pct=45.0, directional_pct=55.0)) == "TOO_NOISY"


def test_forward_recompute_is_in_memory_and_returns_no_persistence_object() -> None:
    labels = compute_forward_path_labels(
        _candles(), horizon=8, tp_threshold=0.8, sl_threshold=0.8,
        flat_boundary=0.2,
    )

    assert isinstance(labels, list)
    assert all(set(row) >= {"timestamp", "label", "atr_at_entry"} for row in labels)
    assert all(row["label"] in {"UP", "DOWN", "FLAT"} for row in labels)


def test_read_only_loader_calls_only_repository_get_range() -> None:
    class ReadOnlyRepository:
        def __init__(self):
            self.calls = []

        def get_range(self, **kwargs):
            self.calls.append(kwargs)
            return _candles(2)

        def __getattr__(self, name):
            if name.startswith(("upsert", "save", "write", "add")):
                raise AssertionError(f"write method accessed: {name}")
            raise AttributeError(name)

    repository = ReadOnlyRepository()
    rows = load_candles_read_only(
        "SOLUSDT", "15m", "2026-04-01", "2026-06-15", repository=repository
    )

    assert len(rows) == 2
    assert len(repository.calls) == 1


def test_parameter_grid_and_top_level_block() -> None:
    result = build_read_only_label_grid_sensitivity_recompute(
        _candles(20), horizons=DEFAULT_HORIZONS,
        threshold_pairs=DEFAULT_THRESHOLD_PAIRS,
        flat_boundaries=DEFAULT_FLAT_BOUNDARIES,
    )

    assert result["diagnostic_name"] == "read_only_label_grid_sensitivity_recompute"
    assert result["diagnostic_version"] == "ml38.10.39"
    assert result["execution_mode"] == "READ_ONLY_NO_TRAINING_NO_DB_WRITES"
    assert result["parameter_grid"]["horizons"] == [8, 12, 16, 24]
    assert len(result["sensitivity_board"]) == 4 * 6 * 4
    assert result["db_writes_performed"] is False
    assert result["training_or_runtime_execution"] is False


def test_reporter_preserves_recompute_top_level_block() -> None:
    block = build_read_only_label_grid_sensitivity_recompute(
        _candles(20), horizons=(8,), threshold_pairs=((0.8, 0.8),),
        flat_boundaries=(0.2,),
    )
    compact = MultiSymbolFeatureRegimeReporter().compact_summary_to_dict(
        {"read_only_label_grid_sensitivity_recompute": block}
    )

    assert compact["read_only_label_grid_sensitivity_recompute"] == block
    assert "DO_NOT_CHANGE_GATES" in block["decision"]
    assert "DO_NOT_CHANGE_LABELS_YET" in block["decision"]
