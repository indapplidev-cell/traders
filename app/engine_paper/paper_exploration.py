"""Conservative PAPER-only exploration admission and durable budget view.

The normal empirical decision remains authoritative.  This module only owns
the separately labelled recovery-evidence lane and reads its state from the
existing plan -> command -> position lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
from typing import Any, Callable, Mapping, Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperOrderRecord,
    PaperPlanExecutionOutcomeRecord,
    PaperPositionRecord,
)
from app.engine_paper.scalping_policy_v2 import (
    ADMISSION_PAPER_EXPLORATION,
    EMPIRICAL_AUTHORITY_ESTABLISHED,
    ExpectancyDecision,
)


EXPLORATION_POLICY_VERSION = "limited-paper-exploration-v1"
EXPLORATION_FLAG = "PAPER_EXPLORATION_ENABLED"
EXPLORATION_PROFILE = "trade-5m-v2"
MAX_CONCURRENT_EXPLORATION_POSITIONS_GLOBAL = 1
MAX_OPEN_EXPLORATION_PER_AUTHORITY_POPULATION = 1
MAX_NEW_EXPLORATION_COMMANDS_PER_CYCLE = 1
MAX_EXPLORATION_PROBES_PER_AUTHORITY_POPULATION_ROLLING_24H = 2
MAX_EXPLORATION_PROBES_GLOBAL_ROLLING_24H = 2
EXPLORATION_COOLDOWN_AFTER_CLOSED_HOURS = 6

NORMAL_EMPIRICAL_REJECT_REASON = "SCALPING_EMPIRICAL_EXPECTANCY_REJECTED"


def feature_enabled(environment: Mapping[str, str] | None = None) -> bool:
    """Fail closed: only the exact explicit true value enables exploration."""
    values = os.environ if environment is None else environment
    return str(values.get(EXPLORATION_FLAG, "false")).strip().lower() == "true"


def exploration_execution_permitted(
    *, admission_mode: str, execution_mode: str, live_allowed: bool,
    trade_profile_id: str, enabled: bool,
) -> bool:
    if admission_mode != ADMISSION_PAPER_EXPLORATION:
        return True
    return bool(
        enabled
        and trade_profile_id == EXPLORATION_PROFILE
        and str(execution_mode).upper() == "PAPER"
        and live_allowed is False
    )


def exploration_eligible(
    decision: ExpectancyDecision, *, candidate_net_rr: float | None,
    profile_id: str, execution_mode: str, enabled: bool,
) -> bool:
    """Allow bypass of the established negative-EV veto and nothing else."""
    required = decision.dynamic_required_net_rr
    return bool(
        enabled
        and profile_id == EXPLORATION_PROFILE
        and str(execution_mode).upper() == "PAPER"
        and not decision.admitted
        and decision.empirical_authority_status == EMPIRICAL_AUTHORITY_ESTABLISHED
        and decision.reason == "EMPIRICAL_SUFFICIENT_NEGATIVE_EV"
        and decision.empirical_ev_net_bps is not None
        and decision.empirical_ev_net_bps < 0
        and candidate_net_rr is not None
        and required is not None
        and candidate_net_rr >= required
        and bool(decision.authority_population_id)
        and bool(decision.authority_observation_set_fingerprint)
    )


def exploration_id(*, pipeline_run_id: str, candidate_id: str, population_id: str) -> str:
    material = f"{EXPLORATION_POLICY_VERSION}|{pipeline_run_id}|{candidate_id}|{population_id}"
    return "paper-exploration:v1:" + sha256(material.encode("utf-8")).hexdigest()


def is_exploration_candidate(candidate: object) -> bool:
    return getattr(candidate, "admission_mode", None) == ADMISSION_PAPER_EXPLORATION


@dataclass(frozen=True, slots=True)
class ExplorationBudgetDecision:
    permitted: bool
    block_reason: str | None
    global_open: int
    authority_open: int
    global_24h: int
    authority_24h: int
    last_authority_closed_at: datetime | None
    cooldown_until: datetime | None

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_version": EXPLORATION_POLICY_VERSION,
            "permitted": self.permitted,
            "block_reason": self.block_reason,
            "global_open": self.global_open,
            "authority_open": self.authority_open,
            "global_rolling_24h": self.global_24h,
            "authority_rolling_24h": self.authority_24h,
            "last_authority_closed_at": _iso(self.last_authority_closed_at),
            "cooldown_until": _iso(self.cooldown_until),
            "limits": {
                "global_concurrent": MAX_CONCURRENT_EXPLORATION_POSITIONS_GLOBAL,
                "authority_concurrent": MAX_OPEN_EXPLORATION_PER_AUTHORITY_POPULATION,
                "global_rolling_24h": MAX_EXPLORATION_PROBES_GLOBAL_ROLLING_24H,
                "authority_rolling_24h": MAX_EXPLORATION_PROBES_PER_AUTHORITY_POPULATION_ROLLING_24H,
                "cooldown_hours": EXPLORATION_COOLDOWN_AFTER_CLOSED_HOURS,
            },
        }


@dataclass(frozen=True, slots=True)
class ExplorationRecoveryEvidence:
    authority_population_id: str
    exploration_closed_count: int
    exploration_wins: int
    exploration_losses: int
    exploration_breakeven: int
    exploration_avg_win_net_bps: float | None
    exploration_avg_loss_net_bps: float | None
    exploration_ev_net_bps: float | None
    first_probe_at: datetime | None
    last_probe_at: datetime | None


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _details(row: PaperPlanExecutionOutcomeRecord) -> Mapping[str, Any]:
    value = row.refinement_details
    return value if isinstance(value, Mapping) else {}


class PaperExplorationStore:
    """Read-only budget/recovery view over existing durable lifecycle rows."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _is_exploration(row: PaperPlanExecutionOutcomeRecord) -> bool:
        return _details(row).get("admission_mode") == ADMISSION_PAPER_EXPLORATION

    def _rows(self) -> tuple[tuple[PaperPlanExecutionOutcomeRecord, PaperPositionRecord | None], ...]:
        statement = (
            select(PaperPlanExecutionOutcomeRecord, PaperPositionRecord)
            .outerjoin(
                PaperExecutionCommandRecord,
                PaperExecutionCommandRecord.command_id == PaperPlanExecutionOutcomeRecord.command_id,
            )
            .outerjoin(
                PaperOrderRecord,
                and_(
                    PaperOrderRecord.command_id == PaperExecutionCommandRecord.command_id,
                    PaperOrderRecord.order_role == "ENTRY",
                ),
            )
            .outerjoin(
                PaperPositionRecord,
                PaperPositionRecord.entry_order_id == PaperOrderRecord.order_id,
            )
            .where(PaperPlanExecutionOutcomeRecord.command_id.is_not(None))
        )
        with self._session_factory() as session:
            return tuple(session.execute(statement))

    def evaluate_budget(
        self, authority_population_id: str, *, now: datetime | None = None,
    ) -> ExplorationBudgetDecision:
        observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        cutoff = observed - timedelta(hours=24)
        rows = tuple((outcome, position) for outcome, position in self._rows() if self._is_exploration(outcome))
        authority_rows = tuple(
            item for item in rows
            if _details(item[0]).get("authority_population_id") == authority_population_id
        )
        unresolved = tuple(
            item for item in rows if item[1] is None or item[1].state != "CLOSED"
        )
        authority_unresolved = tuple(item for item in unresolved if item in authority_rows)

        def started(item: tuple[PaperPlanExecutionOutcomeRecord, PaperPositionRecord | None]) -> datetime:
            position = item[1]
            return (position.opened_at if position is not None else item[0].updated_at).astimezone(timezone.utc)

        global_24h = sum(started(item) >= cutoff for item in rows)
        authority_24h = sum(started(item) >= cutoff for item in authority_rows)
        closed = tuple(
            position.closed_at.astimezone(timezone.utc)
            for _, position in authority_rows
            if position is not None and position.state == "CLOSED" and position.closed_at is not None
        )
        last_closed = max(closed) if closed else None
        cooldown_until = (
            last_closed + timedelta(hours=EXPLORATION_COOLDOWN_AFTER_CLOSED_HOURS)
            if last_closed is not None else None
        )
        reason = None
        if unresolved:
            reason = "EXPLORATION_POSITION_ALREADY_OPEN"
        elif authority_unresolved:
            reason = "EXPLORATION_POSITION_ALREADY_OPEN"
        elif cooldown_until is not None and observed < cooldown_until:
            reason = "EXPLORATION_AUTHORITY_COOLDOWN_ACTIVE"
        elif authority_24h >= MAX_EXPLORATION_PROBES_PER_AUTHORITY_POPULATION_ROLLING_24H:
            reason = "EXPLORATION_AUTHORITY_24H_BUDGET_EXHAUSTED"
        elif global_24h >= MAX_EXPLORATION_PROBES_GLOBAL_ROLLING_24H:
            reason = "EXPLORATION_GLOBAL_24H_BUDGET_EXHAUSTED"
        return ExplorationBudgetDecision(
            reason is None, reason, len(unresolved), len(authority_unresolved),
            global_24h, authority_24h, last_closed, cooldown_until,
        )

    def recovery_evidence(self, authority_population_id: str) -> ExplorationRecoveryEvidence:
        rows = tuple(
            (outcome, position) for outcome, position in self._rows()
            if self._is_exploration(outcome)
            and _details(outcome).get("authority_population_id") == authority_population_id
            and position is not None and position.state == "CLOSED"
        )
        returns: list[float] = []
        opened: list[datetime] = []
        for _, position in rows:
            notional = float(position.entry_quantity) * float(position.average_entry_price)
            returns.append(float(position.realized_pnl) / notional * 10_000)
            opened.append(position.opened_at.astimezone(timezone.utc))
        wins = [value for value in returns if value > 0]
        losses = [abs(value) for value in returns if value < 0]
        breakeven = sum(value == 0 for value in returns)
        average_win = sum(wins) / len(wins) if wins else None
        average_loss = sum(losses) / len(losses) if losses else None
        ev = sum(returns) / len(returns) if returns else None
        return ExplorationRecoveryEvidence(
            authority_population_id, len(rows), len(wins), len(losses), breakeven,
            average_win, average_loss, ev,
            min(opened) if opened else None, max(opened) if opened else None,
        )


