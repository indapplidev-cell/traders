"""Shadow-only Scalping exit reasons; existing PAPER exit policy is untouched."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ScalpingExitReason(StrEnum):
    NONE = "NONE"
    TAKE_PROFIT = "TAKE_PROFIT"
    CAUSAL_STOP = "CAUSAL_STOP"
    TIME_STOP = "TIME_STOP"
    MOMENTUM_FAILURE = "MOMENTUM_FAILURE"
    STRUCTURE_FAILURE = "STRUCTURE_FAILURE"
    ENTRY_INVALIDATED_BEFORE_FILL = "ENTRY_INVALIDATED_BEFORE_FILL"


@dataclass(frozen=True, slots=True)
class ScalpingExitEvaluation:
    exit_required: bool
    reason: ScalpingExitReason
    holding_minutes: float
    shadow_only: bool = True


def evaluate_scalping_shadow_exit(
    *, filled: bool, entry_still_valid: bool, target_hit: bool,
    causal_stop_hit: bool, momentum_failed: bool, structure_failed: bool,
    holding_time_ms: int, time_stop_minutes: int,
) -> ScalpingExitEvaluation:
    if holding_time_ms < 0 or time_stop_minutes not in {15, 30, 45}:
        raise ValueError("holding time or time-stop cohort is invalid")
    minutes = holding_time_ms / 60_000
    if not filled and not entry_still_valid:
        reason = ScalpingExitReason.ENTRY_INVALIDATED_BEFORE_FILL
    elif not filled:
        reason = ScalpingExitReason.NONE
    elif causal_stop_hit:
        reason = ScalpingExitReason.CAUSAL_STOP
    elif target_hit:
        reason = ScalpingExitReason.TAKE_PROFIT
    elif structure_failed:
        reason = ScalpingExitReason.STRUCTURE_FAILURE
    elif momentum_failed:
        reason = ScalpingExitReason.MOMENTUM_FAILURE
    elif minutes >= time_stop_minutes:
        reason = ScalpingExitReason.TIME_STOP
    else:
        reason = ScalpingExitReason.NONE
    return ScalpingExitEvaluation(reason is not ScalpingExitReason.NONE, reason, minutes)
