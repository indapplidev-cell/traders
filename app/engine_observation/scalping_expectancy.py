"""Outcome-based Scalping expectancy metrics; no admission or trading authority."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ScalpingExpectancy:
    closed_trades: int
    wins: int
    losses: int
    win_probability: float | None
    average_net_win: float | None
    average_net_loss: float | None
    net_expectancy_per_trade: float | None
    observed_trades_per_day: float | None
    net_expectancy_per_day: float | None


def calculate_scalping_expectancy(
    net_pnls: Iterable[float], *, observation_days: float | None
) -> ScalpingExpectancy:
    """Calculate expectancy only from closed outcomes.

    Break-even outcomes are retained in the denominator. Missing outcomes or
    a missing observation duration remain ``None`` rather than becoming zero.
    """
    values = tuple(float(value) for value in net_pnls)
    if any(not isfinite(value) for value in values):
        raise ValueError("net PnL outcomes must be finite")
    if observation_days is not None and (
        not isfinite(float(observation_days)) or float(observation_days) <= 0
    ):
        raise ValueError("observation_days must be positive and finite")

    wins = tuple(value for value in values if value > 0)
    losses = tuple(-value for value in values if value < 0)
    count = len(values)
    if not count:
        return ScalpingExpectancy(0, 0, 0, None, None, None, None, None, None)

    probability = len(wins) / count
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0
    expectancy = probability * average_win - (len(losses) / count) * average_loss
    trades_per_day = count / float(observation_days) if observation_days is not None else None
    return ScalpingExpectancy(
        closed_trades=count,
        wins=len(wins),
        losses=len(losses),
        win_probability=probability,
        average_net_win=average_win,
        average_net_loss=average_loss,
        net_expectancy_per_trade=expectancy,
        observed_trades_per_day=trades_per_day,
        net_expectancy_per_day=(expectancy * trades_per_day if trades_per_day is not None else None),
    )
