"""Durable observability for PAPER plan selection and execution attempts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.paper_models import PaperPlanExecutionOutcomeRecord
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow

from .eligible_approval_ranking import (
    EligibleApprovalSelectionResult,
    rank_eligible_candidates,
)


TERMINAL_STATES = frozenset({"EXECUTION_FAILED", "EXPIRED_BEFORE_EXECUTION"})


class PaperPlanExecutionOutcomeStore:
    """Idempotent one-row lifecycle per source pipeline run."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _utc(value: datetime | None = None) -> datetime:
        current = value or datetime.now(timezone.utc)
        return current.replace(tzinfo=timezone.utc) if current.tzinfo is None else current.astimezone(timezone.utc)

    @staticmethod
    def _paper_identity(session: Session, run_id: str) -> tuple[str, int]:
        payload = session.execute(
            select(OnlinePipelineResultRow.paper_payload_json)
            .where(OnlinePipelineResultRow.run_id == run_id)
            .order_by(OnlinePipelineResultRow.id.desc())
            .limit(1)
        ).scalar_one()
        paper = payload if isinstance(payload, Mapping) else {}
        plan_id = str(paper.get("paper_plan_id") or "")
        created = int(paper.get("created_at_ms", -1))
        if not plan_id or created < 0:
            raise ValueError("PAPER_PLAN_IDENTITY_MISSING")
        return plan_id, created

    def observe_selection(
        self,
        candidates: Sequence[Any],
        selection: EligibleApprovalSelectionResult,
        *,
        universe_id: str,
        control_generation: int,
        observed_at: datetime | None = None,
    ) -> None:
        now = self._utc(observed_at)
        ordered = rank_eligible_candidates(candidates)
        ranks = {value.candidate_id: index + 1 for index, value in enumerate(ordered)}
        winner_id = selection.winner.candidate_id if selection.winner is not None else None
        with self._session_factory() as session, session.begin():
            for candidate in ordered:
                run_id = candidate.lineage.source_run_id
                row = session.get(PaperPlanExecutionOutcomeRecord, run_id)
                plan_id, created = self._paper_identity(session, run_id)
                selected = candidate.candidate_id == winner_id
                state = "PLAN_OBSERVED" if selected else "NOT_SELECTED"
                reason = (
                    None if selected else "LOWER_SELECTOR_RANK"
                )
                if row is None:
                    row = PaperPlanExecutionOutcomeRecord(
                        pipeline_run_id=run_id,
                        paper_plan_id=plan_id,
                        final_approval_id=candidate.lineage.final_approval_id,
                        candidate_id=candidate.candidate_id,
                        symbol=candidate.symbol,
                        trade_profile_id=candidate.trade_profile_id,
                        universe_id=universe_id,
                        boundary_closed_at_ms=candidate.watermark.closed_until_ms,
                        plan_created_at_ms=created,
                        approval_valid_until_ms=candidate.valid_until_ms,
                        selector_state="SELECTED" if selected else "NOT_SELECTED",
                        selector_reason=reason,
                        selector_rank=ranks[candidate.candidate_id],
                        selected_winner=selected,
                        lifecycle_state=state,
                        terminal_reason=None,
                        command_id=None,
                        control_generation=control_generation,
                        runtime_enabled=True,
                        daemon_enabled=True,
                        scheduler_enabled=True,
                        mutation_enabled=True,
                        live_enabled=False,
                        attempt_count=0,
                        first_observed_at=now,
                        updated_at=now,
                        terminal_at=None,
                    )
                    session.add(row)
                elif row.lifecycle_state not in TERMINAL_STATES and row.command_id is None:
                    row.selector_state = "SELECTED" if selected else "NOT_SELECTED"
                    row.selector_reason = reason
                    row.selector_rank = ranks[candidate.candidate_id]
                    row.selected_winner = selected
                    row.lifecycle_state = state
                    row.updated_at = now

    def unconsumed_candidates(self, candidates: Sequence[Any]) -> tuple[Any, ...]:
        """Exclude approvals that already produced a durable command."""
        run_ids = tuple(candidate.lineage.source_run_id for candidate in candidates)
        if not run_ids:
            return ()
        with self._session_factory() as session:
            consumed = frozenset(session.scalars(
                select(PaperPlanExecutionOutcomeRecord.pipeline_run_id).where(
                    PaperPlanExecutionOutcomeRecord.pipeline_run_id.in_(run_ids),
                    PaperPlanExecutionOutcomeRecord.command_id.is_not(None),
                )
            ))
        return tuple(
            candidate for candidate in candidates
            if candidate.lineage.source_run_id not in consumed
        )

    def record_attempt(
        self,
        run_id: str,
        *,
        blocker_codes: Sequence[str] = (),
        command_id: str | None = None,
        failure_code: str | None = None,
        observed_at: datetime | None = None,
    ) -> None:
        now = self._utc(observed_at)
        with self._session_factory() as session, session.begin():
            row = session.get(PaperPlanExecutionOutcomeRecord, run_id)
            if row is None:
                raise ValueError("PAPER_PLAN_OUTCOME_NOT_OBSERVED")
            if row.lifecycle_state in TERMINAL_STATES and row.command_id is None:
                return
            row.attempt_count += 1
            row.updated_at = now
            if command_id is not None:
                row.command_id = command_id
                row.lifecycle_state = "COMMAND_CREATED"
                row.terminal_reason = None
                row.terminal_at = None
                row.selector_reason = None
            elif failure_code is not None:
                row.lifecycle_state = "EXECUTION_FAILED"
                row.terminal_reason = failure_code
                row.terminal_at = now
            elif blocker_codes:
                row.lifecycle_state = "BLOCKED_BY_POLICY"
                row.selector_reason = ",".join(dict.fromkeys(blocker_codes))

    def expire_due(self, as_of_ms: int, *, observed_at: datetime | None = None) -> int:
        now = self._utc(observed_at)
        with self._session_factory() as session, session.begin():
            rows = tuple(session.execute(
                select(PaperPlanExecutionOutcomeRecord).where(
                    PaperPlanExecutionOutcomeRecord.command_id.is_(None),
                    PaperPlanExecutionOutcomeRecord.approval_valid_until_ms < as_of_ms,
                    PaperPlanExecutionOutcomeRecord.lifecycle_state.in_((
                        "PLAN_OBSERVED", "NOT_SELECTED", "BLOCKED_BY_POLICY",
                    )),
                )
            ).scalars())
            for row in rows:
                row.lifecycle_state = "EXPIRED_BEFORE_EXECUTION"
                row.terminal_reason = "EXPIRED_BEFORE_EXECUTION"
                row.terminal_at = now
                row.updated_at = now
            return len(rows)


__all__ = ("PaperPlanExecutionOutcomeStore", "TERMINAL_STATES")
