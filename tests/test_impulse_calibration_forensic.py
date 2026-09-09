from scripts.forensic_impulse_calibration import distribution, economics, task_b


def test_distribution_interpolates_requested_quantiles():
    result = distribution(range(1, 101))
    assert result["p10"] == 10.9
    assert result["median"] == 50.5
    assert result["p99"] == 99.01


def test_economics_keeps_non_candidates_out_of_outcome_quality():
    rows = [
        {"candidate_formed": True, "net_outcome_R": 1.0, "net_rr": .8, "required_rr": .6,
         "rr_pass": True, "MFE": 80, "MAE": 10},
        {"candidate_formed": True, "net_outcome_R": -1.0, "net_rr": .4, "required_rr": .6,
         "rr_pass": False, "MFE": 20, "MAE": 50},
        {"candidate_formed": False, "net_outcome_R": 100.0, "rr_pass": True},
    ]
    result = economics(rows, 1)
    assert result["candidate_count"] == 2
    assert result["scoreable_count"] == 2
    assert result["expectancy_R"] == 0
    assert result["PF"] == 1
    assert result["RR_pass_count"] == 1


def test_threshold_provenance_is_15m_legacy_not_a_5m_config_key():
    result = task_b()
    assert result["absolute_threshold"] == 3.0
    assert result["atr_multiplier"] == 2.5
    assert result["config_key"] is None
    assert result["original_timeframe"] == "15m"
    assert result["timeframe_mismatch_found"] is True
    assert result["software_defect_found"] is False
