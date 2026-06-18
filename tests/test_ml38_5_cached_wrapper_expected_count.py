import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML38_2_FV3_TUNING_CONFIG_IDS


def test_cached_wrapper_expected_candidate_count_matches_current_full_matrix() -> None:
    expected = len(run_fv3_cached_tuning.DEFAULT_SYMBOLS) * len(ML38_2_FV3_TUNING_CONFIG_IDS)

    assert len(ML38_2_FV3_TUNING_CONFIG_IDS) == 28
    assert run_fv3_cached_tuning.DEFAULT_FULL_GRID_CONFIG_COUNT == 28
    assert run_fv3_cached_tuning.DEFAULT_EXPECTED_CANDIDATE_COUNT == expected
    assert run_fv3_cached_tuning.DEFAULT_EXPECTED_CANDIDATE_COUNT == 84
