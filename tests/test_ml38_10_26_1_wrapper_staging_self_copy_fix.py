from __future__ import annotations

import json

import run_fv3_cached_tuning


def test_self_copy_staging_keeps_existing_summary_files(tmp_path) -> None:
    args = run_fv3_cached_tuning.parse_args(["--fast-debug"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)
    wrapper.archive_stage_dir = tmp_path / "stage"
    wrapper.per_symbol_stage_dir = wrapper.archive_stage_dir / "per_symbol_experiments"
    wrapper.per_symbol_stage_dir.mkdir(parents=True, exist_ok=True)

    experiment_id = "fv3_cached_fresh_tuning_btcusdt_15m_test"
    staged_dir = wrapper.per_symbol_stage_dir / experiment_id
    staged_dir.mkdir(parents=True, exist_ok=True)

    summary_json_path = staged_dir / "feature_regime_experiment_summary.json"
    summary_json_path.write_text(
        json.dumps(
            {
                "symbol": "BTCUSDT",
                "experiment_id": experiment_id,
                "candidate_count": 10,
            }
        ),
        encoding="utf-8",
    )
    summary_markdown_path = staged_dir / "feature_regime_experiment_summary.md"
    summary_markdown_path.write_text("# BTCUSDT summary\n", encoding="utf-8")

    candidate_results_dir = staged_dir / "candidate_results"
    candidate_results_dir.mkdir(parents=True, exist_ok=True)
    candidate_result_path = candidate_results_dir / "lv30_test.json"
    candidate_result_path.write_text(
        json.dumps({"config_id": "lv30_test", "candidate_status": "REJECTED"}),
        encoding="utf-8",
    )
    raw_outputs_dir = staged_dir / "raw_outputs"
    raw_outputs_dir.mkdir(parents=True, exist_ok=True)
    (raw_outputs_dir / "BTCUSDT-run.stdout.json").write_text(
        '{"candidate_results": [1, 2, 3]}',
        encoding="utf-8",
    )
    model_dir = staged_dir / "artifacts" / "models" / "m"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "model.pt").write_bytes(b"model")

    wrapper.run_results = [
        run_fv3_cached_tuning.SymbolRunResult(
            symbol="BTCUSDT",
            mode="fresh_training_runs_from_db_cache",
            experiment_id=experiment_id,
            output_dir=str(staged_dir),
            summary_json_path=str(summary_json_path),
            summary_markdown_path=str(summary_markdown_path),
            candidate_count=10,
            accepted_candidate_count=0,
            rejected_candidate_count=10,
            failed_candidate_count=0,
            exit_code=0,
            started_at="2026-06-27T00:00:00+00:00",
            finished_at="2026-06-27T00:01:00+00:00",
            duration_seconds=60.0,
            stdout_path=str(tmp_path / "stdout.json"),
            stderr_path=str(tmp_path / "stderr.log"),
        )
    ]

    wrapper._stage_selected_runs()

    assert summary_json_path.exists()
    assert summary_markdown_path.exists()
    assert candidate_result_path.exists()
    assert not (raw_outputs_dir / "BTCUSDT-run.stdout.json").exists()
    assert not (model_dir / "model.pt").exists()
    assert wrapper.compact_prune_summaries

    payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    assert payload["symbol"] == "BTCUSDT"
    assert payload["experiment_id"] == experiment_id
    assert payload["summary_payload_compacted"] is True


def test_copy_staging_also_runs_post_copy_compact_prune(tmp_path) -> None:
    args = run_fv3_cached_tuning.parse_args(["--fast-debug"])
    wrapper = run_fv3_cached_tuning.Fv3CachedTuningWrapper(args)
    wrapper.archive_stage_dir = tmp_path / "stage"
    wrapper.per_symbol_stage_dir = wrapper.archive_stage_dir / "per_symbol_experiments"
    wrapper.per_symbol_stage_dir.mkdir(parents=True, exist_ok=True)

    experiment_id = "fv3_cached_fresh_tuning_btcusdt_15m_copy_test"
    source_dir = tmp_path / "source_outputs" / experiment_id
    source_dir.mkdir(parents=True, exist_ok=True)

    summary_json_path = source_dir / "feature_regime_experiment_summary.json"
    summary_json_path.write_text(
        json.dumps(
            {
                "symbol": "BTCUSDT",
                "experiment_id": experiment_id,
                "candidate_count": 10,
            }
        ),
        encoding="utf-8",
    )
    summary_markdown_path = source_dir / "feature_regime_experiment_summary.md"
    summary_markdown_path.write_text("# BTCUSDT summary\n", encoding="utf-8")

    candidate_results_dir = source_dir / "candidate_results"
    candidate_results_dir.mkdir(parents=True, exist_ok=True)
    (candidate_results_dir / "lv30_test.json").write_text(
        json.dumps({"config_id": "lv30_test", "candidate_status": "REJECTED"}),
        encoding="utf-8",
    )
    raw_outputs_dir = source_dir / "raw_outputs"
    raw_outputs_dir.mkdir(parents=True, exist_ok=True)
    (raw_outputs_dir / "BTCUSDT-run.stdout.json").write_text(
        '{"candidate_results": [1, 2, 3]}',
        encoding="utf-8",
    )
    model_dir = source_dir / "artifacts" / "models" / "m"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "model.pt").write_bytes(b"model")

    wrapper.run_results = [
        run_fv3_cached_tuning.SymbolRunResult(
            symbol="BTCUSDT",
            mode="fresh_training_runs_from_db_cache",
            experiment_id=experiment_id,
            output_dir=str(source_dir),
            summary_json_path=str(summary_json_path),
            summary_markdown_path=str(summary_markdown_path),
            candidate_count=10,
            accepted_candidate_count=0,
            rejected_candidate_count=10,
            failed_candidate_count=0,
            exit_code=0,
            started_at="2026-06-27T00:00:00+00:00",
            finished_at="2026-06-27T00:01:00+00:00",
            duration_seconds=60.0,
            stdout_path=str(tmp_path / "stdout_copy.json"),
            stderr_path=str(tmp_path / "stderr_copy.log"),
        )
    ]

    wrapper._stage_selected_runs()

    staged_dir = wrapper.per_symbol_stage_dir / experiment_id
    assert staged_dir.exists()
    assert (staged_dir / "feature_regime_experiment_summary.json").exists()
    assert not (staged_dir / "raw_outputs" / "BTCUSDT-run.stdout.json").exists()
    assert not (staged_dir / "artifacts" / "models" / "m" / "model.pt").exists()
    assert wrapper.compact_prune_summaries
