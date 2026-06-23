from app.diagnostics.entry_path_quality_filter import EntryPathQualityFilter
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
import run_fv3_cached_tuning


def test_ml38_10_15_directional_context_profile_rewards_aligned_long_setup() -> None:
    filter_ = EntryPathQualityFilter()
    feature_names = [
        "alt_pullback_long_score",
        "alt_indicator_confluence_long_score",
        "nison_expected_followthrough_score",
        "schwager_invalidation_quality_score",
        "alt_no_trade_chop_score",
        "schwager_bull_trap_risk_score",
        "path_12_upper_wick_pressure",
        "volume_16_exhaustion_score",
    ]

    result = filter_.score_rows(
        feature_names=feature_names,
        feature_rows=[
            [0.85, 0.80, 0.75, 0.70, 0.10, 0.05, 0.10, 0.05],
            [0.05, 0.05, 0.10, 0.10, 0.70, 0.90, 0.85, 0.70],
        ],
        setup_quality_scores=[0.80, 0.45],
        expected_move_atr=[1.4, 0.6],
        invalidation_distance_atr=[0.8, 1.2],
        predicted_labels=["UP", "UP"],
        score_profile="directional_context_v2",
    )

    assert result["diagnostic_version"] == "ml38.10.15"
    assert result["score_profile"] == "directional_context_v2"
    first, second = result["score_rows"]
    assert first["entry_path_quality_score"] > second["entry_path_quality_score"]
    assert first["stop_pressure_risk_score"] < second["stop_pressure_risk_score"]
    assert first["direction_alignment_score"] > second["direction_alignment_score"]
    assert second["direction_opposition_risk_score"] > first["direction_opposition_risk_score"]


def test_ml38_10_15_matrix_and_runtime_include_lv23_configs() -> None:
    payload = ML382FV3TuningMatrix().build()
    config_ids = {item["config_id"] for item in payload["configs"]}

    assert "lv23_h08_tts_thr065_sqmask060_epq065_sp050_eff" in config_ids
    assert "lv23_h12_tts_thr065_sqmask060_epq065_sp050_eff" in config_ids
    assert "lv23_h12_tts_thr065_sqmask060_epq068_sp047_eff" in config_ids
    assert payload["entry_path_effectiveness_tuning_stage"] == "ML38.10.15"
    assert run_fv3_cached_tuning.FAST_DEBUG_CONFIGS[0].startswith("lv23_")
    assert run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS[0].startswith("lv23_")
