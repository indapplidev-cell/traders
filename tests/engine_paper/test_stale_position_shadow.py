from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.engine_paper.stale_position_shadow import (
    StalePositionInputs,
    TIME_STOP_SHADOW_BREAK_EVEN_PROTECT,
    TIME_STOP_SHADOW_EXTENSION_ALLOWED,
    TIME_STOP_SHADOW_HARD_LIMIT,
    TIME_STOP_SHADOW_NO_PROGRESS,
    evaluate_stale_position_shadow,
    stale_position_capability,
)


NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


def inputs(**overrides):
    values = dict(
        position_id="position-1", symbol="BTCUSDT", side="LONG",
        opened_at=NOW, evaluation_time=NOW + timedelta(minutes=5),
        evaluation_closed_until_ms=int((NOW + timedelta(minutes=5)).timestamp() * 1000),
        entry_price=Decimal("100"), current_price=Decimal("100.5"),
        quantity=Decimal("1"), stop_price=Decimal("99"), target_price=Decimal("102"),
        entry_fee_incurred=Decimal("0.09"), exit_commission_bps=Decimal("9"),
        spread_bps=Decimal("2"), slippage_bps=Decimal("2"),
        adverse_exit_reserve_bps=Decimal("3"),
        highs=(Decimal("100.8"),), lows=(Decimal("99.8"),),
        setup_valid=True, momentum_valid=True,
    )
    values.update(overrides)
    return StalePositionInputs(**values)


def test_long_and_short_net_exit_math_includes_all_current_costs():
    long = evaluate_stale_position_shadow(inputs())
    assert long.current_gross_pnl == Decimal("0.5")
    assert long.expected_exit_commission == Decimal("0.09045")
    assert long.spread_cost == Decimal("0.0201")
    assert long.slippage_cost == Decimal("0.0201")
    assert long.adverse_exit_reserve == Decimal("0.03015")
    assert long.estimated_net_exit_pnl == Decimal("0.24920")
    assert long.net_break_even_price > Decimal("100.09")

    short = evaluate_stale_position_shadow(inputs(
        side="SHORT", current_price=Decimal("99.5"), stop_price=Decimal("101"),
        target_price=Decimal("98"), highs=(Decimal("100.2"),), lows=(Decimal("99.2"),),
    ))
    assert short.current_gross_pnl == Decimal("0.5")
    assert short.mfe_bps == Decimal("80.000")
    assert short.mae_bps == Decimal("20.000")
    assert short.net_break_even_price < Decimal("99.91")


def test_restart_safe_holding_age_uses_authoritative_opened_at():
    first = evaluate_stale_position_shadow(inputs(
        evaluation_time=NOW + timedelta(seconds=599)
    ))
    restarted = evaluate_stale_position_shadow(inputs(
        evaluation_time=NOW + timedelta(seconds=600)
    ))
    assert first.holding_seconds == 599 and not first.soft_timeout_reached
    assert restarted.holding_seconds == 600 and restarted.soft_timeout_reached


def test_soft_timeout_extension_then_hard_hypothetical_exit_without_mutation():
    source = inputs(
        evaluation_time=NOW + timedelta(seconds=600), current_price=Decimal("100.1"),
        highs=(Decimal("100.2"),), lows=(Decimal("99.9"),),
    )
    extended = evaluate_stale_position_shadow(source)
    assert extended.shadow_decision == "EXTENSION_ALLOWED"
    assert extended.decision_reason == TIME_STOP_SHADOW_EXTENSION_ALLOWED
    assert extended.extension_count == 1 and extended.shadow_exit_time is None

    hard = evaluate_stale_position_shadow(replace(
        source, evaluation_time=NOW + timedelta(seconds=900), extension_count=1,
    ))
    assert hard.hard_timeout_reached
    assert hard.shadow_decision == "HYPOTHETICAL_EXIT"
    assert hard.shadow_exit_reason == TIME_STOP_SHADOW_HARD_LIMIT
    assert source.position_id == hard.position_id


def test_no_progress_and_net_break_even_protection_are_cost_aware():
    no_progress = evaluate_stale_position_shadow(inputs(
        evaluation_time=NOW + timedelta(seconds=600), current_price=Decimal("100.1"),
        setup_valid=False, momentum_valid=False,
    ))
    assert no_progress.shadow_exit_reason == TIME_STOP_SHADOW_NO_PROGRESS

    break_even = evaluate_stale_position_shadow(inputs(
        evaluation_time=NOW + timedelta(seconds=500), current_price=Decimal("101"),
        entry_fee_incurred=Decimal("1"), exit_commission_bps=Decimal("100"),
        spread_bps=Decimal("10"), slippage_bps=Decimal("10"),
        adverse_exit_reserve_bps=Decimal("10"),
    ))
    assert break_even.target_progress == Decimal("0.5")
    assert break_even.estimated_net_exit_pnl < 0
    assert break_even.shadow_exit_reason == TIME_STOP_SHADOW_BREAK_EVEN_PROTECT
    assert break_even.break_even_activation_reason == "TARGET_PROGRESS_THRESHOLD_REACHED"


def test_central_capability_is_runtime_active_shadow_and_live_neutral():
    capability = stale_position_capability()
    assert capability["runtime_active"] is True
    assert capability["mode"] == "SHADOW"
    assert capability["policy"]["soft_timeout_seconds"] == 600
    assert capability["policy"]["hard_timeout_seconds"] == 900
    assert "live" not in capability
