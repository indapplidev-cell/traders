from app.evaluation.model_vs_baseline_comparator import ModelVsBaselineComparator


def test_model_vs_baseline_comparator_allows_recommendation_when_model_beats_baseline() -> None:
    comparator = ModelVsBaselineComparator()

    report = comparator.compare(
        model_version="mv2",
        feature_version="fv2_regime",
        label_version="lv_h16_thr03_tp15_sl10",
        walk_forward_summary={
            "global_total_r": 25.0,
            "global_profit_factor": 1.8,
            "global_expectancy_r": 0.25,
            "total_test_signal_count": 120,
            "long_total_count": 65,
            "short_total_count": 55,
            "dominant_class_ratio_max": 0.62,
        },
        baseline_name="ema_9_21_direction",
        baseline_summary={
            "global_total_r": 12.0,
            "global_profit_factor": 1.2,
            "global_expectancy_r": 0.08,
        },
    )

    assert report["recommendation_allowed"] is True
    assert report["model_beats_baseline_by_total_r"] is True
    assert report["model_beats_baseline_by_profit_factor"] is True
    assert report["model_has_both_directions"] is True
    assert report["reject_reasons"] == []


def test_model_vs_baseline_comparator_collects_reject_reasons() -> None:
    comparator = ModelVsBaselineComparator()

    report = comparator.compare(
        model_version="mv3",
        feature_version="fv2_regime",
        label_version="lv_h16_thr03_tp10_sl10",
        walk_forward_summary={
            "global_total_r": 5.0,
            "global_profit_factor": 0.9,
            "global_expectancy_r": -0.01,
            "total_test_signal_count": 10,
            "long_total_count": 10,
            "short_total_count": 0,
            "dominant_class_ratio_max": 0.93,
        },
        baseline_name="ema_9_21_direction",
        baseline_summary={
            "global_total_r": 7.0,
            "global_profit_factor": 1.1,
            "global_expectancy_r": 0.03,
        },
    )

    assert report["recommendation_allowed"] is False
    assert "model_total_r_not_above_baseline" in report["reject_reasons"]
    assert "model_profit_factor_not_above_baseline" in report["reject_reasons"]
    assert "model_expectancy_not_positive" in report["reject_reasons"]
    assert "model_signal_count_lt_50" in report["reject_reasons"]
    assert "no_short_signals" in report["reject_reasons"]
    assert "dominant_class_ratio_gte_0_90" in report["reject_reasons"]
