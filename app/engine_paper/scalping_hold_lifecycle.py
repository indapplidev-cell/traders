"""Authoritative, causal hold revalidation for an open Scalping v2 PAPER position.

The 5m pipeline owns entry thesis creation.  This module only revalidates that
persisted thesis on each closed 1m boundary with the existing canonical
analysis engine.  It never creates a new setup or changes entry eligibility.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
from typing import Callable, Iterable, Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.trade_parameters import SCALPING_V2, TRADE_PARAMETERS
from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperOrderRecord,
    ScalpingPositionHoldDecisionRecord,
)
from app.engine_analysis import AnalysisWindowConfig, EngineAnalysisCandle, run_engine_analysis
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow
from app.engine_paper.fill_simulator import PaperFillCandle
from app.engine_position.paper_models import PaperPosition


POLICY_VERSION = "scalping-hold-lifecycle-v1"


class HoldValidity(StrEnum):
    VALID = "VALID"
    INVALIDATED = "INVALIDATED"
    REVERSED = "REVERSED"
    STALE = "STALE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    ERROR = "ERROR"


class HoldLifecycleState(StrEnum):
    FRESH = "FRESH"
    AT_RISK = "AT_RISK"
    STALE = "STALE"
    EXTENSION_ALLOWED = "EXTENSION_ALLOWED"
    EXTENSION_EXHAUSTED = "EXTENSION_EXHAUSTED"
    FORCE_EXIT = "FORCE_EXIT"


class HoldExitReason(StrEnum):
    MOMENTUM_INVALIDATED = "MOMENTUM_INVALIDATED"
    MOMENTUM_REVERSAL = "MOMENTUM_REVERSAL"
    STRUCTURE_INVALIDATED = "STRUCTURE_INVALIDATED"
    SETUP_INVALIDATED = "SETUP_INVALIDATED"
    STALE_SCALP = "STALE_SCALP"
    MAX_HOLD_TIME = "MAX_HOLD_TIME"


@dataclass(frozen=True, slots=True)
class ScalpingEntryThesis:
    pipeline_run_id: str
    profile: str
    setup_type: str
    direction: str
    signal_closed_until_ms: int
    entry_closed_until_ms: int
    entry_regime: str | None
    entry_impulse_phase: str | None
    setup_id: str
    config_hash: str


@dataclass(frozen=True, slots=True)
class CanonicalHoldEvidence:
    boundary_ms: int
    regime: str | None
    structure_direction: str | None
    impulse_phase: str | None
    entry_quality: str | None
    confidence: float | None
    engine_status: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScalpingHoldDecision:
    position_id: str
    boundary_ms: int
    evaluated_at: datetime
    holding_seconds: int
    validity: HoldValidity
    lifecycle_state: HoldLifecycleState
    exit_reason: HoldExitReason | None
    extension_count: int
    extension_until_ms: int | None
    thesis: ScalpingEntryThesis
    evidence: CanonicalHoldEvidence

    @property
    def force_exit(self) -> bool:
        return self.lifecycle_state is HoldLifecycleState.FORCE_EXIT


_CONTINUATION_SETUPS = frozenset({
    "SCALP_TREND_PULLBACK", "SCALP_BREAKOUT", "SCALP_BREAKOUT_RETEST",
    "SCALP_MOMENTUM_CONTINUATION", "SCALP_COMPRESSION_BREAK",
    "TREND_CONTINUATION", "BREAKOUT_CONTINUATION", "BREAKOUT_RETEST",
    "PULLBACK_CONTINUATION",
})
_INVALID_IMPULSE = frozenset({
    "IMPULSE_EXHAUSTION", "IMPULSE_EXHAUSTION_RISK", "POST_SPIKE_PULLBACK",
})


def _aligned(value: str | None, direction: str) -> bool:
    token = str(value or "").upper()
    return token in ({"UP", "BULLISH_STRUCTURE", "BULLISH"} if direction == "LONG" else {
        "DOWN", "BEARISH_STRUCTURE", "BEARISH"
    })


def _opposed(value: str | None, direction: str) -> bool:
    token = str(value or "").upper()
    return token in ({"DOWN", "BEARISH_STRUCTURE", "BEARISH"} if direction == "LONG" else {
        "UP", "BULLISH_STRUCTURE", "BULLISH"
    })


def classify_hold_validity(
    thesis: ScalpingEntryThesis,
    evidence: CanonicalHoldEvidence,
) -> tuple[HoldValidity, HoldExitReason | None]:
    """Interpret only explicit canonical evidence; UNKNOWN never invents a reversal."""

    if evidence.engine_status == "ERROR":
        return HoldValidity.ERROR, None
    if evidence.engine_status != "COMPOSED":
        return HoldValidity.DATA_UNAVAILABLE, None
    if _opposed(evidence.structure_direction, thesis.direction):
        return HoldValidity.REVERSED, HoldExitReason.STRUCTURE_INVALIDATED
    if _opposed(evidence.regime, thesis.direction):
        return HoldValidity.REVERSED, HoldExitReason.MOMENTUM_REVERSAL
    if str(evidence.entry_quality or "").upper() in {"INVALID", "POOR"}:
        return HoldValidity.INVALIDATED, HoldExitReason.SETUP_INVALIDATED
    if str(evidence.impulse_phase or "").upper() in _INVALID_IMPULSE:
        return HoldValidity.INVALIDATED, HoldExitReason.MOMENTUM_INVALIDATED
    if thesis.setup_type in _CONTINUATION_SETUPS:
        if _aligned(evidence.regime, thesis.direction) or _aligned(
            evidence.structure_direction, thesis.direction
        ):
            return HoldValidity.VALID, None
        return HoldValidity.STALE, None
    # Range/sweep theses do not require a continuing trend.  Absence of an
    # explicit opposite structure is sufficient; this is revalidation, not a
    # second setup detector.
    return HoldValidity.VALID, None


def evaluate_hold_lifecycle(
    *,
    position_id: str,
    opened_at: datetime,
    thesis: ScalpingEntryThesis,
    evidence: CanonicalHoldEvidence,
    prior_extension_count: int = 0,
    prior_extension_until_ms: int | None = None,
) -> ScalpingHoldDecision:
    policy = SCALPING_V2.exit_policy.stale_position
    evaluated_at = datetime.fromtimestamp(evidence.boundary_ms / 1000, tz=timezone.utc)
    holding = max(0, int((evaluated_at - opened_at.astimezone(timezone.utc)).total_seconds()))
    validity, causal_reason = classify_hold_validity(thesis, evidence)
    state = HoldLifecycleState.FRESH
    reason: HoldExitReason | None = None
    count = prior_extension_count
    extension_until = prior_extension_until_ms

    # The hard limit is absolute and independent of analysis/cost availability.
    if holding >= policy.hard_timeout_seconds:
        state, reason = HoldLifecycleState.FORCE_EXIT, HoldExitReason.MAX_HOLD_TIME
    elif validity in {HoldValidity.INVALIDATED, HoldValidity.REVERSED}:
        state, reason = HoldLifecycleState.FORCE_EXIT, causal_reason
    elif holding >= policy.soft_timeout_seconds:
        soft_boundary = int(opened_at.timestamp() * 1000) + policy.soft_timeout_seconds * 1000
        maximum_until = min(
            int(opened_at.timestamp() * 1000) + policy.hard_timeout_seconds * 1000,
            soft_boundary + policy.extension_seconds * 1000,
        )
        if validity is not HoldValidity.VALID:
            state, reason = HoldLifecycleState.FORCE_EXIT, HoldExitReason.STALE_SCALP
        elif prior_extension_count == 0 and policy.extension_allowed and policy.max_extensions > 0:
            state = HoldLifecycleState.EXTENSION_ALLOWED
            count, extension_until = 1, maximum_until
        elif extension_until is not None and evidence.boundary_ms < extension_until:
            state = HoldLifecycleState.EXTENSION_ALLOWED
        else:
            state, reason = HoldLifecycleState.FORCE_EXIT, HoldExitReason.STALE_SCALP
    elif validity in {HoldValidity.DATA_UNAVAILABLE, HoldValidity.ERROR, HoldValidity.STALE}:
        state = HoldLifecycleState.AT_RISK

    return ScalpingHoldDecision(
        position_id=position_id, boundary_ms=evidence.boundary_ms,
        evaluated_at=evaluated_at, holding_seconds=holding, validity=validity,
        lifecycle_state=state, exit_reason=reason, extension_count=count,
        extension_until_ms=extension_until, thesis=thesis, evidence=evidence,
    )


def canonical_hold_evidence(
    symbol: str, candles: tuple[PaperFillCandle, ...], boundary_ms: int
) -> CanonicalHoldEvidence:
    causal = tuple(item for item in candles if item.close_boundary_ms <= boundary_ms)
    if len(causal) < AnalysisWindowConfig().minimum_candles:
        return CanonicalHoldEvidence(
            boundary_ms, None, None, None, None, None,
            "DATA_UNAVAILABLE", ("NOT_ENOUGH_CLOSED_1M_DATA",),
        )
    engine_candles = tuple(EngineAnalysisCandle(
        timestamp=datetime.fromtimestamp(item.open_time_ms / 1000, tz=timezone.utc).isoformat(),
        open=float(item.open_price), high=float(item.high_price), low=float(item.low_price),
        close=float(item.close_price), volume=0.0,
    ) for item in causal[-AnalysisWindowConfig().context_candles:])
    try:
        output = run_engine_analysis(symbol, "1m", engine_candles)
        payload = output.json_payload
        result = output.composer_output.result
        structure = output.composer_output.matrix.unified_context.altunina_context.structure_direction.value
        status = output.composer_output.decision_trace.status.value
        return CanonicalHoldEvidence(
            boundary_ms=boundary_ms, regime=result.market_regime.value,
            structure_direction=structure,
            impulse_phase=str(payload.get("impulse_phase") or "") or None,
            entry_quality=str(payload.get("entry_quality") or "") or None,
            confidence=float(result.confidence), engine_status=status,
            # Persist a bounded diagnostic sample; the complete engine trace
            # remains in its canonical analysis artifacts.
            reason_codes=tuple(result.reason_codes[:32]),
        )
    except Exception as error:
        return CanonicalHoldEvidence(
            boundary_ms, None, None, None, None, None, "ERROR",
            (f"CANONICAL_ANALYSIS_{type(error).__name__}",),
        )


class PostgresScalpingHoldLifecycleService:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sessions = session_factory

    def _thesis(self, position: PaperPosition) -> ScalpingEntryThesis:
        with self._sessions() as session:
            command = session.scalar(
                select(PaperExecutionCommandRecord)
                .join(
                    PaperOrderRecord,
                    PaperOrderRecord.command_id == PaperExecutionCommandRecord.command_id,
                )
                .where(PaperOrderRecord.order_id == position.entry_order_id)
            )
            if command is None:
                raise LookupError("PAPER_COMMAND_NOT_FOUND")
            result = session.scalar(select(OnlinePipelineResultRow).where(
                OnlinePipelineResultRow.run_id == command.pipeline_run_id
            ))
        setup: Mapping[str, object] = result.setup_payload_json if result is not None else {}
        analysis: Mapping[str, object] = result.analysis_payload_json if result is not None else {}
        setup_type = str(setup.get("setup_type") or setup.get("type") or "UNKNOWN").upper()
        return ScalpingEntryThesis(
            pipeline_run_id=command.pipeline_run_id, profile="trade-5m-v2",
            setup_type=setup_type, direction=position.side.value,
            signal_closed_until_ms=command.closed_until_ms,
            entry_closed_until_ms=int(position.opened_at.timestamp() * 1000),
            entry_regime=str(analysis.get("regime") or analysis.get("market_regime") or "") or None,
            entry_impulse_phase=str(analysis.get("impulse_phase") or "") or None,
            setup_id=command.setup_id, config_hash=TRADE_PARAMETERS.config_hash,
        )

    def evaluate_and_persist(
        self,
        position: PaperPosition,
        candles: Iterable[PaperFillCandle],
        *,
        from_closed_until_ms: int,
    ) -> ScalpingHoldDecision | None:
        ordered = tuple(sorted(candles, key=lambda item: item.open_time_ms))
        candidates = tuple(item for item in ordered if (
            item.close_boundary_ms > int(position.opened_at.timestamp() * 1000)
            and item.close_boundary_ms > from_closed_until_ms
        ))
        if not candidates:
            return None
        thesis = self._thesis(position)
        with self._sessions() as session:
            count = int(session.scalar(select(func.max(
                ScalpingPositionHoldDecisionRecord.extension_count
            )).where(ScalpingPositionHoldDecisionRecord.position_id == position.position_id)) or 0)
            extension_until = session.scalar(select(func.max(
                ScalpingPositionHoldDecisionRecord.extension_until_ms
            )).where(ScalpingPositionHoldDecisionRecord.position_id == position.position_id))
        selected: ScalpingHoldDecision | None = None
        for candle in candidates:
            evidence = canonical_hold_evidence(position.symbol, ordered, candle.close_boundary_ms)
            decision = evaluate_hold_lifecycle(
                position_id=position.position_id, opened_at=position.opened_at,
                thesis=thesis, evidence=evidence, prior_extension_count=count,
                prior_extension_until_ms=extension_until,
            )
            count, extension_until = decision.extension_count, decision.extension_until_ms
            self._persist(decision)
            if decision.force_exit:
                selected = decision
                break
        return selected or decision

    def _persist(self, decision: ScalpingHoldDecision) -> None:
        thesis_json = asdict(decision.thesis)
        evidence_json = asdict(decision.evidence)
        provenance = {
            "policy_version": POLICY_VERSION,
            "decision_hash": sha256(json.dumps({
                "thesis": thesis_json, "evidence": evidence_json,
                "state": decision.lifecycle_state.value,
                "reason": decision.exit_reason.value if decision.exit_reason else None,
            }, sort_keys=True, default=str).encode()).hexdigest(),
            "signal_timeframe": "5m", "hold_timeframe": "1m",
            "future_bars_used": False,
        }
        with self._sessions() as session:
            session.merge(ScalpingPositionHoldDecisionRecord(
                position_id=decision.position_id,
                evaluation_closed_until_ms=decision.boundary_ms,
                evaluated_at=decision.evaluated_at,
                holding_seconds=decision.holding_seconds,
                validity=decision.validity.value,
                lifecycle_state=decision.lifecycle_state.value,
                exit_reason=decision.exit_reason.value if decision.exit_reason else None,
                extension_count=decision.extension_count,
                extension_until_ms=decision.extension_until_ms,
                thesis=thesis_json, evidence=evidence_json,
                policy_version=POLICY_VERSION,
                config_hash=decision.thesis.config_hash,
                provenance=provenance,
            ))
            session.commit()


__all__ = (
    "CanonicalHoldEvidence", "HoldExitReason", "HoldLifecycleState", "HoldValidity",
    "PostgresScalpingHoldLifecycleService", "ScalpingEntryThesis", "ScalpingHoldDecision",
    "canonical_hold_evidence", "classify_hold_validity", "evaluate_hold_lifecycle",
)
