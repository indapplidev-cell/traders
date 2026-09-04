from datetime import datetime, timezone
from types import SimpleNamespace

from app.server_api.runtime import _budget_semantics
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
