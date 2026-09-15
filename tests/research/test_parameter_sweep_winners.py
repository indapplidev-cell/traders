from __future__ import annotations

from types import SimpleNamespace

from traders_ml.parameter_sweep.controller import ParameterSweepController, PresentationState
from traders_ml.parameter_sweep.ui import format_positive_winner_card, format_win_count_card
from traders_ml.parameter_sweep.winners import (
    METRIC_FIELDS, WinnerTracker, search_incumbents,
)


def row(
    config_id: str, *, net: float, wins: int, losses: int = 0,
    expectancy: float | None = 0.1, pf: float | None = 1.2,
    drawdown: float = 1.0, trades: int | None = None,
    behavior: str | None = None, eligible: bool = False,
    parameters: dict | None = None,
):
    count = trades if trades is not None else wins + losses
    return {
        "config_id": config_id,
        "config_index": int(config_id.strip("c") or 0),
        "parameters": parameters or {"p": config_id},
        "behavioral_signature": behavior or f"behavior-{config_id}",
        "trade_count": count,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / count if count else None,
        "gross_pnl": net + 0.4,
        "fees": 0.3,
        "slippage": 0.1,
        "net_pnl": net,
        "expectancy_R": expectancy,
        "profit_factor": pf,
        "max_drawdown": drawdown,
        "avg_win": 1.5,
        "avg_loss": 0.75,
        "avg_holding_time": 42.0,
        "independent_period_count": 2,
        "symbol_coverage": 1,
        "performance_class": "VALIDATION_CANDIDATE" if eligible else "INSUFFICIENT_SAMPLE",
        "promotion_eligible": eligible,
    }


def test_positive_pnl_winner_and_higher_net_pnl_are_selected():
    tracker = WinnerTracker.from_rows([
        row("c1", net=1.0, wins=2), row("c2", net=2.0, wins=1),
    ])
    assert tracker.best_positive_net_pnl["config_id"] == "c2"
    assert tracker.best_net_pnl_fallback["config_id"] == "c2"


def test_positive_equal_net_uses_expectancy_pf_drawdown_and_config_id_ties():
    rows = [
        row("c1", net=2, wins=2, expectancy=0.1, pf=4, drawdown=0.1),
        row("c2", net=2, wins=2, expectancy=0.2, pf=1, drawdown=9),
        row("c3", net=2, wins=2, expectancy=0.2, pf=2, drawdown=3),
        row("c4", net=2, wins=2, expectancy=0.2, pf=2, drawdown=1),
        row("c5", net=2, wins=2, expectancy=0.2, pf=2, drawdown=1),
    ]
    assert WinnerTracker.from_rows(rows).best_positive_net_pnl["config_id"] == "c5"


def test_win_count_winner_and_equal_wins_use_net_pnl():
    tracker = WinnerTracker.from_rows([
        row("c1", net=10, wins=3), row("c2", net=-5, wins=7, losses=10),
        row("c3", net=-2, wins=7, losses=10),
    ])
    assert tracker.best_win_count["config_id"] == "c3"
    assert tracker.best_win_count["net_pnl"] == -2


def test_high_win_negative_pnl_remains_visible_and_not_profitable():
    state = PresentationState()
    state.best_win_count_config = WinnerTracker.from_rows([
        row("c7", net=-8, wins=14, losses=62),
    ]).best_win_count
    text = format_win_count_card(state)
    assert "Побед: 14" in text
    assert "Поражений: 62" in text
    assert "Net PnL: -8" in text
    assert "Экономический результат: ОТРИЦАТЕЛЬНЫЙ" in text


def test_no_positive_keeps_best_net_pnl_fallback():
    tracker = WinnerTracker.from_rows([
        row("c1", net=-5, wins=2), row("c2", net=-1, wins=1),
    ])
    artifact = tracker.artifact(
        symbol="DOGEUSDT", profile="trade-5m-v2", search_budget=2,
        search_status="COMPLETED",
    )
    assert artifact["positive_net_pnl_found"] is False
    assert artifact["best_positive_net_pnl"] is None
    assert artifact["best_net_pnl_fallback"]["config_id"] == "c2"


def test_validation_eligibility_does_not_hide_research_winners():
    tracker = WinnerTracker.from_rows([row("c1", net=3, wins=2, eligible=False)])
    assert tracker.best_positive_net_pnl["validation_status"] == "INSUFFICIENT_SAMPLE"
    assert tracker.best_positive_net_pnl["promotion_eligible"] is False


