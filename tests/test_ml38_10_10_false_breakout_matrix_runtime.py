from __future__ import annotations

from app.experiments.ml38_2_fv3_tuning_matrix import (
    ML382FV3TuningMatrix,
    ML38_10_10_FALSE_BREAKOUT_TRAP_CONFIG_IDS,
    ML38_2_FV3_TUNING_CONFIG_IDS,
    ML38_2_FEATURE_VERSION,
)
from run_fv3_cached_tuning import FAST_DEBUG_CONFIGS, QUICK_QUALITY_CONFIGS


def test_ml38_10_10_configs_are_in_matrix() -> None:
    payload = ML382FV3TuningMatrix().build()
    config_ids = set(payload["config_ids"])

    assert ML38_2_FEATURE_VERSION == "fv4_book_setup_context"
    assert payload["false_breakout_trap_stage"] == "ML38.10.10"
    assert payload["false_breakout_trap_config_count"] == 3

    for config_id in ML38_10_10_FALSE_BREAKOUT_TRAP_CONFIG_IDS:
        assert config_id in ML38_2_FV3_TUNING_CONFIG_IDS
        assert config_id in config_ids


def test_ml38_10_10_runtime_shortlists_keep_lv19_comparator_and_move_current_smoke_to_lv21() -> None:
    assert "lv22_h08_tts_thr065_sqmask060_epq070_sp045" in FAST_DEBUG_CONFIGS
    assert "lv19_h08_tts_thr065_sqmask060" in FAST_DEBUG_CONFIGS

    assert "lv22_h12_tts_thr065_sqmask060_epq070_sp045" in QUICK_QUALITY_CONFIGS
    assert "lv21_h12_tts_thr065_sqmask060_epq070" in QUICK_QUALITY_CONFIGS
    assert "lv19_h12_tts_thr065_sqmask060" in QUICK_QUALITY_CONFIGS
    assert QUICK_QUALITY_CONFIGS[0].startswith("lv31_")
    assert len(QUICK_QUALITY_CONFIGS) == 46
