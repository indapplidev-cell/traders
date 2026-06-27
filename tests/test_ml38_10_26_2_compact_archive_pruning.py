import json
from pathlib import Path

from app.reporting.compact_report import (
    COMPACT_REPORT_PROFILE,
    prune_and_compact_report_tree,
    should_include_report_file,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_prune_and_compact_report_tree_keeps_summary_but_removes_heavy_files(tmp_path: Path) -> None:
    archive_root = tmp_path / "stage"
    experiment = archive_root / "per_symbol_experiments" / "fv3_cached_fresh_tuning_btcusdt_15m_test"

    summary = experiment / "feature_regime_experiment_summary.json"
    _write_json(
        summary,
        {
            "symbol": "BTCUSDT",
            "candidate_count": 2,
            "candidate_results": [
                {"config_id": "a", "profit_factor": 1.1, "prediction_rows": list(range(1000))},
                {"config_id": "b", "profit_factor": 0.9, "gate_probes": list(range(1000))},
            ],
        },
    )
    (experiment / "feature_regime_experiment_summary.md").write_text("# summary", encoding="utf-8")

    _write_json(
        experiment / "candidate_results" / "candidate_a.json",
        {
            "config_id": "candidate_a",
            "profit_factor": 1.2,
            "candidate_board_rows": [{"x": index} for index in range(1000)],
        },
    )
    (experiment / "candidate_results" / "candidate_a.md").write_text("# candidate", encoding="utf-8")

    _write_json(experiment / "raw_outputs" / "BTCUSDT-run.stdout.json", {"candidate_results": list(range(1000))})
    (experiment / "feature_regime_experiment.log").write_text("log", encoding="utf-8")
    (experiment / "artifacts" / "models" / "m" / "model.pt").parent.mkdir(parents=True)
    (experiment / "artifacts" / "models" / "m" / "model.pt").write_bytes(b"model")

    result = prune_and_compact_report_tree(
        experiment,
        archive_root=archive_root,
        report_profile=COMPACT_REPORT_PROFILE,
    )

    assert result["exists"] is True
    assert result["pruned_files"] >= 3
    assert result["compacted_json_files"] >= 2
    assert result["errors"] == []

    assert summary.exists()
    assert (experiment / "feature_regime_experiment_summary.md").exists()
    assert (experiment / "candidate_results" / "candidate_a.json").exists()
    assert (experiment / "candidate_results" / "candidate_a.md").exists()

    assert not (experiment / "raw_outputs" / "BTCUSDT-run.stdout.json").exists()
    assert not (experiment / "feature_regime_experiment.log").exists()
    assert not (experiment / "artifacts" / "models" / "m" / "model.pt").exists()

    compact_summary = json.loads(summary.read_text(encoding="utf-8"))
    assert compact_summary["summary_payload_compacted"] is True
    assert compact_summary["candidate_count"] == 2

    candidate_payload = json.loads((experiment / "candidate_results" / "candidate_a.json").read_text(encoding="utf-8"))
    assert candidate_payload["summary_payload_compacted"] is True
    assert candidate_payload["config_id"] == "candidate_a"


def test_compact_archive_rules_exclude_runtime_streams_and_models(tmp_path: Path) -> None:
    archive_root = tmp_path / "stage"
    stdout_file = archive_root / "per_symbol_experiments" / "x" / "raw_outputs" / "BTCUSDT-run.stdout.json"
    model_file = archive_root / "per_symbol_experiments" / "x" / "artifacts" / "models" / "m" / "model.pt"
    candidate_file = archive_root / "per_symbol_experiments" / "x" / "candidate_results" / "candidate.json"
    summary_file = archive_root / "per_symbol_experiments" / "x" / "feature_regime_experiment_summary.json"

    for path in (stdout_file, candidate_file, summary_file):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_bytes(b"model")

    assert should_include_report_file(stdout_file, archive_root=archive_root, report_profile=COMPACT_REPORT_PROFILE) is False
    assert should_include_report_file(model_file, archive_root=archive_root, report_profile=COMPACT_REPORT_PROFILE) is False
    assert should_include_report_file(candidate_file, archive_root=archive_root, report_profile=COMPACT_REPORT_PROFILE) is True
    assert should_include_report_file(summary_file, archive_root=archive_root, report_profile=COMPACT_REPORT_PROFILE) is True