def test_winner_updates_streaming_and_controller_projects_event():
    tracker = WinnerTracker()
    tracker.update(row("c1", net=-2, wins=1))
    tracker.update(row("c2", net=4, wins=2))
    artifact = tracker.artifact(
        symbol="SUIUSDT", profile="trade-5m-v2", search_budget=10,
        search_status="RUNNING",
    )
    controller = ParameterSweepController.__new__(ParameterSweepController)
    controller.state = PresentationState()
    controller._apply_pipeline_progress({
        "progress_sequence": 1, "phase": "EXPANDED_AUTOMATIC_SEARCH",
        "event_type": "CONFIG_COMPLETED", "config_index": 2,
        "parameters": {"p": 2}, "best_configs": artifact,
        "evaluated_count": 2, "planned_total": 10,
    })
    assert controller.state.best_positive_net_pnl_config["config_id"] == "c2"
    assert controller.state.search_evaluated == 2
    assert controller.state.search_status == "RUNNING"


def test_resume_restores_incumbents_without_evaluated_rows():
    original = WinnerTracker.from_rows([row("c1", net=4, wins=3)])
    restored = WinnerTracker.restore(original.state())
    assert restored.state() == original.state()
    restored.update(row("c2", net=5, wins=2))
    assert restored.best_positive_net_pnl["config_id"] == "c2"


def test_numeric_aliases_deduplicate_to_deterministic_behavioral_representative():
    tracker = WinnerTracker.from_rows([
        row("c1", net=2, wins=2, behavior="same"),
        row("c9", net=2, wins=2, behavior="same"),
    ])
    assert tracker.best_positive_net_pnl["behavioral_cluster_id"] == "same"
    assert tracker.best_positive_net_pnl["numeric_config_id"] == "c9"
    assert tracker.best_positive_net_pnl["numeric_alias_count"] == 2


def test_dynamic_n_dimensional_parameters_and_full_metrics_serialize():
    parameters = {f"dimension_{index}": index / 10 for index in range(12)}
    winner = WinnerTracker.from_rows([
        row("c1", net=2, wins=2, parameters=parameters),
    ]).best_positive_net_pnl
    assert winner["parameters"] == parameters
    assert all(field in winner for field in METRIC_FIELDS)


def test_deterministic_winners_are_independent_of_batch_order():
    rows = [
        row("c1", net=2, wins=3), row("c2", net=2, wins=3),
        row("c3", net=-1, wins=8, losses=9),
    ]
    forward = WinnerTracker.from_rows(rows).state()
    reverse = WinnerTracker.from_rows(reversed(rows)).state()
    assert forward == reverse


def test_gui_positive_card_renders_full_metrics_and_fallback():
    tracker = WinnerTracker.from_rows([row("c1", net=-1, wins=4, losses=5)])
    state = SimpleNamespace(
        positive_net_pnl_found=False, best_positive_net_pnl_config=None,
        best_net_pnl_config=tracker.best_net_pnl_fallback,
    )
    text = format_positive_winner_card(state)
    for expected in (
        "Положительная прибыль не найдена", "Лучший Net PnL", "Config ID: c1",
        "Gross PnL", "Fees", "Slippage", "Expectancy R", "Profit Factor",
        "Max Drawdown", "Independent periods", "dimension",
    ):
        if expected != "dimension":
            assert expected in text


def test_search_incumbents_are_distinct_and_keep_win_count_analytical():
    tracker = WinnerTracker.from_rows([
        row("c1", net=5, wins=2, behavior="profit"),
        row("c2", net=-4, wins=9, losses=12, behavior="wins"),
    ])
    parents = search_incumbents(tracker.state(), row("c3", net=1, wins=1, behavior="balanced"))
    assert [parent["incumbent_role"] for parent in parents] == [
        "BEST_POSITIVE_NET_PNL_CONFIG", "BEST_WIN_COUNT_CONFIG", "BEST_BALANCED_CONFIG",
    ]
    assert parents[1]["net_pnl"] == -4


def test_streaming_tracker_does_not_retain_evaluated_dataset():
    tracker = WinnerTracker()
    for index in range(10_000):
        tracker.update(row(f"c{index}", net=float(index), wins=index % 7))
    assert not hasattr(tracker, "rows")
    assert set(tracker.__slots__) == {
        "evaluated", "best_positive_net_pnl", "best_net_pnl_fallback", "best_win_count",
    }
