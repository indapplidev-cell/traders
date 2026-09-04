from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.engine_safety.paper_production_control import PersistentState
from app.server_api.runtime import _budget_semantics, _paper_control_status
from app.server_api.schemas.paper import PaperControlStatus
from app.engine_paper.continuous_authority import (
    ContinuousAuthoritySnapshot, PAPER_BUDGET_ENFORCEMENT_MODE,
)


def budget(now, **changes):
    value = dict(
        generation=12, control_mode="CONTINUOUS", control_state="CONTINUOUS_ARMED",
        effective_state="CONTINUOUS_ARMED", mode_version=1, budget_day=now.date(),
        budget_reset_at=now + timedelta(days=1),
        budget_policy_version="scalping-v2-continuous-paper-statistics-v2",
        budget_policy_source="USER_AUTHORIZED_VIRTUAL_PAPER_STATISTICS_POLICY",
        budget_enforcement_mode=PAPER_BUDGET_ENFORCEMENT_MODE,
        daily_command_budget_unit="trade_count",
        daily_risk_budget_unit="equity_basis_points",
        daily_realized_loss_budget_unit="USDT", loss_streak_unit="closed_trade_count",
        daily_command_budget=10, commands_used=4, daily_realized_loss_budget=1,
        realized_pnl=-1, realized_loss=1, daily_risk_budget_bps=50,
        risk_used_bps=40, max_consecutive_losses=None, loss_streak=1,
        pause_reason=None, updated_at=now,
    )
    value.update(changes)
    return SimpleNamespace(**value)


def test_every_continuous_budget_value_declares_unit_source_window_and_reset():
    semantics = _budget_semantics(
        budget(datetime(2026, 9, 4, 12, 30, tzinfo=timezone.utc))
    )
    assert set(semantics) == {
        "daily_command_budget",
        "commands_used_today",
        "daily_realized_loss_budget",
        "realized_pnl_today",
        "realized_loss_today",
        "daily_risk_budget_bps",
        "risk_used_today_bps",
        "max_consecutive_losses",
        "loss_streak",
    }
    assert {item["unit"] for item in semantics.values()} == {
        "trade_count", "USDT", "equity_basis_points", "closed_trade_count"
    }
    for item in semantics.values():
        assert item["source"]
        assert item["window"] == "UTC_TRADING_DAY"
        assert item["reset_boundary"] == "00:00:00Z"
        assert item["updated_at"] == "2026-09-04T12:30:00Z"


def test_budget_semantics_are_part_of_the_readonly_control_contract():
    semantics = _budget_semantics(
        budget(datetime(2026, 9, 4, tzinfo=timezone.utc))
    )
    model = PaperControlStatus(
        state="CONTINUOUS_ARMED",
        effective_state="CONTINUOUS_ARMED",
        generation=12,
        health="HEALTHY",
        emergency_stop_available=True,
        audit_health="PASS",
        state_audit_reconciliation="PASS",
        authority_mode="CONTINUOUS",
        budget_semantics=semantics,
    )
    assert model.model_dump(mode="json")["budget_semantics"] == semantics


def test_paper_statistics_policy_exposes_no_limits_and_never_computes_pause():
    now = datetime(2026, 9, 4, tzinfo=timezone.utc)
    current = budget(
        now, commands_used=100, realized_loss=999, risk_used_bps=999,
    )
    assert ContinuousAuthoritySnapshot.budget_reason.fget(current) is None
    control = SimpleNamespace(
        read_authoritative=lambda: SimpleNamespace(
            state=PersistentState.CONTINUOUS_ARMED, generation=12
        )
    )
    status = _paper_control_status(
        control,
        canaries=SimpleNamespace(current=lambda: None),
        continuous=SimpleNamespace(read=lambda: current),
    )
    assert status.state == "CONTINUOUS_ARMED"
    assert status.effective_state == "CONTINUOUS_ARMED"
    assert status.risk_pause is False
    assert status.risk_pause_reason is None
    assert status.daily_command_budget_value == 100
    assert status.daily_command_budget_limit is None
    assert status.daily_risk_limit is None
    assert status.daily_realized_loss_limit is None
    assert status.daily_command_budget_unit == "trade_count"
    assert status.daily_risk_unit == "equity_basis_points"
    assert status.daily_realized_loss_unit == "USDT"
    assert status.risk_per_trade_value == "10.0"
    assert status.risk_per_trade_unit == "equity_basis_points"
    assert status.risk_per_trade_source == (
        "SCALPING_V2_RUNTIME_PARAMETERS/risk_per_trade_bps"
    )
    assert "net_pnl < 0" in status.daily_loss_formula
    assert "UNIQUE(command_id)" in status.daily_risk_formula
    assert status.daily_command_budget is None
    assert status.daily_risk_budget_bps is None
    assert status.daily_realized_loss_budget is None


def test_future_real_money_policy_retains_exact_limit_comparisons():
    now = datetime(2026, 9, 4, tzinfo=timezone.utc)
    limited = budget(
        now, budget_enforcement_mode="REAL_MONEY_LIMITED",
        commands_used=4, realized_loss=1, daily_realized_loss_budget=1,
    )
    assert ContinuousAuthoritySnapshot.budget_reason.fget(limited) == (
        "DAILY_LOSS_BUDGET_EXHAUSTED"
    )
