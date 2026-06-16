import run_fv3_cached_tuning


def test_ml38_5_cached_wrapper_expected_candidate_count_is_42() -> None:
    assert run_fv3_cached_tuning.DEFAULT_EXPECTED_CANDIDATE_COUNT == 42
