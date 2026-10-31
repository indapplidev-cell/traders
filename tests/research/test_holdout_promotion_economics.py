from __future__ import annotations

from datetime import datetime, timezone

import pytest

from traders_ml.parameter_sweep import engine
from traders_ml.parameter_sweep.research_protocol import HoldoutAccessPolicy, ResearchPhase


def _policy(params: dict[str, object]) -> HoldoutAccessPolicy:
    candidate = "candidate-1"
    return HoldoutAccessPolicy(
        phase=ResearchPhase.HOLDOUT_EVALUATION,
        freeze_hash="frozen",
        frozen_finalists=frozenset({candidate}),
        finalist_hashes={
            candidate: engine._config_hash({"symbol": "BTCUSDT", "parameters": params})
        },
    )


def _trades(wins: int) -> list[dict[str, object]]:
    start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    return [
        {
            "symbol": "BTCUSDT",
            "net_pnl": 1.0 if index < wins else -0.5,
            "opened_at_ms": start + (index % 5) * 86_400_000,
        }
        for index in range(100)
    ]


@pytest.mark.parametrize(
    ("wins", "profit_factor", "expectancy", "net_pnl", "expected"),
    (
        (51, 1.21, 0.01, 1.0, "PASS"),
        (50, 2.0, 0.10, 10.0, "FAIL"),
        (60, 1.19, 0.10, 10.0, "FAIL"),
        (60, 2.0, 0.0, 10.0, "FAIL"),
        (60, 2.0, 0.10, 0.0, "FAIL"),
    ),
)
def test_holdout_requires_win_rate_profit_factor_and_positive_economics(
    monkeypatch, wins, profit_factor, expectancy, net_pnl, expected,
):
    params: dict[str, object] = {}
    trades = _trades(wins)
    monkeypatch.setattr(engine, "_gate_funnel", lambda rows, values: (list(rows), {}))
    monkeypatch.setattr(
        engine,
        "_time_stop_metrics",
        lambda rows, values, config_hash: {
            "trades": trades,
            "trade_count": len(trades),
            "expectancy_R": expectancy,
            "profit_factor": profit_factor,
            "net_pnl": net_pnl,
            "max_drawdown": 1.0,
        },
    )
    result = engine._evaluate_frozen_holdout(
        params,
        [{"symbol": "BTCUSDT"}],
        finalist_id="candidate-1",
        policy=_policy(params),
        minimum_sample=100,
    )
    assert result["verdict"] == expected
    assert result["win_rate"] == wins / 100
    assert result["promotion_gates"]["minimum_profit_factor"] == 1.2
    assert result["promotion_gates"]["minimum_win_rate_exclusive"] == 0.5


def test_holdout_requires_five_independent_utc_days(monkeypatch):
    params: dict[str, object] = {}
    trades = _trades(60)
    for trade in trades:
        trade["opened_at_ms"] = trades[0]["opened_at_ms"]
    monkeypatch.setattr(engine, "_gate_funnel", lambda rows, values: (list(rows), {}))
    monkeypatch.setattr(
        engine,
        "_time_stop_metrics",
        lambda rows, values, config_hash: {
            "trades": trades,
            "trade_count": 100,
            "expectancy_R": 0.1,
            "profit_factor": 2.0,
            "net_pnl": 10.0,
            "max_drawdown": 1.0,
        },
    )
    result = engine._evaluate_frozen_holdout(
        params,
        [{"symbol": "BTCUSDT"}],
        finalist_id="candidate-1",
        policy=_policy(params),
        minimum_sample=100,
    )
    assert result["period_coverage"] == 1
    assert result["verdict"] == "FAIL"
