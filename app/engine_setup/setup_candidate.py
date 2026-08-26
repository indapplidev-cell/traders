"""Stable output model for one setup-discovery window."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

from app.engine_setup.setup_reason_codes import SetupReasonCode
from app.engine_setup.setup_diagnostics import SetupDiagnostics
from app.engine_setup.setup_status import ConfirmationState, DirectionHint, SetupQuality, SetupStatus
from app.engine_setup.setup_type import SetupType
from app.engine_setup.setup_quality_diagnostics import SetupQualityDiagnostics


_QUALITY_RANK = {"GOOD": 0, "ACCEPTABLE": 1, "WEAK": 2, "POOR": 3, "INVALID": 4, "UNKNOWN": 5}


def setup_candidate_id(symbol: str, timeframe: str, closed_until_ms: int, setup_type: str, status: str) -> str:
    identity = f"{symbol.upper()}:{timeframe}:{int(closed_until_ms)}:{setup_type}:{status}"
    digest = sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"setup:{identity}:{digest}"


def clamp_setup_quality(value: str, analysis_quality: str | None) -> str:
    requested = SetupQuality(value).value
    if analysis_quality is None or analysis_quality not in _QUALITY_RANK:
        return SetupQuality.UNKNOWN.value if requested != SetupQuality.INVALID.value else requested
    if _QUALITY_RANK[requested] < _QUALITY_RANK[analysis_quality]:
        return analysis_quality
    return requested


@dataclass(frozen=True, slots=True)
class SetupCandidate:
    setup_id: str
    symbol: str
    timeframe: str
    closed_until_ms: int
    created_at_ms: int
    source_analysis_snapshot_id: str | None = None
    source_regime: str | None = None
    source_confidence: float | None = None
    source_action: str | None = None
    source_impulse_phase: str | None = None
    source_entry_quality: str | None = None
    status: str = SetupStatus.NO_SETUP.value
    setup_type: str = SetupType.NO_SETUP.value
    direction_hint: str = DirectionHint.NONE.value
    confirmation_state: str = ConfirmationState.NOT_APPLICABLE.value
    setup_quality: str = SetupQuality.UNKNOWN.value
    quality_score: float | None = None
    quality_diagnostics: SetupQualityDiagnostics | None = None
    quality_reasons: list[str] = field(default_factory=list)
    quality_warnings: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    invalidation_reasons: list[str] = field(default_factory=list)
    diagnostics: SetupDiagnostics = field(default_factory=SetupDiagnostics)
    context: dict[str, Any] = field(default_factory=dict)
    opportunity_id: str | None = None
    entry_zone: dict[str, float] | None = None
    causal_invalidation: float | None = None
    target_candidates: list[dict[str, Any]] = field(default_factory=list)
    regime: str | None = None
    future_bars_used: bool = field(default=False, init=False)
    is_trade_signal: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        status = SetupStatus(self.status).value
        setup_type = SetupType(self.setup_type).value
        direction = DirectionHint(self.direction_hint).value
        confirmation = ConfirmationState(self.confirmation_state).value
        quality = (self.quality_diagnostics.quality if self.quality_diagnostics is not None
                   else clamp_setup_quality(self.setup_quality, self.source_entry_quality))
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "setup_type", setup_type)
        object.__setattr__(self, "direction_hint", direction)
        object.__setattr__(self, "confirmation_state", confirmation)
        object.__setattr__(self, "setup_quality", quality)
        if self.quality_diagnostics is not None:
            object.__setattr__(self, "quality_score", self.quality_diagnostics.quality_score)
            object.__setattr__(self, "quality_reasons", list(self.quality_diagnostics.quality_reasons))
            object.__setattr__(self, "quality_warnings", list(self.quality_diagnostics.quality_warnings))
        if self.source_action not in {None, "NO_ACTION"}:
            object.__setattr__(self, "source_action", None)
        if not self.setup_id:
            raise ValueError("setup_id must not be empty")
        if self.opportunity_id is not None and not self.opportunity_id.startswith("opportunity:"):
            raise ValueError("opportunity identity is invalid")
        if status == SetupStatus.SETUP_INVALID.value and not self.invalidation_reasons:
            raise ValueError("invalidation_reasons are required for SETUP_INVALID")
        if status == SetupStatus.ERROR.value and SetupReasonCode.SETUP_PROCESSING_ERROR.value not in self.reason_codes:
            raise ValueError("ERROR requires SETUP_PROCESSING_ERROR")
        if status == SetupStatus.SETUP_CANDIDATE.value and quality in {
            SetupQuality.POOR.value, SetupQuality.INVALID.value, SetupQuality.UNKNOWN.value,
        }:
            raise ValueError("SETUP_CANDIDATE quality cannot be POOR or INVALID; UNKNOWN is also forbidden")
        if (status == SetupStatus.WAIT_FOR_CONFIRMATION.value and self.diagnostics.has_structural_trigger
                and quality == SetupQuality.UNKNOWN.value):
            raise ValueError("structural WAIT_FOR_CONFIRMATION quality cannot be UNKNOWN")
