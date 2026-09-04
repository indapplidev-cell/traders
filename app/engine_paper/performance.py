"""Factual PAPER performance telemetry; no policy tuning authority."""

from __future__ import annotations

from decimal import Decimal
from statistics import median
from typing import Mapping, Sequence

from app.engine_paper.accounting import PaperTradeFinancialReport


def scalp_v2_performance(
    reports: Sequence[PaperTradeFinancialReport],
    context: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    selected = tuple(
        report for report in reports
        if context.get(report.position_id, {}).get("trade_profile_id") == "trade-5m-v2"
    )
    pnl = tuple(report.net_pnl for report in selected)
    wins = tuple(value for value in pnl if value > 0)
    losses = tuple(value for value in pnl if value < 0)
    breakeven = sum(value == 0 for value in pnl)
    gross_profit = sum(wins, Decimal("0"))
    gross_loss = -sum(losses, Decimal("0"))
    sample_count = len(selected)
    elapsed_hours = (
        Decimal(str((selected[-1].exit_time - selected[0].entry_time).total_seconds()))
        / Decimal("3600")
        if sample_count > 1 else None
    )
    cumulative = Decimal("0")
    peak = Decimal("0")
    max_drawdown = Decimal("0")
    loss_streak = 0
    max_loss_streak = 0
    for value in pnl:
        cumulative += value
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)
        loss_streak = loss_streak + 1 if value < 0 else 0
        max_loss_streak = max(max_loss_streak, loss_streak)
    avg_win = gross_profit / len(wins) if wins else None
    avg_loss = gross_loss / len(losses) if losses else None
    break_even = (
        avg_loss / (avg_win + avg_loss)
        if avg_win is not None and avg_loss is not None and avg_win + avg_loss > 0
        else None
    )
    holding = tuple(
        Decimal(str((item.exit_time - item.entry_time).total_seconds()))
        for item in selected
    )
    costs_bps = tuple(
        item.total_fees / item.entry_notional * Decimal("10000")
        for item in selected if item.entry_notional > 0
    )
    net_rr = tuple(
        item.net_pnl / Decimal(str(context[item.position_id]["risk_amount"]))
        for item in selected
        if Decimal(str(context[item.position_id].get("risk_amount", "0"))) > 0
    )
    total = sum(pnl, Decimal("0"))
    fees = sum((item.total_fees for item in selected), Decimal("0"))
    gross_pnl = sum(
        (
            getattr(item, "gross_pnl", item.net_pnl + item.total_fees)
            for item in selected
        ),
        Decimal("0"),
    )
    return {
        "profile_id": "trade-5m-v2",
        "profile_version": "v2",
        "observation_status": "OBSERVED" if sample_count else "NO_OBSERVATIONS",
        # The project has no statistically approved sufficiency threshold.
        # Reporting that fact avoids silently turning N into a conclusion.
        "sample_status": "THRESHOLD_NOT_DEFINED",
        "sample_threshold": None,
        "sample_count": sample_count,
        "sample_size": sample_count,
        "closed_trades_count": sample_count,
        "period_start": min((item.entry_time for item in selected), default=None),
        "period_end": max((item.exit_time for item in selected), default=None),
        "wins": len(wins), "losses": len(losses), "breakeven": breakeven,
        "gross_pnl": gross_pnl,
        "fees": fees,
        "net_pnl": total,
        "win_rate": None if not sample_count else Decimal(len(wins)) / sample_count,
        "avg_win": avg_win, "avg_loss": avg_loss,
        "net_expectancy_per_trade": None if not sample_count else total / sample_count,
        "net_expectancy_per_hour": (
            total / elapsed_hours if elapsed_hours is not None and elapsed_hours > 0 else None
        ),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else None,
        "max_drawdown": max_drawdown,
        "max_loss_streak": max_loss_streak,
        "median_holding_time_seconds": None if not holding else Decimal(str(median(holding))),
        "average_cost_bps": None if not costs_bps else sum(costs_bps) / len(costs_bps),
        "average_net_rr": None if not net_rr else sum(net_rr) / len(net_rr),
        "break_even_win_rate": break_even,
        "automatic_rr_retune": False,
        "automatic_conclusion": None,
    }


__all__ = ("scalp_v2_performance",)
