import json
from pathlib import Path

from app.experiments.feature_regime_experiment_runner import (
    FeatureRegimeExperimentConfig,
    FeatureRegimeExperimentRunner,
)


def test_feature_regime_experiment_runner_dry_run_completes_and_creates_paths(tmp_path: Path) -> None:
    result = FeatureRegimeExperimentRunner().run(
        FeatureRegimeExperimentConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            experiment_id="fr_dry_test",
            max_configs=2,
            dry_run=True,
            output_dir=tmp_path,
        )
    )

    payload = result.to_dict()

    assert payload["experiment_status"] == "DRY_RUN_COMPLETED"
    assert payload["config_count"] == 2
    assert payload["candidate_count"] == 2
    assert Path(payload["summary_json_path"]).exists()
    assert Path(payload["summary_markdown_path"]).exists()
    assert (tmp_path / "fr_dry_test" / "diagnostics" / "feature_quality.json").exists()
    assert payload["approved_for_live_trading"] is False
    assert payload["approved_for_auto_activation"] is False
    assert payload["orders_enabled"] is False
    assert payload["traders_core_connected"] is False


def test_feature_regime_experiment_runner_sample_mode_creates_diagnostics_and_candidates(tmp_path: Path) -> None:
    result = FeatureRegimeExperimentRunner().run(
        FeatureRegimeExperimentConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            experiment_id="fr_sample_test",
            max_configs=2,
            sample_mode=True,
            output_dir=tmp_path,
        )
    )

    payload = result.to_dict()
    experiment_dir = tmp_path / "fr_sample_test"

    assert payload["experiment_status"] == "SAMPLE_COMPLETED"
    assert payload["config_count"] == 2
    assert payload["candidate_count"] == 2
    assert (experiment_dir / "diagnostics" / "feature_group_quality.json").exists()
    assert (experiment_dir / "diagnostics" / "regime_feature_diagnostics.json").exists()
    assert (experiment_dir / "diagnostics" / "feature_leakage_guard.json").exists()
    assert (experiment_dir / "diagnostics" / "regime_experiment_plan.json").exists()
    assert any((experiment_dir / "candidate_results").iterdir())
    assert json.dumps(payload)
