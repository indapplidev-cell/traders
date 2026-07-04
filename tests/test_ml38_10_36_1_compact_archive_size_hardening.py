import json

from app.experiments.compact_archive_pruner import (
    compact_json_value,
    compact_staged_symbol_output,
)
import run_fv3_cached_tuning as wrapper


def _write_heavy_training_report(tmp_path):
    report_path = (
        tmp_path
        / "label_grid_runtime"
        / "x"
        / "pipeline_runs"
        / "run1"
        / "training_pipeline_report.json"
    )
    report_path.parent.mkdir(parents=True)
    payload = {
        "status": "ok",
        "symbol": "SOLUSDT",
        "interval": "15m",
        "config_id": "lv36_test",
        "candidate_status": "REJECTED",
        "profit_aware_summary": {"profit_factor": 1.2, "profit_total_r": 3.4},
        "walk_forward_summary": {"walk_forward_total_r": 0.0},
        "flat_bias_root_cause_audit": {
            "actual_flat_rate": 0.92,
            "predicted_flat_rate": 0.11,
            "flat_underprediction_detected": True,
        },
        "pipeline_events": [{"x": "y" * 1000} for _ in range(5000)],
        "prediction_rows": [
            {"p": 0.1, "x": "z" * 1000} for _ in range(5000)
        ],
    }
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    return report_path


def test_compact_helper_reduces_heavy_training_pipeline_report(tmp_path) -> None:
    report_path = _write_heavy_training_report(tmp_path)
    original_size = report_path.stat().st_size

    result = compact_staged_symbol_output(tmp_path)
    final_size = report_path.stat().st_size
    compacted = json.loads(report_path.read_text(encoding="utf-8"))

    assert result.training_pipeline_reports_seen == 1
    assert result.training_pipeline_reports_compacted == 1
    assert result.saved_size_bytes > 0
    assert final_size < original_size
    assert final_size < 2_000_000
    assert compacted["status"] == "ok"
    assert compacted["symbol"] == "SOLUSDT"
    assert compacted["config_id"] == "lv36_test"
    assert "profit_aware_summary" in compacted
    assert "walk_forward_summary" in compacted
    assert "flat_bias_root_cause_audit" in compacted
    assert "__compact_archive_pruning__" in compacted
    assert compacted["pipeline_events"]["_compact_pruned"] is True
    assert compacted["prediction_rows"]["_compact_pruned"] is True


def test_helper_writes_compact_archive_pruning_summary(tmp_path) -> None:
    _write_heavy_training_report(tmp_path)

    compact_staged_symbol_output(tmp_path)
    summary_path = tmp_path / "compact_archive_pruning_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary_path.exists()
    for key in (
        "training_pipeline_reports_seen",
        "training_pipeline_reports_compacted",
        "original_size_bytes",
        "final_size_bytes",
        "saved_size_bytes",
        "files",
    ):
        assert key in summary


def test_feature_regime_experiment_summary_compaction_is_conservative(tmp_path) -> None:
    summary_path = tmp_path / "feature_regime_experiment_summary.json"
    payload = {
        "status": "ok",
        "symbol": "SOLUSDT",
        "candidate_count": 46,
        "best_candidate_config_id": "lv31_test",
        "ranking": [
            {"config_id": f"cfg_{index}", "score": index, "details": "x" * 1000}
            for index in range(10000)
        ],
        "feature_filter_diagnostics": {"some": "diagnostic"},
        "flat_bias_root_cause_audit": {"flat_underprediction_detected": True},
    }
    summary_path.write_text(json.dumps(payload), encoding="utf-8")
    original_size = summary_path.stat().st_size

    result = compact_staged_symbol_output(tmp_path)
    compacted = json.loads(summary_path.read_text(encoding="utf-8"))

    assert result.feature_summaries_seen == 1
    assert result.feature_summaries_compacted == 1
    assert compacted["status"] == "ok"
    assert compacted["symbol"] == "SOLUSDT"
    assert compacted["candidate_count"] == 46
    assert compacted["best_candidate_config_id"] == "lv31_test"
    assert compacted["feature_filter_diagnostics"] == {"some": "diagnostic"}
    assert compacted["flat_bias_root_cause_audit"] == {
        "flat_underprediction_detected": True
    }
    assert compacted["ranking"]["_compact_pruned"] is True
    assert summary_path.stat().st_size < original_size


def test_generic_compactor_preserves_zero_values() -> None:
    compacted = compact_json_value(
        {
            "walk_forward_summary": {
                "total_r_by_symbol": {"BTCUSDT": 0.0, "SOLUSDT": 4.456}
            }
        }
    )

    totals = compacted["walk_forward_summary"]["total_r_by_symbol"]
    assert totals["BTCUSDT"] == 0.0
    assert totals["SOLUSDT"] == 4.456


def test_runtime_config_counts_remain_unchanged() -> None:
    assert len(wrapper.FAST_DEBUG_CONFIGS) == 22
    assert len(wrapper.QUICK_QUALITY_CONFIGS) == 46
