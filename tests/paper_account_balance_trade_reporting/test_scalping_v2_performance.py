from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.engine_paper.performance import scalp_v2_performance


def _report(identity: str, pnl: str, fee: str, minute: int):
    entry = datetime(2026, 9, 4, 12, minute, tzinfo=timezone.utc)
    return SimpleNamespace(
        position_id=identity,
        net_pnl=Decimal(pnl),
        total_fees=Decimal(fee),
        entry_notional=Decimal("100"),
        entry_time=entry,
        exit_time=entry + timedelta(minutes=10),
    )


def test_scalping_v2_expectancy_is_factual_and_profile_isolated() -> None:
    reports = (
        _report("win", "0.40", "0.20", 0),
        _report("loss", "-0.30", "0.20", 20),
        _report("legacy", "99", "0", 40),
    )
    context = {
        "win": {"trade_profile_id": "trade-5m-v2", "risk_amount": "0.20"},
        "loss": {"trade_profile_id": "trade-5m-v2", "risk_amount": "0.20"},
        "legacy": {"trade_profile_id": "trade-5m-v1", "risk_amount": "1"},
    }
    value = scalp_v2_performance(reports, context)
    assert value["sample_count"] == 2
    assert value["sample_size"] == value["closed_trades_count"] == 2
    assert (value["wins"], value["losses"], value["breakeven"]) == (1, 1, 0)
    assert value["win_rate"] == Decimal("0.5")
    assert value["net_expectancy_per_trade"] == Decimal("0.05")
    assert value["profit_factor"] == Decimal("1.333333333333333333333333333")
    assert value["max_drawdown"] == Decimal("0.30")
    assert value["max_loss_streak"] == 1
    assert value["median_holding_time_seconds"] == Decimal("600")
    assert value["average_cost_bps"] == Decimal("20")
    assert value["average_net_rr"] == Decimal("0.25")
    assert value["break_even_win_rate"] == Decimal("0.4285714285714285714285714286")
    assert value["automatic_rr_retune"] is False
    assert value["sample_status"] == "THRESHOLD_NOT_DEFINED"
    assert value["sample_threshold"] is None
    assert value["automatic_conclusion"] is None
    assert value["gross_pnl"] == Decimal("0.50")
    assert value["fees"] == Decimal("0.40")
    assert value["net_pnl"] == Decimal("0.10")
    assert value["period_start"] == reports[0].entry_time
    assert value["period_end"] == reports[1].exit_time


def test_empty_sample_is_explicit_and_never_claims_profitability() -> None:
    value = scalp_v2_performance((), {})
    assert value["sample_count"] == 0
    assert value["observation_status"] == "NO_OBSERVATIONS"
    assert value["sample_status"] == "THRESHOLD_NOT_DEFINED"
    assert value["net_expectancy_per_trade"] is None
    assert value["profit_factor"] is None
