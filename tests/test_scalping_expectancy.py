import pytest

from app.engine_observation.scalping_expectancy import calculate_scalping_expectancy


def test_expectancy_uses_net_outcomes_and_scales_to_observed_day_rate():
    result = calculate_scalping_expectancy([2.0, 1.0, -1.0, -1.0], observation_days=2)

    assert result.win_probability == 0.5
    assert result.average_net_win == 1.5
    assert result.average_net_loss == 1.0
    assert result.net_expectancy_per_trade == 0.25
    assert result.observed_trades_per_day == 2.0
    assert result.net_expectancy_per_day == 0.5


def test_missing_outcomes_and_duration_are_not_silently_zeroed():
    empty = calculate_scalping_expectancy([], observation_days=None)
    undated = calculate_scalping_expectancy([1.0], observation_days=None)

    assert empty.net_expectancy_per_trade is None
    assert empty.net_expectancy_per_day is None
    assert undated.net_expectancy_per_trade == 1.0
    assert undated.net_expectancy_per_day is None


@pytest.mark.parametrize("days", [0, -1, float("inf")])
def test_invalid_observation_duration_fails_closed(days):
    with pytest.raises(ValueError):
        calculate_scalping_expectancy([1.0], observation_days=days)
