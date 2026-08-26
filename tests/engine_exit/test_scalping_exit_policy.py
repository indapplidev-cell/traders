import pytest

from app.engine_exit.scalping_exit_policy import (
    ScalpingExitReason,
    evaluate_scalping_shadow_exit,
)


def evaluate(**changes):
    values = dict(
        filled=True, entry_still_valid=True, target_hit=False,
        causal_stop_hit=False, momentum_failed=False,
        structure_failed=False, holding_time_ms=5 * 60_000,
        time_stop_minutes=30,
    )
    values.update(changes)
    return evaluate_scalping_shadow_exit(**values)


@pytest.mark.parametrize("changes,reason", [
    ({"filled": False, "entry_still_valid": False}, ScalpingExitReason.ENTRY_INVALIDATED_BEFORE_FILL),
    ({"causal_stop_hit": True, "target_hit": True}, ScalpingExitReason.CAUSAL_STOP),
    ({"target_hit": True}, ScalpingExitReason.TAKE_PROFIT),
    ({"structure_failed": True}, ScalpingExitReason.STRUCTURE_FAILURE),
    ({"momentum_failed": True}, ScalpingExitReason.MOMENTUM_FAILURE),
    ({"holding_time_ms": 30 * 60_000}, ScalpingExitReason.TIME_STOP),
])
def test_each_exit_rule_has_an_explicit_independent_reason(changes, reason):
    result = evaluate(**changes)
    assert result.exit_required
    assert result.reason is reason
    assert result.shadow_only


def test_no_rule_does_not_invent_break_even_or_trailing_exit():
    result = evaluate()
    assert result.exit_required is False
    assert result.reason is ScalpingExitReason.NONE
