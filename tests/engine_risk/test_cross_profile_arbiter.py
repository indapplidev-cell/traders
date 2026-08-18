from app.engine_risk.cross_profile_arbiter import (
    CrossProfileDecision,
    FutureCrossProfileArbiter,
    ProfileApprovalCandidate,
)


def candidate(profile, direction="BULLISH"):
    return ProfileApprovalCandidate(profile, "BTCUSDT", direction, f"approval:{profile}")


def test_same_symbol_double_exposure_is_default_denied():
    result = FutureCrossProfileArbiter().evaluate((
        candidate("trade-15m-v1"), candidate("trade-5m-v1"),
    ))
    assert result.decision == CrossProfileDecision.DENY_SAME_SYMBOL_DOUBLE_EXPOSURE
    assert result.automatic_execution_allowed is False


def test_opposite_direction_is_explicit_conflict_and_never_auto_executes():
    result = FutureCrossProfileArbiter().evaluate((
        candidate("trade-15m-v1", "BULLISH"),
        candidate("trade-5m-v1", "BEARISH"),
    ))
    assert result.decision == CrossProfileDecision.CROSS_TIMEFRAME_CONFLICT
    assert result.selected is None and result.automatic_execution_allowed is False


def test_existing_or_planned_exposure_is_shared_and_denied():
    result = FutureCrossProfileArbiter().evaluate(
        (candidate("trade-5m-v1"),),
        symbols_with_existing_or_planned_exposure=frozenset({"BTCUSDT"}),
    )
    assert result.decision == CrossProfileDecision.DENY_SAME_SYMBOL_DOUBLE_EXPOSURE
    assert result.global_account_equity_authority_shared
    assert result.global_open_position_budget_shared
    assert result.global_daily_risk_budget_shared
