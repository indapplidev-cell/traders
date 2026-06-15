from app.experiments.ml38_2_1_wrapper_manifest import (
    build_ml38_2_1_wrapper_manifest,
    validate_reusable_symbol_summary,
)


def test_wrapper_manifest_success_flags_are_explicit() -> None:
    payload = build_ml38_2_1_wrapper_manifest(
        branch="ml38-2-1-fresh-grid-orchestration-gap-gate",
        archive_path="reports/feature_regime_experiments/ml38_2_1.zip",
        archive_stage_dir="reports/feature_regime_experiments/ml38_2_1",
        manifest_path="reports/feature_regime_experiments/ml38_2_1/archive_manifest.json",
        script_path="D:/disk_E/game_projects/traders/run_ml38_2_fv3_tuning_btc_eth_sol.ps1",
        source_mode="reuse_existing_symbol_results",
        wrapper_completed_end_to_end=True,
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        symbols_completed=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        failed_symbols=[],
        run_results=[{"symbol": "BTCUSDT", "exit_code": 0}],
        multi_symbol_result={
            "candidate_count": 24,
            "accepted_candidate_count": 0,
            "rejected_candidate_count": 24,
        },
        included_files=["archive_manifest.json", "multi_symbol_feature_regime_analysis.json"],
    )

    assert payload["stage"] == "ML38.2.1"
    assert payload["wrapper_completed_end_to_end"] is True
    assert payload["manual_archive_assembly_used"] is False
    assert payload["fresh_grid_archive_created_by_wrapper"] is True
    assert payload["source_mode"] == "reuse_existing_symbol_results"


def test_wrapper_manifest_failed_case_tracks_failed_symbols() -> None:
    payload = build_ml38_2_1_wrapper_manifest(
        branch="ml38-2-1-fresh-grid-orchestration-gap-gate",
        archive_path="reports/feature_regime_experiments/ml38_2_1_failed.zip",
        archive_stage_dir="reports/feature_regime_experiments/ml38_2_1_failed",
        manifest_path="reports/feature_regime_experiments/ml38_2_1_failed/archive_manifest.json",
        script_path="D:/disk_E/game_projects/traders/run_ml38_2_fv3_tuning_btc_eth_sol.ps1",
        source_mode="fresh_training_runs",
        wrapper_completed_end_to_end=False,
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        symbols_completed=["BTCUSDT", "ETHUSDT"],
        failed_symbols=["SOLUSDT"],
        run_results=[{"symbol": "SOLUSDT", "exit_code": 1}],
        multi_symbol_result=None,
        included_files=["archive_manifest.json"],
    )

    assert payload["wrapper_completed_end_to_end"] is False
    assert payload["failed_symbols"] == ["SOLUSDT"]
    assert payload["manual_archive_assembly_used"] is False


def test_reuse_validation_requires_real_fv3_regime_outputs() -> None:
    payload = validate_reusable_symbol_summary(
        {
            "feature_version_used": "fv3_candle_ta_context",
            "candle_ta_context_features_attached": True,
            "real_feature_diagnostics_used": True,
            "regime_features_attached": True,
            "model_quality_validation_status": "COMPLETED",
            "configs_ranked": [{"config_id": "lv2_h08_thr03_tp10_sl10"}],
            "best_candidate_config_id": "lv2_h08_thr03_tp10_sl10",
        }
    )

    assert payload["reusable"] is True
    assert payload["issues"] == []
