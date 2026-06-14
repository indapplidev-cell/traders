import pytest

from app.experiments.feature_regime_experiment_runner import FeatureRegimeExperimentRunner
from app.features.feature_models import feature_names_for_version


def test_ml38_feature_version_fv3_is_registered_and_previewed() -> None:
    names = feature_names_for_version("fv3_candle_ta_context")

    assert "doji_score" in names
    assert "trend_slope_long" in names
    assert "distance_to_support" in names
    assert "bollinger_position" in names
    assert "stochastic_k" in names
    assert "regime_trend_up" in names

    preview = FeatureRegimeExperimentRunner().build_preview()
    assert "fv3_candle_ta_context" in preview["feature_versions_available"]
    assert preview["feature_regime_integration"]["candle_ta_context_features_attached"] is True


def test_ml38_feature_version_keeps_older_versions_and_clear_errors() -> None:
    assert feature_names_for_version("fv1")
    assert feature_names_for_version("fv2")
    assert feature_names_for_version("fv2_regime")

    with pytest.raises(ValueError, match="Unsupported feature_version"):
        feature_names_for_version("fv3_unknown")
