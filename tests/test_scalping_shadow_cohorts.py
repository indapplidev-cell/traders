import pytest

from app.engine_observation.scalping_shadow_cohorts import (
    SCALPING_SHADOW_FACTORS,
    isolated_cohorts,
)


def test_all_required_factors_are_declared_and_each_cohort_changes_one_factor():
    base = {name: values[-1] for name, values in SCALPING_SHADOW_FACTORS.items()}
    for factor in SCALPING_SHADOW_FACTORS:
        cohorts = isolated_cohorts(base, factor=factor)
        assert len(cohorts) == len(SCALPING_SHADOW_FACTORS[factor])
        for cohort in cohorts:
            differences = {
                key for key in base if cohort.parameters[key] != base[key]
            }
            assert differences <= {factor}
            assert cohort.execution_eligible is False
            assert cohort.mutates_production_trading_state is False


def test_undeclared_or_missing_factor_fails_closed():
    with pytest.raises(ValueError):
        isolated_cohorts({}, factor="minimum_rr")
    with pytest.raises(ValueError):
        isolated_cohorts({"unknown": 1}, factor="unknown")
