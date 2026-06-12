import pytest

from app.experiments.label_grid_experiment_runner import (
    LabelGridExperimentConfig,
    LabelGridExperimentRunner,
)
from app.features.feature_models import feature_names_for_version


def test_feature_version_selection_keeps_fv1_backward_compatible_and_supports_fv2() -> None:
    assert feature_names_for_version("fv1")
    assert "return_6" in feature_names_for_version("fv2")

    result = LabelGridExperimentRunner().run(
        LabelGridExperimentConfig(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2025-01-01",
            feature_version="fv2",
            max_configs=1,
            sample_mode=True,
        )
    )

    assert result.feature_version_used == "fv2"


def test_invalid_feature_version_is_rejected_clearly() -> None:
    with pytest.raises(ValueError, match="Unsupported feature_version"):
        feature_names_for_version("fv999")
