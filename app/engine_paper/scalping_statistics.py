"""Read-only statistical authority for Scalping v2 PAPER admission."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
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


STATISTICS_SOURCE_VERSION = "postgres-paper-plus-causal-prospective-v2"
PROSPECTIVE_OUTCOME_SEMANTICS = "scalping-probability-outcome-v2-ttl30s-timestop15m-netcost"


@dataclass(frozen=True, slots=True)
class PaperOutcome:
    symbol: str
    setup_type: str
    direction: str
    regime: str
    cost_bucket: str
    won: bool
    parameter_set_id: str = "legacy-unattributed"
    observed_at_ms: int = 0
    evidence_source: str = "CLOSED_PAPER_POSITION"
    outcome_semantics: str = "REALIZED_NET_PNL"


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


def _utc_ms(value: object) -> int:
    if isinstance(value, datetime):
        current = value
    else:
        try:
            current = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return 0
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return int(current.timestamp() * 1000)


def load_prospective_outcomes(
    root: Path, *, parameter_set_id: str,
) -> tuple[PaperOutcome, ...]:
    """Load only causally complete, exact-semantics outcomes from one set segment."""
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return ()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    compatible_segments = {
        str(item.get("observation_segment_id"))
        for item in manifest.get("segments", ())
        if _text(_nested(item, "homogeneity_identity", "parameter_set_id")).lower()
        == _text(parameter_set_id).lower()
        and _nested(item, "homogeneity_identity", "outcome_semantics_version")
        == PROSPECTIVE_OUTCOME_SEMANTICS
    }
    results: list[PaperOutcome] = []
    for part in manifest.get("parts", ()):
        if part.get("kind") != "outcomes" or str(part.get("observation_segment_id")) not in compatible_segments:
            continue
        path = root / str(part.get("path"))
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            frozen = _nested(record, "frozen_opportunity")
            if not isinstance(frozen, Mapping):
                continue
            terminal = str(record.get("baseline_outcome") or "")
            if terminal == "TP_FIRST":
                won = True
            elif terminal == "SL_FIRST":
                won = False
            elif terminal == "TIME_EXPIRED" and record.get("net_return_bps") is not None:
                won = float(record["net_return_bps"]) > 0
            else:
                # Entry expiry, ambiguous same-candle paths and incomplete geometry
                # are not silently converted into probability labels.
                continue
            results.append(PaperOutcome(
                symbol=_text(frozen.get("symbol")),
                setup_type=_text(frozen.get("setup_type")),
                direction=_text(frozen.get("direction")),
                regime=_text(frozen.get("regime")),
                cost_bucket=_text(frozen.get("cost_bucket")),
                won=won,
                parameter_set_id=_text(parameter_set_id).lower(),
                observed_at_ms=_utc_ms(record.get("completed_at")),
                evidence_source="CAUSAL_COUNTERFACTUAL_OPPORTUNITY",
                outcome_semantics=PROSPECTIVE_OUTCOME_SEMANTICS,
            ))
    return tuple(results)


def hierarchy_from_outcomes(
    outcomes: Iterable[PaperOutcome], *, symbol: str, setup_type: str,
    direction: str, regime: str = "UNKNOWN", cost_bucket: str = "UNKNOWN",
    parameter_set_id: str | None = None,
) -> StatisticalHierarchy:
    """Build the configured narrow-to-global hierarchy from real outcomes."""
    rows = tuple(
        row for row in outcomes
        if parameter_set_id is None or row.parameter_set_id == parameter_set_id
    )
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
        evidence_sources = sorted({row.evidence_source for row in selected})
        buckets.append(EmpiricalSetupBucket(
            setup_type=setup_type,
            direction=direction,
            samples=len(selected),
            wins=sum(row.won for row in selected),
            level=level,
            bucket_key=(
                f"{level}|{symbol}|{setup_type}|{direction}|{regime}|{cost_bucket}"
            ),
            evidence_source=(
                evidence_sources[0] if len(evidence_sources) == 1
                else "COMPOSITE:" + "+".join(evidence_sources)
                if evidence_sources else STATISTICS_SOURCE_VERSION
            ),
        ))
    return StatisticalHierarchy(buckets[0], tuple(buckets[1:]), outcome_count=len(rows))


class PostgresPaperOutcomeStatisticsSource:
    """Bounded adapter over the existing durable PAPER lifecycle truth."""

    def __init__(
        self, session_factory: Callable[[], Session], *, maximum_outcomes: int = 5_000,
        prospective_outcome_directory: Path | None = None,
    ) -> None:
        if maximum_outcomes <= 0:
            raise ValueError("maximum_outcomes must be positive")
        self._session_factory = session_factory
        self.maximum_outcomes = maximum_outcomes
        self.prospective_outcome_directory = prospective_outcome_directory

    def _load(self) -> tuple[PaperOutcome, ...]:
        statement = (
            select(
                PaperPositionRecord.symbol,
                PaperPositionRecord.side,
                PaperPositionRecord.realized_pnl,
                OnlinePipelineResultRow.setup_payload_json,
                OnlinePipelineResultRow.analysis_payload_json,
                OnlinePipelineResultRow.paper_payload_json,
                PaperPositionRecord.closed_at,
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
            parameter_set_id=_text(
                _nested(row.paper_payload_json, "parameter_set_id")
                or _nested(row.paper_payload_json, "runtime_parameter_set_id"),
                "LEGACY_UNATTRIBUTED",
            ).lower(),
            observed_at_ms=_utc_ms(getattr(row, "closed_at", None)),
        ) for row in rows)

    def resolve(
        self, *, symbol: str, setup_type: str, direction: str,
        regime: str = "UNKNOWN", cost_bucket: str = "UNKNOWN",
        parameter_set_id: str | None = None,
    ) -> StatisticalHierarchy:
        outcomes = self._load()
        if self.prospective_outcome_directory is not None and parameter_set_id is not None:
            outcomes += load_prospective_outcomes(
                self.prospective_outcome_directory,
                parameter_set_id=parameter_set_id,
            )
        return hierarchy_from_outcomes(
            outcomes, symbol=_text(symbol), setup_type=_text(setup_type),
            direction=_text(direction), regime=_text(regime),
            cost_bucket=_text(cost_bucket),
            parameter_set_id=parameter_set_id,
        )


__all__ = (
    "PaperOutcome", "PostgresPaperOutcomeStatisticsSource",
    "PROSPECTIVE_OUTCOME_SEMANTICS", "STATISTICS_SOURCE_VERSION",
    "StatisticalHierarchy", "hierarchy_from_outcomes", "load_prospective_outcomes",
)
