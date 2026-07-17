"""Normalized read-only view of analysis fields used by setup rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SetupContext:
    regime: str | None
    confidence: float | None
    action: str | None
    impulse_phase: str | None
    entry_quality: str | None
    reason_codes: tuple[str, ...] = ()
    analysis_context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_analysis_snapshot(cls, snapshot: object) -> "SetupContext":
        action = _upper(getattr(snapshot, "action", None))
        return cls(
            regime=_upper(getattr(snapshot, "regime", None)),
            confidence=getattr(snapshot, "confidence", None),
            action=action if action in {None, "NO_ACTION"} else None,
            impulse_phase=_upper(getattr(snapshot, "impulse_phase", None)),
            entry_quality=_upper(getattr(snapshot, "entry_quality", None)),
            reason_codes=tuple(_upper(value) or "" for value in getattr(snapshot, "reason_codes", ())),
            analysis_context=dict(getattr(snapshot, "analysis_context", {}) or {}),
        )


def _upper(value: object) -> str | None:
    return str(value).upper() if value is not None else None
