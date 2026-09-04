from datetime import datetime, timezone
from types import SimpleNamespace

from app.engine_safety.paper_production_control import PersistentState
from app.server_api.runtime import _budget_semantics, _paper_control_status
from app.server_api.schemas.paper import PaperControlStatus


def test_every_continuous_budget_value_declares_unit_source_window_and_reset():
    semantics = _budget_semantics(
        SimpleNamespace(updated_at=datetime(2026, 9, 4, 12, 30, tzinfo=timezone.utc))
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
        "commands", "USDT", "bps", "closed_trades"
    }
    for item in semantics.values():
        assert item["source"]
        assert item["window"] == "UTC_TRADING_DAY"
        assert item["reset_boundary"] == "00:00:00Z"
        assert item["updated_at"] == "2026-09-04T12:30:00Z"


def test_budget_semantics_are_part_of_the_readonly_control_contract():
    semantics = _budget_semantics(
        SimpleNamespace(updated_at=datetime(2026, 9, 4, tzinfo=timezone.utc))
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


def test_risk_pause_is_the_effective_state_while_continuous_authority_persists():
    now = datetime(2026, 9, 4, tzinfo=timezone.utc)
    budget = SimpleNamespace(
        generation=12,
        control_mode="CONTINUOUS",
        control_state="PAUSED_BY_RISK",
        effective_state="PAUSED_BY_RISK",
        mode_version=1,
        budget_day=now.date(),
        daily_command_budget=10,
        commands_used=4,
        daily_realized_loss_budget=1,
        realized_pnl=-1,
        realized_loss=1,
        daily_risk_budget_bps=50,
        risk_used_bps=40,
        max_consecutive_losses=None,
        loss_streak=1,
        pause_reason="DAILY_LOSS_BUDGET_EXHAUSTED",
        updated_at=now,
    )
    control = SimpleNamespace(
        read_authoritative=lambda: SimpleNamespace(
            state=PersistentState.CONTINUOUS_ARMED, generation=12
        )
    )
    status = _paper_control_status(
        control,
        canaries=SimpleNamespace(current=lambda: None),
        continuous=SimpleNamespace(read=lambda: budget),
    )
    assert status.state == "CONTINUOUS_ARMED"
    assert status.effective_state == "PAUSED_BY_RISK"
    assert status.risk_pause_reason == "DAILY_LOSS_BUDGET_EXHAUSTED"
