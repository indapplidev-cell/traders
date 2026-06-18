import run_fv3_cached_tuning
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix


def test_cached_wrapper_expected_candidate_count_matches_fv3_matrix() -> None:
    payload = ML382FV3TuningMatrix().build()
    expected = payload["config_count"] * len(run_fv3_cached_tuning.DEFAULT_SYMBOLS)

    assert run_fv3_cached_tuning.DEFAULT_EXPECTED_CANDIDATE_COUNT == expected
