import run_fv3_cached_tuning


def test_ml38_6_cached_wrapper_expected_candidate_count_is_60() -> None:
    assert run_fv3_cached_tuning.DEFAULT_EXPECTED_CANDIDATE_COUNT == 60
