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


def test_portfolio_limits_cover_count_total_risk_direction_and_correlation():
    arbiter = FutureCrossProfileArbiter()
    existing = (
        ProfileApprovalCandidate("trade-15m-v1", "ETHUSDT", "BULLISH", "a", 25, "BTC_BETA"),
    )
    risk = ProfileApprovalCandidate(
        "trade-5m-v1", "SOLUSDT", "BEARISH", "b", 30, "ALT_BETA"
    )
    assert arbiter.evaluate(
        (risk,), existing_positions=existing, max_total_open_risk_bps=50
    ).decision == CrossProfileDecision.DENY_TOTAL_OPEN_RISK

    correlated = ProfileApprovalCandidate(
        "trade-5m-v1", "SOLUSDT", "BEARISH", "c", 10, "BTC_BETA"
    )
    assert arbiter.evaluate(
        (correlated,), existing_positions=existing
    ).decision == CrossProfileDecision.DENY_CORRELATED_EXPOSURE

    same_direction = ProfileApprovalCandidate(
        "trade-5m-v1", "SOLUSDT", "BULLISH", "d", 10, "ALT_BETA"
    )
    assert arbiter.evaluate(
        (same_direction,), existing_positions=existing,
        max_same_direction_positions=1,
    ).decision == CrossProfileDecision.DENY_SAME_DIRECTION_EXPOSURE

    too_many = ProfileApprovalCandidate(
        "trade-5m-v1", "SOLUSDT", "BEARISH", "e", 10, "ALT_BETA"
    )
    assert arbiter.evaluate(
        (too_many,), existing_positions=existing, max_concurrent_positions=1,
    ).decision == CrossProfileDecision.DENY_MAX_CONCURRENT_POSITIONS
