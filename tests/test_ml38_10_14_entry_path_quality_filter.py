from app.diagnostics.entry_path_quality_filter import EntryPathQualityFilter


def test_ml38_10_14_entry_path_quality_scores_good_setup_above_bad_setup() -> None:
    filter_ = EntryPathQualityFilter()
    feature_names = [
        "alt_no_trade_chop_score",
        "alt_range_chop_score",
        "alt_false_breakout_risk_score",
        "schwager_trap_safe_setup_score",
    ]
    result = filter_.score_rows(
        feature_names=feature_names,
        feature_rows=[
            [0.10, 0.10, 0.05, 0.80],
            [0.85, 0.80, 0.75, 0.00],
        ],
        setup_quality_scores=[0.85, 0.35],
        expected_move_atr=[1.6, 0.4],
        invalidation_distance_atr=[0.8, 1.4],
    )

    assert result["diagnostic_name"] == "entry_path_quality_filter"
    assert result["diagnostic_version"] == "ml38.10.16"
    assert result["entry_path_quality_scores"][0] > result["entry_path_quality_scores"][1]
    assert result["stop_pressure_risk_scores"][0] < result["stop_pressure_risk_scores"][1]
    assert result["safety"]["uses_realized_mae_mfe_for_filter"] is False
