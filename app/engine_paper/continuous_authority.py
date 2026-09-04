"""Durable restart-safe authority and budgets for continuous production PAPER."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.paper_models import (
    PaperContinuousControlEventRecord,
    PaperContinuousControlRecord,
    PaperExecutionCommandRecord,
    PaperFirstCanarySessionRecord,
    PaperPositionRecord,
)


CONTROL_MODE = "CONTINUOUS"
CONTROL_MODE_VERSION = 1
TRADING_DAY_TIMEZONE = "UTC"
DAILY_COMMAND_BUDGET = 10
DAILY_REALIZED_LOSS_BUDGET = Decimal("0.500000000000000000")
DAILY_RISK_BUDGET_BPS = Decimal("50.0000000000")
SCALPING_V2_RISK_PER_TRADE_BPS = Decimal("10.0000000000")
MAX_CONSECUTIVE_LOSSES: int | None = None
ACTIVE_STATE = "CONTINUOUS_ARMED"
PAUSED_STATE = "PAUSED_BY_RISK"


class ContinuousAuthorityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ContinuousAuthoritySnapshot:
    control_mode: str
    control_state: str
    enabled: bool
    generation: int
    mode_version: int
    activated_at: datetime | None
    updated_at: datetime
    activation_source: str | None
    activation_reason: str | None
    budget_day: date
    daily_command_budget: int
    daily_realized_loss_budget: Decimal
    daily_risk_budget_bps: Decimal
    max_consecutive_losses: int | None
    commands_used: int
    realized_pnl: Decimal
    realized_loss: Decimal
    risk_used_bps: Decimal
    loss_streak: int
    pause_reason: str | None
    last_successful_reconciliation: datetime | None
    last_command_id: str | None
    last_position_id: str | None
    open_positions: int
    in_flight_commands: int
    version: int

    @property
    def budget_reason(self) -> str | None:
        if self.commands_used >= self.daily_command_budget:
            return "DAILY_COMMAND_BUDGET_EXHAUSTED"
        if self.realized_loss >= self.daily_realized_loss_budget:
            return "DAILY_LOSS_BUDGET_EXHAUSTED"
        if self.risk_used_bps >= self.daily_risk_budget_bps:
            return "DAILY_RISK_BUDGET_EXHAUSTED"
        if self.max_consecutive_losses is not None and self.loss_streak >= self.max_consecutive_losses:
            return "MAX_CONSECUTIVE_LOSSES_REACHED"
        return None


def _event_id(event_type: str, identity: str) -> str:
    return "paper:continuous:event:" + sha256(f"{event_type}|{identity}".encode("utf-8")).hexdigest()


class PaperContinuousAuthorityStore:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _open_positions(session: Session) -> int:
        return int(session.scalar(
            select(func.count()).select_from(PaperPositionRecord).where(
                PaperPositionRecord.state.in_(("OPEN", "CLOSING"))
            )
        ) or 0)

    @staticmethod
    def _in_flight_commands(session: Session) -> int:
        # Command processing_status intentionally remains durable history and is
        # not a lifecycle completion marker.  The continuous-cycle row is the
        # authoritative bounded work claim, so only an active cycle with a
        # command but no position is an in-flight command.
        return int(session.scalar(
            select(func.count()).select_from(PaperFirstCanarySessionRecord).where(
                PaperFirstCanarySessionRecord.authority_mode == CONTROL_MODE,
                PaperFirstCanarySessionRecord.command_id.is_not(None),
                PaperFirstCanarySessionRecord.position_id.is_(None),
                PaperFirstCanarySessionRecord.state.notin_(
                    ("COMPLETED", "FAILED_SAFE", "PREEMPTED")
                ),
            )
        ) or 0)

    def _snapshot(self, session: Session, row: PaperContinuousControlRecord) -> ContinuousAuthoritySnapshot:
        return ContinuousAuthoritySnapshot(
            control_mode=row.control_mode, control_state=row.control_state, enabled=row.enabled,
            generation=row.generation, mode_version=row.mode_version,
            activated_at=row.activated_at, updated_at=row.updated_at,
            activation_source=row.activation_source, activation_reason=row.activation_reason,
            budget_day=row.budget_day, daily_command_budget=row.daily_command_budget,
            daily_realized_loss_budget=row.daily_realized_loss_budget,
            daily_risk_budget_bps=row.daily_risk_budget_bps,
            max_consecutive_losses=row.max_consecutive_losses,
            commands_used=row.commands_used, realized_pnl=row.realized_pnl,
            realized_loss=row.realized_loss, risk_used_bps=row.risk_used_bps,
            loss_streak=row.loss_streak, pause_reason=row.pause_reason,
            last_successful_reconciliation=row.last_successful_reconciliation,
            last_command_id=row.last_command_id, last_position_id=row.last_position_id,
            open_positions=self._open_positions(session),
            in_flight_commands=self._in_flight_commands(session), version=row.version,
        )

    @staticmethod
    def _append_event(
        session: Session, *, event_type: str, identity: str, row: PaperContinuousControlRecord,
        reason: str, source: str, details: dict[str, object], now: datetime,
    ) -> None:
        event_id = _event_id(event_type, identity)
        if session.get(PaperContinuousControlEventRecord, event_id) is None:
            session.add(PaperContinuousControlEventRecord(
                event_id=event_id, event_type=event_type, occurred_at=now,
                generation=row.generation, control_state=row.control_state,
                reason_code=reason, source=source, details=details,
            ))

    def read(self) -> ContinuousAuthoritySnapshot | None:
        with self._session_factory() as session:
            row = session.get(PaperContinuousControlRecord, "PRODUCTION")
            return None if row is None else self._snapshot(session, row)

    def activate(
        self, *, generation: int, source: str, reason: str,
        now: datetime | None = None,
    ) -> ContinuousAuthoritySnapshot:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with self._session_factory() as session:
            try:
                row = session.get(PaperContinuousControlRecord, "PRODUCTION", with_for_update=True)
                if row is None:
                    row = PaperContinuousControlRecord(
                        environment="PRODUCTION", control_mode=CONTROL_MODE,
                        control_state=ACTIVE_STATE, enabled=True, generation=generation,
                        mode_version=CONTROL_MODE_VERSION, activated_at=current, updated_at=current,
                        activation_source=source, activation_reason=reason,
                        trading_day_timezone=TRADING_DAY_TIMEZONE, budget_day=current.date(),
                        daily_command_budget=DAILY_COMMAND_BUDGET,
                        daily_realized_loss_budget=DAILY_REALIZED_LOSS_BUDGET,
                        daily_risk_budget_bps=DAILY_RISK_BUDGET_BPS,
                        max_consecutive_losses=MAX_CONSECUTIVE_LOSSES,
                        commands_used=0, realized_pnl=Decimal("0"), realized_loss=Decimal("0"),
                        risk_used_bps=Decimal("0"), loss_streak=0, pause_reason=None,
                        last_successful_reconciliation=current, last_command_id=None,
                        last_position_id=None, version=0,
                    )
                    session.add(row)
                    session.flush()
                elif row.generation == generation and row.control_state == ACTIVE_STATE:
                    return self._snapshot(session, row)
                else:
                    row.control_state = ACTIVE_STATE
                    row.enabled = True
                    row.generation = generation
                    row.activated_at = current
                    row.updated_at = current
                    row.activation_source = source
                    row.activation_reason = reason
                    row.pause_reason = None
                    row.version += 1
                self._append_event(
                    session, event_type="CONTINUOUS_ACTIVATED", identity=str(generation), row=row,
                    reason=reason, source=source,
                    details={"mode": CONTROL_MODE, "mode_version": CONTROL_MODE_VERSION}, now=current,
                )
                session.commit()
                return self._snapshot(session, row)
            except (IntegrityError, SQLAlchemyError) as exc:
                session.rollback()
                raise ContinuousAuthorityError("CONTINUOUS_ACTIVATION_FAILED") from exc

    def reconcile(self, *, generation: int, now: datetime | None = None) -> ContinuousAuthoritySnapshot:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with self._session_factory() as session:
            row = session.get(PaperContinuousControlRecord, "PRODUCTION", with_for_update=True)
            if row is None:
                raise ContinuousAuthorityError("CONTINUOUS_CONTROL_NOT_CONFIGURED")
            if row.generation != generation:
                raise ContinuousAuthorityError("CONTINUOUS_CONTROL_GENERATION_MISMATCH")
            if row.budget_day != current.date():
                old_day = row.budget_day.isoformat()
                row.budget_day = current.date()
                row.commands_used = 0
                row.realized_pnl = Decimal("0")
                row.realized_loss = Decimal("0")
                row.risk_used_bps = Decimal("0")
                row.loss_streak = 0
                row.pause_reason = None
                row.control_state = ACTIVE_STATE
                row.enabled = True
                row.version += 1
                self._append_event(
                    session, event_type="TRADING_DAY_RESET", identity=current.date().isoformat(), row=row,
                    reason="TRADING_DAY_BUDGET_RESET", source="continuous-worker",
                    details={"previous_budget_day": old_day, "timezone": TRADING_DAY_TIMEZONE}, now=current,
                )
            reason = row.pause_reason
            snapshot = self._snapshot(session, row)
            computed = snapshot.budget_reason
            if computed is not None and row.control_state == ACTIVE_STATE:
                row.control_state = PAUSED_STATE
                row.enabled = False
                row.pause_reason = computed
                row.version += 1
                reason = computed
                self._append_event(
                    session, event_type="RISK_PAUSED", identity=f"{row.budget_day}:{computed}", row=row,
                    reason=computed, source="continuous-worker", details={}, now=current,
                )
            row.last_successful_reconciliation = current
            row.updated_at = current
            session.commit()
            return self._snapshot(session, row)

    def record_command(self, *, command_id: str, position_id: str | None = None, now: datetime | None = None) -> ContinuousAuthoritySnapshot:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with self._session_factory() as session:
            row = session.get(PaperContinuousControlRecord, "PRODUCTION", with_for_update=True)
            if row is None or row.control_state != ACTIVE_STATE:
                raise ContinuousAuthorityError("CONTINUOUS_CONTROL_NOT_ARMED")
            identity = f"command:{command_id}"
            event_id = _event_id("COMMAND_RECORDED", identity)
            if session.get(PaperContinuousControlEventRecord, event_id) is None:
                row.commands_used += 1
                row.risk_used_bps += SCALPING_V2_RISK_PER_TRADE_BPS
                row.last_command_id = command_id
                if position_id is not None:
                    row.last_position_id = position_id
                row.updated_at = current
                row.version += 1
                self._append_event(
                    session, event_type="COMMAND_RECORDED", identity=identity, row=row,
                    reason="COMMAND_CREATED", source="continuous-worker",
                    details={"command_id": command_id, "risk_bps": str(SCALPING_V2_RISK_PER_TRADE_BPS)}, now=current,
                )
            session.commit()
            return self._snapshot(session, row)

    def set_control_state(
        self, *, generation: int, state: str, source: str, reason: str,
        now: datetime | None = None,
    ) -> ContinuousAuthoritySnapshot | None:
        """Mirror an operator stop into the durable continuous authority row."""
        if state not in {"DISABLED", "EMERGENCY_STOPPED"}:
            raise ValueError("unsupported continuous control state")
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with self._session_factory() as session:
            row = session.get(PaperContinuousControlRecord, "PRODUCTION", with_for_update=True)
            if row is None:
                return None
            identity = f"{state}:{generation}"
            event_id = _event_id("CONTROL_STATE_CHANGED", identity)
            if session.get(PaperContinuousControlEventRecord, event_id) is None:
                row.control_state = state
                row.enabled = False
                row.generation = generation
                row.updated_at = current
                row.pause_reason = reason if state == "EMERGENCY_STOPPED" else None
                row.version += 1
                self._append_event(
                    session, event_type="CONTROL_STATE_CHANGED", identity=identity, row=row,
                    reason=reason, source=source, details={"state": state}, now=current,
                )
            session.commit()
            return self._snapshot(session, row)

    def record_position(self, *, position_id: str, now: datetime | None = None) -> ContinuousAuthoritySnapshot:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with self._session_factory() as session:
            row = session.get(PaperContinuousControlRecord, "PRODUCTION", with_for_update=True)
            if row is None:
                raise ContinuousAuthorityError("CONTINUOUS_CONTROL_NOT_CONFIGURED")
            event_id = _event_id("POSITION_LINKED", position_id)
            if session.get(PaperContinuousControlEventRecord, event_id) is None:
                row.last_position_id = position_id
                row.updated_at = current
                row.version += 1
                self._append_event(
                    session, event_type="POSITION_LINKED", identity=position_id, row=row,
                    reason="POSITION_OPEN", source="continuous-worker",
                    details={"position_id": position_id}, now=current,
                )
            session.commit()
            return self._snapshot(session, row)

    def record_close(
        self, *, position_id: str, realized_pnl: Decimal,
        reconciliation_healthy: bool, now: datetime | None = None,
    ) -> ContinuousAuthoritySnapshot:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        with self._session_factory() as session:
            row = session.get(PaperContinuousControlRecord, "PRODUCTION", with_for_update=True)
            if row is None:
                raise ContinuousAuthorityError("CONTINUOUS_CONTROL_NOT_CONFIGURED")
            if not reconciliation_healthy:
                raise ContinuousAuthorityError("CONTINUOUS_RECONCILIATION_UNHEALTHY")
            event_id = _event_id("POSITION_CLOSED", position_id)
            if session.get(PaperContinuousControlEventRecord, event_id) is None:
                value = Decimal(realized_pnl)
                row.realized_pnl += value
                if value < 0:
                    row.realized_loss += -value
                    row.loss_streak += 1
                else:
                    row.loss_streak = 0
                row.last_position_id = position_id
                row.last_successful_reconciliation = current
                row.updated_at = current
                row.version += 1
                self._append_event(
                    session, event_type="POSITION_CLOSED", identity=position_id, row=row,
                    reason="POSITION_CLOSED_RECONCILED", source="continuous-worker",
                    details={"position_id": position_id, "realized_pnl": str(value)}, now=current,
                )
            session.commit()
            return self._snapshot(session, row)


__all__ = (
    "ACTIVE_STATE", "CONTROL_MODE", "CONTROL_MODE_VERSION", "ContinuousAuthorityError",
    "ContinuousAuthoritySnapshot", "DAILY_COMMAND_BUDGET", "DAILY_REALIZED_LOSS_BUDGET",
    "DAILY_RISK_BUDGET_BPS", "MAX_CONSECUTIVE_LOSSES", "PAUSED_STATE",
    "PaperContinuousAuthorityStore", "SCALPING_V2_RISK_PER_TRADE_BPS",
)
