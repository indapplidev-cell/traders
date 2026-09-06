"""Read-only statistical authority for Scalping v2 PAPER admission."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_orchestrator.orchestrator_models import (
    OnlinePipelineResultRow,
    OnlinePipelineRun,
)
from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket


STATISTICS_SOURCE_VERSION = "postgres-paper-outcomes-v1"


@dataclass(frozen=True, slots=True)
class PaperOutcome:
    symbol: str
    setup_type: str
    direction: str
    regime: str
    cost_bucket: str
    won: bool


@dataclass(frozen=True, slots=True)
class StatisticalHierarchy:
    exact: EmpiricalSetupBucket | None
    parents: tuple[EmpiricalSetupBucket, ...]
    source_version: str = STATISTICS_SOURCE_VERSION
    outcome_count: int = 0


def _text(value: object, default: str = "UNKNOWN") -> str:
    normalized = str(value or default).strip().upper()
    return normalized or default


def _nested(payload: object, *path: str) -> object | None:
    value: object = payload
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _cost_bucket(payload: object) -> str:
    raw = _nested(
        payload, "paper_context", "scalping_geometry_diagnostics",
        "effective_total_cost_bps",
    )
    try:
        cost = float(raw)
    except (TypeError, ValueError):
        return "UNKNOWN"
    return "LOW" if cost <= 20 else "MEDIUM" if cost <= 40 else "HIGH"


def hierarchy_from_outcomes(
    outcomes: Iterable[PaperOutcome], *, symbol: str, setup_type: str,
    direction: str, regime: str = "UNKNOWN", cost_bucket: str = "UNKNOWN",
) -> StatisticalHierarchy:
    """Build the configured narrow-to-global hierarchy from real outcomes."""
    rows = tuple(outcomes)
    dimensions = (
        ("exact", lambda row: (
            row.symbol, row.setup_type, row.direction, row.regime, row.cost_bucket
        ) == (symbol, setup_type, direction, regime, cost_bucket)),
        ("setup_direction_regime", lambda row: (
            row.setup_type, row.direction, row.regime
        ) == (setup_type, direction, regime)),
        ("setup_direction", lambda row: (
            row.setup_type, row.direction
        ) == (setup_type, direction)),
        ("setup", lambda row: row.setup_type == setup_type),
        ("global", lambda row: True),
    )
    buckets: list[EmpiricalSetupBucket] = []
    for level, predicate in dimensions:
        selected = tuple(row for row in rows if predicate(row))
        buckets.append(EmpiricalSetupBucket(
            setup_type=setup_type,
            direction=direction,
            samples=len(selected),
            wins=sum(row.won for row in selected),
            level=level,
            bucket_key=(
                f"{level}|{symbol}|{setup_type}|{direction}|{regime}|{cost_bucket}"
            ),
        ))
    return StatisticalHierarchy(buckets[0], tuple(buckets[1:]), outcome_count=len(rows))


class PostgresPaperOutcomeStatisticsSource:
    """Bounded adapter over the existing durable PAPER lifecycle truth."""

    def __init__(
        self, session_factory: Callable[[], Session], *, maximum_outcomes: int = 5_000,
    ) -> None:
        if maximum_outcomes <= 0:
            raise ValueError("maximum_outcomes must be positive")
        self._session_factory = session_factory
        self.maximum_outcomes = maximum_outcomes

    def _load(self) -> tuple[PaperOutcome, ...]:
        statement = (
            select(
                PaperPositionRecord.symbol,
                PaperPositionRecord.side,
                PaperPositionRecord.realized_pnl,
                OnlinePipelineResultRow.setup_payload_json,
                OnlinePipelineResultRow.analysis_payload_json,
                OnlinePipelineResultRow.paper_payload_json,
            )
            .join(PaperOrderRecord, PaperOrderRecord.order_id == PaperPositionRecord.entry_order_id)
            .join(
                PaperExecutionCommandRecord,
                PaperExecutionCommandRecord.command_id == PaperOrderRecord.command_id,
            )
            .join(
                OnlinePipelineRun,
                OnlinePipelineRun.run_id == PaperExecutionCommandRecord.pipeline_run_id,
            )
            .join(
                OnlinePipelineResultRow,
                OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id,
            )
            .where(
                PaperPositionRecord.state == "CLOSED",
                OnlinePipelineRun.trade_profile_id == "trade-5m-v2",
            )
            .order_by(PaperPositionRecord.closed_at.desc())
            .limit(self.maximum_outcomes)
        )
        with self._session_factory() as session:
            rows = tuple(session.execute(statement))
        return tuple(PaperOutcome(
            symbol=_text(row.symbol),
            setup_type=_text(_nested(row.setup_payload_json, "setup_type")),
            direction="BULLISH" if _text(row.side) == "LONG" else "BEARISH",
            regime=_text(_nested(row.analysis_payload_json, "regime")),
            cost_bucket=_cost_bucket(row.paper_payload_json),
            won=float(row.realized_pnl) > 0,
        ) for row in rows)

    def resolve(
        self, *, symbol: str, setup_type: str, direction: str,
        regime: str = "UNKNOWN", cost_bucket: str = "UNKNOWN",
    ) -> StatisticalHierarchy:
        return hierarchy_from_outcomes(
            self._load(), symbol=_text(symbol), setup_type=_text(setup_type),
            direction=_text(direction), regime=_text(regime),
            cost_bucket=_text(cost_bucket),
        )


__all__ = (
    "PaperOutcome", "PostgresPaperOutcomeStatisticsSource",
    "STATISTICS_SOURCE_VERSION", "StatisticalHierarchy",
    "hierarchy_from_outcomes",
)