def exploration_selection_metadata(candidate: object) -> dict[str, object]:
    provenance = getattr(candidate, "exploration_provenance", None)
    values = dict(provenance) if isinstance(provenance, Mapping) else {}
    values["admission_mode"] = ADMISSION_PAPER_EXPLORATION
    values["exploration_policy_version"] = EXPLORATION_POLICY_VERSION
    return values


__all__ = (
    "EXPLORATION_COOLDOWN_AFTER_CLOSED_HOURS", "EXPLORATION_FLAG",
    "EXPLORATION_POLICY_VERSION", "ExplorationBudgetDecision",
    "ExplorationRecoveryEvidence", "MAX_CONCURRENT_EXPLORATION_POSITIONS_GLOBAL",
    "MAX_EXPLORATION_PROBES_GLOBAL_ROLLING_24H",
    "MAX_EXPLORATION_PROBES_PER_AUTHORITY_POPULATION_ROLLING_24H",
    "MAX_NEW_EXPLORATION_COMMANDS_PER_CYCLE", "MAX_OPEN_EXPLORATION_PER_AUTHORITY_POPULATION",
    "PaperExplorationStore", "exploration_eligible", "exploration_execution_permitted",
    "exploration_id", "exploration_selection_metadata", "feature_enabled",
    "is_exploration_candidate",
)
