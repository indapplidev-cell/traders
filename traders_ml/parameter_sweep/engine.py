"""Manual deterministic offline parameter sweep for Scalping v2."""

from __future__ import annotations

import argparse
from collections import ChainMap
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from itertools import product
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import threading
import time
import traceback
from typing import Any, Callable, Iterator, Mapping

import yaml
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.engine import Connection, URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config.trade_parameters import (
    CONFIG_PATH, SCALPING_V2, TRADE_PARAMETERS, StalePositionPolicyParameters,
)
from app.config.yaml_authority import RESEARCH_PARAMETERS
from app.db.paper_models import (
    PaperExecutionCommandRecord, PaperOrderRecord, PaperPositionRecord,
    ScalpingOpportunityRecord, ScalpingOutcomeDiagnosticRecord,
    ScalpingStalePositionShadowRecord,
)
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket, evaluate_expectancy
from app.engine_paper.stale_position_shadow import (
    StalePositionInputs, evaluate_stale_position_shadow,
)
from .events import EventType, SweepEvent
from .artifact_writer import (
    ArtifactWriteError, DEFAULT_ARTIFACT_WRITER, DurableResultWriter,
)
from .artifact_v2 import (
    ARTIFACT_SCHEMA_VERSION, ArtifactSizeBudgetExceeded, aggregate_result_semantics,
    build_opportunity_funnel, compact_result, compact_trade, enforce_size_budget,
    iter_results,
)
from .ranking import pareto_frontier, rank_results, selection_bias_guard
from .targeted import (
    active_search_space, deduplicate_behavioral_configs, sensitivity_preflight,
    staged_candidates, validate_targeted_space,
)
from .integrity import verify_artifacts
from .historical_replay import (
    HistoricalReplayRepository, baseline_parity, build_parameter_registry,
    chronological_portfolio_replay,
)
from .locking import SingleRunLock
from .models import ReplayDiagnostics, SearchPlanState, StructuredError
from .modes import (
    ACTIVE_RESEARCH_FAMILIES, FROZEN_RESEARCH_FAMILIES, ResearchMode,
    families_for_mode, parse_research_mode,
)
from .state import RunState, StatusStore, SweepRunStatus
from .texts import ERRORS_RU
from .utils import generate_run_id

SCHEMA_VERSION = "SCALPING_V2_PARAMETER_SWEEP/3"
DATASET_MANIFEST_VERSION = "PARAMETER_SWEEP_DATASET_MANIFEST/2"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTECTED_BINDING_PATH = PROJECT_ROOT / ".env.production.local"
PROTECTED_READONLY_KEY = "TRADERS_READONLY_API_DATABASE_URL"
PROTECTED_RUNTIME_KEY = "TRADERS_PAPER_RUNTIME_DATABASE_URL"
DATASET_SOURCE = "production_paper_readonly"
LEGACY_DATASET_SOURCE = "postgres-paper-outcomes-readonly"
DEFAULT_MAX_ROWS = RESEARCH_PARAMETERS.dataset.max_rows
REQUIRED_TABLES = frozenset({
    "alembic_version", "paper_positions", "paper_orders",
    "paper_execution_commands", "online_pipeline_runs",
    "online_pipeline_results",
    "scalping_stale_position_shadow_diagnostics",
})
TIME_STOP_SEARCH_FIELDS = frozenset({
    "soft_timeout_seconds", "hard_timeout_seconds",
    "min_target_progress_at_soft_timeout", "min_mfe_bps_at_soft_timeout",
    "min_remaining_ev_r_at_soft_timeout", "extension_seconds", "max_extensions",
    "break_even_activation_target_progress", "net_break_even_protection_enabled",
})


def _search_plan_state(
    space: Mapping[str, list[object]], plan: "SearchPlan",
) -> SearchPlanState:
    dimensions = tuple(sorted(space))
    return SearchPlanState(
        search_dimensions=dimensions,
        dimension_values={name: list(space[name]) for name in dimensions},
        conditional_dimensions=tuple(sorted(TIME_STOP_SEARCH_FIELDS & space.keys())),
        raw_search_space_size=plan.raw_search_space_size,
        planned_configs=plan.evaluation_budget,
        selected_strategy=plan.selected_strategy,
    )


def _replay_diagnostics(rows: list[dict[str, Any]], coverage: Mapping[str, Any]) -> ReplayDiagnostics:
    reasons = coverage.get("REPLAY_REASON_COUNTS", {})
    summary = rows[0].get("__historical_summary", {}) if rows else {}
    return ReplayDiagnostics(
        dataset_rows=len(rows),
        outcome_replay_rows=int(coverage["OUTCOME_ONLY_REPLAY_ROWS"]),
        time_stop_replay_rows=int(coverage["TIME_STOP_REPLAY_ELIGIBLE_ROWS"]),
        full_replay_rows=int(coverage["FULL_REPLAY_ELIGIBLE_ROWS"]),
        post_instrumentation_rows=int(coverage["POST_TIME_STOP_INSTRUMENTATION_ROWS"]),
        missing_market_timeline_rows=int(reasons.get("UNREPLAYABLE_MISSING_MARKET_TIMELINE", 0)),
        missing_cost_timeline_rows=int(reasons.get("UNREPLAYABLE_MISSING_COST_TIMELINE", 0)),
        historical_market_rows=int(summary.get("MARKET_1M_ROWS", 0))+int(summary.get("MARKET_5M_ROWS", 0)),
        opportunity_universe_size=int(summary.get("TOTAL_OPPORTUNITY_UNIVERSE", 0)),
        persisted_closed_trades=int(summary.get("PERSISTED_CLOSED_POSITIONS", 0)),
        reconstructed_opportunities=int(summary.get("TOTAL_RECONSTRUCTED_ONLY_CANDIDATES", 0)),
        replay_capabilities=rows[0].get("__replay_capabilities", {}) if rows else {},
    )


def _structured_replay_error(contract_failure: str) -> StructuredError:
    code = (
        "INSUFFICIENT_REPLAY_DATA"
        if contract_failure == "NO_REPLAYABLE_ROWS_FOR_REQUIRED_DIMENSIONS"
        else contract_failure
    )
    translated = ERRORS_RU.get(code, {"title": code, "message": contract_failure})
    return StructuredError(
        error_code=code,
        error_title_ru=str(translated["title"]),
        error_message_ru=str(translated["message"]),
        error_details={"engine_reason": contract_failure},
    )

REPLAY_FIELD_CONTRACT: tuple[tuple[str, str, bool], ...] = (
    ("position_id", "position_id", True),
    ("command_id", "command_id", True),
    ("profile_id", "profile_id", True),
    ("symbol", "symbol", True),
    ("direction", "direction", True),
    ("setup_type", "setup type", False),
    ("opened_at_ms", "opened_at", True),
    ("closed_at_ms", "closed_at", True),
    ("entry_price", "entry_price", True),
    ("exit_price", "exit_price", True),
    ("stop_price", "stop_price", True),
    ("target_price", "target_price", True),
    ("gross_pnl", "gross_pnl", True),
    ("net_pnl", "net_pnl", True),
    ("entry_fee_incurred", "entry_fee", True),
    ("exit_fee_incurred", "exit_fee", True),
    ("commission_provenance", "commission provenance", False),
    ("cost_provenance", "cost provenance", False),
    ("spread_slippage_provenance", "spread/slippage provenance", False),
    ("causal_opportunity", "causal_opportunity_id", False),
    ("mae", "MAE", False),
    ("mfe", "MFE", False),
    ("market_data_watermark_ms", "market-data watermark", False),
    ("historical_observation_timestamps", "historical observation timestamps", False),
    ("time_stop_observations", "historical price/time-stop observations", False),
)

OUTCOME_REPLAY_REQUIRED = frozenset({
    "position_id", "opened_at_ms", "closed_at_ms", "entry_price", "exit_price",
    "gross_pnl", "net_pnl", "entry_fee_incurred", "exit_fee_incurred",
    "holding_time_ms", "exit_reason",
})
ENTRY_REPLAY_REQUIRED = frozenset({
    "command_id", "profile_id", "setup_type", "probability_sample_size",
    "p_win_raw", "stop_distance_bps", "target_distance_bps",
    "effective_total_cost_bps", "causal_opportunity",
})


class SweepExpectedError(ValueError):
    """A fixed, secret-free operator failure reason."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        message = (
            "invalid research search space"
            if reason == "SEARCH_SPACE_INVALID" else reason
        )
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class DatabaseBinding:
    url: URL
    source: str


@dataclass(frozen=True, slots=True)
class DatasetOptions:
    source: str = DATASET_SOURCE
    profile: str = "trade-5m-v2"
    primary_timeframe: str = "5m"
    closed_only: bool = False
    selection_mode: str = "ALL_UNTIL_CUTOFF"
    maximum_rows: int | None = DEFAULT_MAX_ROWS
    from_time: datetime | None = None
    to_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class SearchPlan:
    raw_search_space_size: int
    effective_search_space_size: int
    dimension_cardinalities: dict[str, int]
    available_replay_rows: int
    selected_strategy: str
    evaluation_budget: int
    batch_size: int
    seed: int
    staged_search_plan: tuple[dict[str, object], ...]
    reason: str
    statistical_warning: str
    promotion_eligible: bool
    estimated_active_batch_memory_mb: float
    invalid_combinations_generated: int = 0
    conditional_dimension_collapse: bool = False
    research_mode: str = ResearchMode.ALL.value
    active_families: tuple[str, ...] = ACTIVE_RESEARCH_FAMILIES

    def safe_dict(self) -> dict[str, object]:
        return {
            "RAW_SEARCH_SPACE_SIZE": self.raw_search_space_size,
            "EFFECTIVE_SEARCH_SPACE_SIZE": self.effective_search_space_size,
            "DIMENSION_COUNT": len(self.dimension_cardinalities),
            "DIMENSION_CARDINALITIES": self.dimension_cardinalities,
            "AVAILABLE_REPLAY_ROWS": self.available_replay_rows,
            "SELECTED_SEARCH_STRATEGY": self.selected_strategy,
            "EVALUATION_BUDGET": self.evaluation_budget,
            "BATCH_SIZE": self.batch_size,
            "SEED": self.seed,
            "STAGED_SEARCH_PLAN": self.staged_search_plan,
            "REASON": self.reason,
            "STATISTICAL_SEARCH_WARNING": self.statistical_warning,
            "PROMOTION_ELIGIBLE": self.promotion_eligible,
            "MEMORY_PLAN": "SAFE",
            "ESTIMATED_ACTIVE_BATCH_MEMORY_MB": self.estimated_active_batch_memory_mb,
            "CONFIG_GENERATION": "LAZY",
            "RAW_SPACE_MATERIALIZED_IN_MEMORY": "NO",
            "INVALID_COMBINATIONS_GENERATED": self.invalid_combinations_generated,
            "CONDITIONAL_DIMENSION_COLLAPSE": (
                "YES" if self.conditional_dimension_collapse else "NO"
            ),
            "RESEARCH_MODE": self.research_mode,
            "ACTIVE_FAMILIES": self.active_families,
            "FROZEN_FAMILIES": FROZEN_RESEARCH_FAMILIES,
        }


class ParameterSweepSearchPlanner:
    """Transparent deterministic planner for exhaustive or bounded exploration."""

    BYTES_PER_ACTIVE_CONFIG = RESEARCH_PARAMETERS.search.bytes_per_active_config
    MAX_ACTIVE_BATCH_MEMORY_MB = RESEARCH_PARAMETERS.search.max_active_batch_memory_mb

    @staticmethod
    def raw_cardinality(space: Mapping[str, list[object]]) -> int:
        return math.prod(len(values) for values in space.values())

    def plan(
        self, *, dataset_rows: int, space: Mapping[str, list[object]],
        search: Mapping[str, object], max_configs_override: int | None = None,
        validation_rows: int = 0, holdout_rows: int = 0,
        available_replay_rows: int = 0,
        mode: ResearchMode = ResearchMode.ALL,
    ) -> SearchPlan:
        raw = self.raw_cardinality(space)
        effective = _effective_cardinality(space)
        if effective < 1:
            raise SweepExpectedError("SEARCH_SPACE_INVALID")
        strategy = str(search["strategy"]).lower()
        if strategy not in {"auto", "exhaustive", "bounded", "targeted"}:
            raise SweepExpectedError("SEARCH_SPACE_INVALID")
        seed = int(search["seed"])
        exhaustive_threshold = int(search["exhaustive_max_configs"])
        configured_budget = min(int(search["max_evaluated_configs"]), int(search.get("max_total_configs", search["max_evaluated_configs"])))
        per_observation = float(search["max_configs_per_observation"])
        statistical_cap = max(1, int(dataset_rows * per_observation))
        budget = min(effective, configured_budget, statistical_cap)
        if max_configs_override is not None:
            if max_configs_override <= 0:
                raise SweepExpectedError("SEARCH_SPACE_INVALID")
            budget = min(budget, max_configs_override)
        exhaustive = effective <= exhaustive_threshold and strategy not in {"bounded", "targeted"}
        if strategy == "exhaustive" and effective > exhaustive_threshold:
            raise SweepExpectedError("UNSAFE_EXHAUSTIVE_SEARCH")
        selected = "TARGETED_STAGED" if strategy == "targeted" else ("EXHAUSTIVE_LAZY" if exhaustive else "AUTO_BOUNDED")
        requested_batch = int(search["batch_size"])
        safe_batch = int(
            self.MAX_ACTIVE_BATCH_MEMORY_MB * 1024 * 1024
            / self.BYTES_PER_ACTIVE_CONFIG
        )
        batch = min(requested_batch, safe_batch, budget)
        if batch < 1:
            raise SweepExpectedError("UNSAFE_MEMORY_PLAN")
        if strategy == "targeted":
            configured_stages = search.get("stage_budgets", {})
            remaining = budget
            stage_rows = []
            for name in ("SET2_BASELINE", "ONE_FACTOR_SENSITIVITY", "SMALL_FAMILY_SEARCH", "TOP_REGION_REFINEMENT", "LOCAL_FINALIST_VALIDATION"):
                count = min(remaining, int(configured_stages.get(name, 0)))
                stage_rows.append({"stage": name, "budget": count, "uses_holdout": False})
                remaining -= count
            stages = tuple(stage_rows)
        else:
            fractions = (
                float(search.get("stage1_fraction", .6)),
                float(search.get("stage2_fraction", .3)),
                float(search.get("stage3_fraction", .1)),
            )
            if any(value < 0 for value in fractions) or not math.isclose(sum(fractions), 1.0):
                raise SweepExpectedError("SEARCH_SPACE_INVALID")
            counts = [int(budget * fractions[0]), int(budget * fractions[1])]
            counts.append(budget - sum(counts))
            stages = tuple({"stage": name, "budget": count, "uses_holdout": False} for name, count in zip(("BROAD_EXPLORATION", "VALIDATION_REFINEMENT", "LOCAL_REFINEMENT"), counts, strict=True))
        minimum_validation = int(search["minimum_validation_sample"])
        minimum_holdout = int(search["minimum_holdout_sample"])
        warning = (
            "LARGE_HYPOTHESIS_SPACE_SMALL_SAMPLE"
            if raw > exhaustive_threshold and dataset_rows < configured_budget else "NONE"
        )
        promotion = (
            warning == "NONE" and validation_rows >= minimum_validation
            and holdout_rows >= minimum_holdout and budget == effective
        )
        return SearchPlan(
            raw, effective,
            {name: len(values) for name, values in sorted(space.items())},
            available_replay_rows, selected, budget, batch, seed, stages,
            "RAW_SPACE_WITHIN_EXHAUSTIVE_THRESHOLD" if exhaustive
            else "RAW_SPACE_EXCEEDS_SAFE_EXHAUSTIVE_THRESHOLD",
            warning, promotion,
            round(batch * self.BYTES_PER_ACTIVE_CONFIG / 1024 / 1024, 3),
            0, effective < raw, mode.value, families_for_mode(mode),
        )


def _conditional_variants(space: Mapping[str, list[object]]) -> tuple[dict[str, object], ...]:
    names = tuple(sorted(TIME_STOP_SEARCH_FIELDS & space.keys()))
    if not names:
        return ({},)
    variants: list[dict[str, object]] = []
    seen: set[str] = set()
    for values in product(*(space[name] for name in names)):
        item = dict(zip(names, values, strict=True))
        if {
            "soft_timeout_seconds", "hard_timeout_seconds",
        } <= item.keys() and int(item["soft_timeout_seconds"]) >= int(item["hard_timeout_seconds"]):
            continue
        if "max_extensions" in item and "extension_seconds" in item:
            if int(item["max_extensions"]) == 0:
                item["extension_seconds"] = 0
            if int(item["extension_seconds"]) == 0:
                item["max_extensions"] = 0
        if item.get("net_break_even_protection_enabled") is False:
            item["break_even_activation_target_progress"] = space[
                "break_even_activation_target_progress"
            ][0]
        try:
            _stale_policy(item)
        except (KeyError, TypeError, ValueError):
            # Partial spaces are validated by the caller; complete known-invalid
            # relationships never become generated candidates.
            if names == tuple(sorted(TIME_STOP_SEARCH_FIELDS)):
                continue
        identity = json.dumps(item, sort_keys=True, separators=(",", ":"))
        if identity not in seen:
            seen.add(identity)
            variants.append(item)
    return tuple(variants)


def _effective_cardinality(space: Mapping[str, list[object]]) -> int:
    independent = {
        name: values for name, values in space.items()
        if name not in TIME_STOP_SEARCH_FIELDS
    }
    conditional = _conditional_variants(space)
    if TIME_STOP_SEARCH_FIELDS & space.keys() and not conditional:
        return 0
    return math.prod(len(values) for values in independent.values()) * len(conditional or ({},))


def _config_from_index(
    space: Mapping[str, list[object]], index: int,
) -> dict[str, object]:
    result: dict[str, object] = {}
    for name in sorted(space, reverse=True):
        values = space[name]
        index, offset = divmod(index, len(values))
        result[name] = values[offset]
    return {name: result[name] for name in sorted(result)}


def _candidate_indices(plan: SearchPlan) -> Iterator[int]:
    """Lazy reproducible full-cycle permutation with O(1) active state."""
    size = plan.effective_search_space_size
    if plan.selected_strategy == "EXHAUSTIVE_LAZY":
        yield from range(size)
        return
    rng = random.Random(plan.seed)
    start = rng.randrange(size)
    step = rng.randrange(1, size)
    while math.gcd(step, size) != 1:
        step = (step + 1) % size or 1
    for offset in range(size):
        yield (start + offset * step) % size


def _candidate_config(
    space: Mapping[str, list[object]], effective_index: int,
    *, conditional_variants: tuple[dict[str, object], ...] | None = None,
) -> dict[str, object]:
    variants = conditional_variants or _conditional_variants(space)
    independent = {
        name: values for name, values in space.items()
        if name not in TIME_STOP_SEARCH_FIELDS
    }
    independent_index, variant_index = divmod(effective_index, len(variants))
    result = _config_from_index(independent, independent_index) if independent else {}
    result.update(variants[variant_index])
    return {name: result[name] for name in sorted(result)}


def _parse_utc(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        raise SweepExpectedError("INVALID_DATE_RANGE") from None


def _safe_url(value: str) -> URL:
    try:
        url = make_url(value)
    except Exception:
        raise SweepExpectedError("PROJECT_DATABASE_BINDING_NOT_AVAILABLE") from None
    if url.get_backend_name() != "postgresql" or not url.database:
        raise SweepExpectedError("PROJECT_DATABASE_BINDING_NOT_AVAILABLE")
    return url


def _protected_values(path: Path) -> dict[str, str]:
    """Read only the allowlisted existing binding; never return it to output."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError):
        return {}
    allowed = {PROTECTED_READONLY_KEY, PROTECTED_RUNTIME_KEY}
    values: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in allowed and value:
            values[key] = value
    return values


def resolve_database_binding(
    *, explicit_url: str | None = None,
    protected_path: Path = PROTECTED_BINDING_PATH,
    environment: Mapping[str, str] | None = None,
) -> DatabaseBinding:
    """Resolve explicit, protected-project, then compatibility environment binding."""
    if explicit_url:
        return DatabaseBinding(_safe_url(explicit_url), "EXPLICIT_CLI_OVERRIDE")
    protected = _protected_values(protected_path)
    readonly_value = protected.get(PROTECTED_READONLY_KEY)
    if readonly_value:
        readonly_url = _safe_url(readonly_value)
        runtime_value = protected.get(PROTECTED_RUNTIME_KEY)
        if runtime_value:
            runtime_url = _safe_url(runtime_value)
            # The protected readonly URL is container-native; reuse the already
            # protected host endpoint without copying or publishing credentials.
            if readonly_url.host not in {"127.0.0.1", "localhost", "::1"}:
                readonly_url = readonly_url.set(
                    host=runtime_url.host, port=runtime_url.port,
                )
        return DatabaseBinding(readonly_url, "PROJECT_PROTECTED_BINDING")
    env = os.environ if environment is None else environment
    compatibility = env.get("DATABASE_URL")
    if compatibility:
        return DatabaseBinding(_safe_url(compatibility), "DATABASE_URL_ENVIRONMENT")
    raise SweepExpectedError("PROJECT_DATABASE_BINDING_NOT_AVAILABLE")


class ReadOnlyResearchDatabase:
    """SELECT-only adapter backed by a PostgreSQL session-level write guard."""

    def __init__(self, binding: DatabaseBinding) -> None:
        try:
            self.engine = create_engine(binding.url, hide_parameters=True, pool_pre_ping=True)
        except Exception:
            raise SweepExpectedError("DATABASE_CONNECTION_FAILED") from None
        self.binding_source = binding.source

        @event.listens_for(self.engine, "connect")
        def _force_read_only(dbapi_connection: object, _record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            try:
                cursor.execute("SET default_transaction_read_only = on")
            finally:
                cursor.close()

    @contextmanager
    def connection(self) -> Iterator[Connection]:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                yield connection
                connection.rollback()
        except SweepExpectedError:
            raise
        except SQLAlchemyError:
            raise SweepExpectedError("DATABASE_CONNECTION_FAILED") from None

    @staticmethod
    def _assert_select(statement: object) -> None:
        if getattr(statement, "is_select", False):
            return
        rendered = str(statement).lstrip().upper()
        if rendered.startswith(("SELECT ", "WITH ", "SHOW ")):
            return
        raise SweepExpectedError("PRODUCTION_MUTATION_GUARD_REJECTED_WRITE")

    def execute_select(self, connection: Connection, statement: object):
        self._assert_select(statement)
        return connection.execute(statement)  # type: ignore[arg-type]

    def dispose(self) -> None:
        self.engine.dispose()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _nested(value: object, *path: str) -> object | None:
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _shadow_observation(
    shadow: ScalpingStalePositionShadowRecord,
    position: PaperPositionRecord,
) -> dict[str, Any]:
    entry = Decimal(position.average_entry_price)
    quantity = Decimal(position.entry_quantity)
    notional = Decimal(shadow.current_price) * quantity
    long = position.side == "LONG"
    mfe = Decimal(shadow.mfe_bps)
    mae = Decimal(shadow.mae_bps)
    high = entry * (Decimal("1") + (mfe if long else mae) / Decimal(10_000))
    low = entry * (Decimal("1") - (mae if long else mfe) / Decimal(10_000))

    def bps(amount: Decimal) -> float | None:
        return None if notional <= 0 else float(amount / notional * Decimal(10_000))

    provenance = shadow.provenance if isinstance(shadow.provenance, dict) else {}
    commission = provenance.get("commission", {})
    source = commission.get("source") if isinstance(commission, dict) else None
    return {
        "evaluation_time_ms": int(shadow.evaluated_at.timestamp() * 1000),
        "evaluation_closed_until_ms": int(shadow.evaluation_closed_until_ms),
        "current_price": float(shadow.current_price),
        "highs": [float(high)], "lows": [float(low)],
        "exit_commission_bps": bps(Decimal(shadow.expected_exit_commission)),
        "spread_bps": bps(Decimal(shadow.spread_cost)),
        "slippage_bps": bps(Decimal(shadow.slippage_cost)),
        "adverse_exit_reserve_bps": bps(Decimal(shadow.adverse_exit_reserve)),
        "setup_valid": shadow.setup_valid,
        "momentum_valid": shadow.momentum_valid,
        "remaining_ev_r": (
            None if shadow.remaining_ev_r is None else float(shadow.remaining_ev_r)
        ),
        "historical_cost_evidence": bool(source),
        "commission_source": source,
        "target_progress": float(shadow.target_progress),
        "mfe_bps": float(shadow.mfe_bps), "mae_bps": float(shadow.mae_bps),
        "estimated_net_exit_pnl": float(shadow.estimated_net_exit_pnl),
        "shadow_decision": shadow.shadow_decision,
        "hypothetical_exit_price": (
            None if shadow.shadow_exit_price is None else float(shadow.shadow_exit_price)
        ),
        "hypothetical_exit_costs": (
            None if shadow.shadow_fees is None else float(shadow.shadow_fees)
        ),
        "reason": shadow.shadow_exit_reason or shadow.decision_reason,
        "source": "scalping_stale_position_shadow_diagnostics",
    }


def _production_rows(
    database: ReadOnlyResearchDatabase,
    options: DatasetOptions,
) -> list[dict[str, Any]]:
    """Load the v2 opportunity universe, never a positions-only dataset."""
    if options.selection_mode not in {"ALL_UNTIL_CUTOFF", "LATEST_N_UNTIL_CUTOFF"}:
        raise SweepExpectedError("DATASET_SELECTION_MODE_INVALID")
    if options.selection_mode == "LATEST_N_UNTIL_CUTOFF" and (
        options.maximum_rows is None or options.maximum_rows < 1
    ):
        raise SweepExpectedError("MAX_ROWS_OUT_OF_RANGE")
    repository = HistoricalReplayRepository(database)
    dataset = repository.load(
        maximum_rows=options.maximum_rows,
        selection_mode=options.selection_mode,
        from_ms=None if options.from_time is None else int(options.from_time.timestamp() * 1000),
        to_ms=None if options.to_time is None else int(options.to_time.timestamp() * 1000),
    )
    repository.load_paths(dataset.rows, horizon_seconds=3600)
    if dataset.rows:
        dataset.rows[0]["__historical_summary"] = dataset.summary
        dataset.rows[0]["__replay_capabilities"] = dataset.capabilities
        dataset.rows[0]["__baseline_positions"] = dataset.baseline_positions
        dataset.rows[0]["__source_inventory"] = dataset.inventory
        dataset.rows[0]["__dataset_fingerprint"] = dataset.fingerprint
    return dataset.rows


def _legacy_production_rows(
    database: ReadOnlyResearchDatabase,
    options: DatasetOptions,
) -> list[dict[str, Any]]:
    """Legacy closed-position loader retained only for fixture compatibility."""
    statement = (
        select(
            PaperPositionRecord, PaperExecutionCommandRecord,
            OnlinePipelineResultRow, ScalpingOutcomeDiagnosticRecord,
            ScalpingOpportunityRecord,
        )
        .join(PaperOrderRecord, PaperOrderRecord.order_id == PaperPositionRecord.entry_order_id)
        .join(PaperExecutionCommandRecord, PaperExecutionCommandRecord.command_id == PaperOrderRecord.command_id)
        .join(OnlinePipelineRun, OnlinePipelineRun.run_id == PaperExecutionCommandRecord.pipeline_run_id)
        .join(OnlinePipelineResultRow, OnlinePipelineResultRow.run_id == OnlinePipelineRun.run_id)
        .outerjoin(ScalpingOutcomeDiagnosticRecord,
                   ScalpingOutcomeDiagnosticRecord.position_id == PaperPositionRecord.position_id)
        .outerjoin(ScalpingOpportunityRecord,
                   ScalpingOpportunityRecord.position_id == PaperPositionRecord.position_id)
        .where(OnlinePipelineRun.trade_profile_id == options.profile)
        .order_by(PaperPositionRecord.closed_at.desc())
        .limit(options.maximum_rows)
    )
    if options.closed_only:
        statement = statement.where(PaperPositionRecord.state == "CLOSED")
    if options.from_time is not None:
        statement = statement.where(PaperPositionRecord.opened_at >= options.from_time)
    if options.to_time is not None:
        statement = statement.where(PaperPositionRecord.closed_at <= options.to_time)
    with database.connection() as connection, Session(
        bind=connection, autoflush=False, expire_on_commit=False,
    ) as session:
        database._assert_select(statement)
        records = tuple(session.execute(statement))
        position_ids = tuple({record[0].position_id for record in records})
        shadow_records = tuple(session.scalars(
            select(ScalpingStalePositionShadowRecord)
            .where(ScalpingStalePositionShadowRecord.position_id.in_(position_ids))
            .order_by(
                ScalpingStalePositionShadowRecord.position_id,
                ScalpingStalePositionShadowRecord.evaluation_closed_until_ms,
            )
        )) if position_ids else ()
    shadows_by_position: dict[str, list[ScalpingStalePositionShadowRecord]] = {}
    for shadow in shadow_records:
        shadows_by_position.setdefault(shadow.position_id, []).append(shadow)
    rows: list[dict[str, Any]] = []
    for position, command, result, outcome, opportunity in records:
        diagnostic = _nested(
            result.paper_payload_json, "paper_context", "scalping_geometry_diagnostics"
        ) or {}
        fees = float(position.entry_fees + position.exit_fees)
        net_pnl = float(position.realized_pnl or 0)
        shadow_observations = [
            _shadow_observation(shadow, position)
            for shadow in shadows_by_position.get(position.position_id, ())
            if int(shadow.evaluation_closed_until_ms) <= int(position.closed_at.timestamp() * 1000)
        ]
        commission_provenance = diagnostic.get("commission_provenance")
        rows.append({
            "profile_id": options.profile,
            "position_id": position.position_id,
            "command_id": command.command_id,
            "opened_at_ms": int(position.opened_at.timestamp() * 1000),
            "closed_at_ms": int(position.closed_at.timestamp() * 1000),
            "net_pnl": net_pnl, "gross_pnl": net_pnl + fees, "fees": fees,
            "exit_reason": position.reason_code,
            "holding_time_ms": int((position.closed_at - position.opened_at).total_seconds() * 1000),
            "mae": None if outcome is None else float(outcome.mae),
            "mfe": None if outcome is None else float(outcome.mfe),
            "symbol": position.symbol, "direction": position.side,
            "entry_price": float(position.average_entry_price),
            "exit_price": float(position.average_exit_price),
            "setup_type": _nested(result.setup_payload_json, "setup_type") or "UNKNOWN",
            "setup": result.setup_payload_json,
            "causal_opportunity": (
                None if opportunity is None else opportunity.causal_opportunity_id
            ),
            "cost_provenance": {
                "fee_policy_id": command.fee_policy_id,
                "slippage_policy_id": command.slippage_policy_id,
                "diagnostics": diagnostic.get("commission_provenance"),
            },
            "commission_provenance": commission_provenance,
            "spread_slippage_provenance": {
                "slippage_policy_id": command.slippage_policy_id,
                "effective_total_cost_bps": diagnostic.get("effective_total_cost_bps"),
            },
            "probability_ev_provenance": {
                "configuration_fingerprint": command.configuration_fingerprint,
                "probability_sample_size": diagnostic.get("probability_sample_size", 0),
                "p_win_raw": diagnostic.get("p_win_raw", diagnostic.get("estimated_p_win")),
                "expected_ev_r": diagnostic.get("expected_ev_r"),
            },
            "session": "UTC", "rejection_reason": diagnostic.get("rejection_reason"),
            "p_win_raw": diagnostic.get("p_win_raw", diagnostic.get("estimated_p_win")),
            "probability_sample_size": diagnostic.get("probability_sample_size", 0),
            "stop_distance_bps": diagnostic.get("stop_distance_bps"),
            "target_distance_bps": diagnostic.get("target_distance_bps"),
            "effective_total_cost_bps": diagnostic.get("effective_total_cost_bps"),
            "adverse_fill_reserve_bps": diagnostic.get("adverse_fill_reserve_bps", 0),
            "entry_slippage_bps": diagnostic.get("entry_slippage_bps", 0),
            "quantity": float(position.entry_quantity),
            "stop_price": float(position.stop_price),
            "target_price": float(position.target_price),
            "entry_fee_incurred": float(position.entry_fees),
            "exit_fee_incurred": float(position.exit_fees),
            "market_data_watermark_ms": result.closed_until_ms,
            "historical_observation_timestamps": [
                item["evaluation_time_ms"] for item in shadow_observations
            ],
            # Reuse the authoritative persisted SHADOW observations. Current
            # market prices or current commission are never substituted.
            "time_stop_observations": shadow_observations,
            "causal_reset_conditions": 1,
            "one_min_confirmation_count": 1,
        })
    return rows


def _load_rows(
    options: DatasetOptions, database: ReadOnlyResearchDatabase | None,
) -> list[dict[str, Any]]:
    if options.source in {DATASET_SOURCE, LEGACY_DATASET_SOURCE}:
        if database is None:
            raise SweepExpectedError("PROJECT_DATABASE_BINDING_NOT_AVAILABLE")
        return _production_rows(database, options)
    value = _json(Path(options.source))
    if not isinstance(value, list):
        raise SweepExpectedError("DATASET_INVALID")
    return value


def _validate_dataset_authority(
    rows: list[dict[str, Any]], options: DatasetOptions,
) -> None:
    for row in rows:
        if row.get("profile_id") != options.profile:
            raise SweepExpectedError("DATASET_PROFILE_MISMATCH")
        if row.get("primary_timeframe") != options.primary_timeframe:
            raise SweepExpectedError("DATASET_TIMEFRAME_MISMATCH")


def _config_hash(value: object) -> str:
    return sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), default=str,
    ).encode()).hexdigest()


def _snapshot_json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return {"__parameter_sweep_type__": "decimal", "value": str(value)}
    if isinstance(value, datetime):
        return {"__parameter_sweep_type__": "datetime", "value": value.isoformat()}
    raise TypeError(f"unsupported frozen dataset value: {type(value).__name__}")


def _snapshot_json_hook(value: dict[str, Any]) -> object:
    if value.get("__parameter_sweep_type__") == "decimal":
        return Decimal(str(value["value"]))
    if value.get("__parameter_sweep_type__") == "datetime":
        return datetime.fromisoformat(str(value["value"]))
    return value


def _manifest_from_rows(
    *, run_id: str, options: DatasetOptions, rows: list[dict[str, Any]],
    schema_head: str,
) -> dict[str, Any]:
    summary = rows[0].get("__historical_summary", {}) if rows else {}
    inventory = rows[0].get("__source_inventory", []) if rows else []
    opened = [int(row.get("opened_at_ms", row.get("boundary_ms", 0))) for row in rows]
    closed = [int(row.get("closed_at_ms", row.get("boundary_ms", 0))) for row in rows]
    period_start = int(summary.get("HISTORICAL_PERIOD_START_MS") or min(opened))
    period_end = int(summary.get("HISTORICAL_PERIOD_END_MS") or max(closed))
    dataset_fingerprint = _config_hash({
        "manifest_version": DATASET_MANIFEST_VERSION,
        "source": options.source,
        "profile": options.profile,
        "primary_timeframe": options.primary_timeframe,
        "schema_head": schema_head,
        "rows": rows,
    })
    manifest = {
        "manifest_version": DATASET_MANIFEST_VERSION,
        "run_id": run_id,
        "profile": options.profile,
        "primary_timeframe": options.primary_timeframe,
        "baseline_set_id": RESEARCH_PARAMETERS.calibration.baseline_set_id,
        "symbols": sorted({str(row.get("symbol")) for row in rows if row.get("symbol")}),
        "historical_period_start_ms": period_start,
        "historical_period_end_ms": period_end,
        "dataset_cutoff_at": datetime.fromtimestamp(period_end / 1000, timezone.utc).isoformat(),
        "dataset_source": options.source,
        "dataset_row_count": len(rows),
        "selection_mode": options.selection_mode,
        "requested_max_rows": options.maximum_rows,
        "total_eligible_rows": int(summary.get("TOTAL_OPPORTUNITY_UNIVERSE", len(rows))),
        "loaded_rows": len(rows),
        "cutoff": datetime.fromtimestamp(period_end / 1000, timezone.utc).isoformat(),
        "first_loaded_boundary": min(opened),
        "last_loaded_boundary": max(closed),
        "latest_eligible_boundary": int(summary.get("LATEST_ELIGIBLE_BOUNDARY_MS", max(closed))),
        "omitted_older_rows": int(summary.get("OMITTED_OLDER_ROWS", 0)),
        "omitted_newer_rows": int(summary.get("OMITTED_NEWER_ROWS", 0)),
        "pagination": {
            "mode": "DETERMINISTIC_STREAMING_FETCHMANY",
            "stable_order": ["closed_until_ms", "symbol", "run_id"],
            "page_size": int(summary.get("STREAM_CHUNK_SIZE", len(rows))),
        },
        "composition": {
            "profile": {options.profile: len(rows)},
            "primary_timeframe": {options.primary_timeframe: len(rows)},
            "configuration_fingerprint": dict(sorted(_distribution(rows, "configuration_fingerprint").items())),
            "parameter_set_id": dict(sorted(_distribution(rows, "parameter_set_id").items())),
            "cost_provenance": dict(sorted(_distribution(rows, "cost_provenance").items())),
            "time_period_utc_date": dict(sorted(
                _distribution([
                    {"period": datetime.fromtimestamp(int(row.get("boundary_ms", row.get("opened_at_ms", 0))) / 1000, timezone.utc).date().isoformat()}
                    for row in rows
                ], "period").items()
            )),
        },
        "dataset_fingerprint": dataset_fingerprint,
        "source_schema_version": schema_head,
        "trade_config_version": TRADE_PARAMETERS.config_version,
        "trade_config_hash": TRADE_PARAMETERS.config_hash,
        "source_watermarks": {
            str(item.get("SOURCE")): {
                "table": item.get("TABLE_MODEL"),
                "timestamp_field": item.get("TIMESTAMP_FIELD"),
                "maximum_timestamp": (item.get("TIME_RANGE") or [None, None])[1],
                "row_count": item.get("ROW_COUNT"),
                "primary_key": item.get("PRIMARY_KEY"),
                "watermark_field": item.get("WATERMARK_FIELD"),
            }
            for item in inventory
        },
        "snapshot_file": "DATASET_SNAPSHOT.json",
    }
    manifest["manifest_hash"] = _config_hash(manifest)
    return manifest


def _present(row: Mapping[str, Any], field: str) -> bool:
    value = row.get(field)
    return value is not None and value != "" and value != [] and value != {}


def _has_fields(row: Mapping[str, Any], fields: frozenset[str]) -> bool:
    return all(_present(row, field) for field in fields)


def _observation_capability(row: Mapping[str, Any]) -> tuple[bool, bool]:
    observations = row.get("time_stop_observations")
    if not isinstance(observations, list) or not observations:
        return False, False
    market = all(
        isinstance(item, dict)
        and all(item.get(field) is not None for field in (
            "evaluation_time_ms", "evaluation_closed_until_ms", "current_price",
            "highs", "lows",
        ))
        for item in observations
    )
    costs = all(
        isinstance(item, dict)
        and item.get("historical_cost_evidence") is True
        and all(item.get(field) is not None for field in (
            "exit_commission_bps", "spread_bps", "slippage_bps",
            "adverse_exit_reserve_bps", "commission_source",
        ))
        for item in observations
    )
    return market, costs


def _replay_reason(row: Mapping[str, Any]) -> str:
    if not _has_fields(row, OUTCOME_REPLAY_REQUIRED):
        if not _present(row, "entry_price") or not _present(row, "opened_at_ms"):
            return "UNREPLAYABLE_MISSING_ENTRY_PROVENANCE"
        return "UNREPLAYABLE_MISSING_EXIT_PROVENANCE"
    market, costs = _observation_capability(row)
    if not market:
        return "UNREPLAYABLE_MISSING_MARKET_TIMELINE"
    if not costs:
        return "UNREPLAYABLE_MISSING_COST_TIMELINE"
    return "REPLAYABLE"


def _dataset_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if rows and "boundary_ms" in rows[0]:
        market = sum(bool(row.get("market_path_1m")) for row in rows)
        cost = sum(bool(row.get("cost_provenance")) for row in rows)
        full = sum(
            bool(row.get("market_path_1m")) and row.get("entry_price") is not None
            and row.get("stop_price") is not None and row.get("target_price") is not None
            and bool(row.get("cost_provenance")) for row in rows
        )
        return {
            "FIELD_COVERAGE": [], "BASELINE_REPLAY_ELIGIBLE_ROWS": full,
            "OUTCOME_ONLY_REPLAY_ROWS": full,
            "ENTRY_ADMISSION_REPLAY_ELIGIBLE_ROWS": len(rows),
            "TIME_STOP_REPLAY_ELIGIBLE_ROWS": full,
            "COST_REPLAY_ELIGIBLE_ROWS": cost,
            "MAE_MFE_REPLAY_ELIGIBLE_ROWS": market,
            "FULL_REPLAY_ELIGIBLE_ROWS": full,
            "UNREPLAYABLE_ROWS": len(rows)-full,
            "REPLAY_REASON_COUNTS": {
                "REPLAYABLE_RECONSTRUCTED_FROM_MARKET_HISTORY": full,
                "UNAVAILABLE_OPTIONAL_FAMILY_ROWS": len(rows)-full,
            },
            "PRE_TIME_STOP_INSTRUMENTATION_ROWS": len(rows),
            "POST_TIME_STOP_INSTRUMENTATION_ROWS": 0,
        }
    total = len(rows)
    matrix = []
    for field, label, required in REPLAY_FIELD_CONTRACT:
        present = sum(_present(row, field) for row in rows)
        matrix.append({
            "FIELD": label, "ROWS_PRESENT": present,
            "ROWS_MISSING": total - present,
            "COVERAGE_PERCENT": round(present / total * 100, 3) if total else 0.0,
            "REPLAY_REQUIRED": "YES" if required else "CAPABILITY_DEPENDENT",
        })
    outcome = sum(_has_fields(row, OUTCOME_REPLAY_REQUIRED) for row in rows)
    entry = sum(_has_fields(row, ENTRY_REPLAY_REQUIRED) for row in rows)
    market_cost = [
        _observation_capability(row) for row in rows
    ]
    time_stop = sum(market and costs for market, costs in market_cost)
    mae_mfe = sum(
        _present(row, "mae") and _present(row, "mfe") for row in rows
    )
    full = sum(
        _has_fields(row, OUTCOME_REPLAY_REQUIRED)
        and _has_fields(row, ENTRY_REPLAY_REQUIRED)
        and market and costs
        for row, (market, costs) in zip(rows, market_cost, strict=True)
    )
    reasons = _distribution(
        [{"reason": _replay_reason(row)} for row in rows], "reason"
    )
    post = sum(bool(row.get("time_stop_observations")) for row in rows)
    return {
        "FIELD_COVERAGE": matrix,
        "BASELINE_REPLAY_ELIGIBLE_ROWS": outcome,
        "OUTCOME_ONLY_REPLAY_ROWS": outcome,
        "ENTRY_ADMISSION_REPLAY_ELIGIBLE_ROWS": entry,
        "TIME_STOP_REPLAY_ELIGIBLE_ROWS": time_stop,
        "COST_REPLAY_ELIGIBLE_ROWS": sum(costs for _market, costs in market_cost),
        "MAE_MFE_REPLAY_ELIGIBLE_ROWS": mae_mfe,
        "FULL_REPLAY_ELIGIBLE_ROWS": full,
        "UNREPLAYABLE_ROWS": total - time_stop,
        "REPLAY_REASON_COUNTS": reasons,
        "PRE_TIME_STOP_INSTRUMENTATION_ROWS": total - post,
        "POST_TIME_STOP_INSTRUMENTATION_ROWS": post,
    }


def _production_baseline_config() -> dict[str, object]:
    economics = SCALPING_V2.economics
    costs = SCALPING_V2.costs
    geometry = SCALPING_V2.geometry
    stale = SCALPING_V2.exit_policy.stale_position
    return {
        "risk_per_trade_bps": SCALPING_V2.risk.risk_per_trade_bps,
        "max_open_positions": SCALPING_V2.risk.max_open_positions,
        "total_open_risk_limit_bps": SCALPING_V2.risk.total_open_risk_limit_bps,
        "max_new_commands_per_cycle": SCALPING_V2.risk.max_new_commands_per_cycle,
        "minimum_planned_rr": geometry.minimum_planned_rr,
        "min_positive_ev_r": economics.min_positive_ev_r,
        "min_ev_reserve_r": economics.min_ev_reserve_r,
        "min_net_edge_bps": economics.min_net_edge_bps,
        "bucket_min_sample": economics.bucket_min_sample,
        "probability_confidence_level": economics.probability_confidence_level,
        "prior_alpha": economics.prior_alpha, "prior_beta": economics.prior_beta,
        "adverse_fill_reserve_bps": costs.adverse_fill_reserve_bps,
        "entry_slippage_bps": costs.entry_slippage_bps,
        "stop_max_bps": geometry.stop_max_bps,
        "target_min_bps": geometry.target_min_bps,
        "causal_reset_min_conditions": SCALPING_V2.causal_opportunity.reset_min_conditions,
        "entry_refinement_1m_confirmation_count": SCALPING_V2.signal.confirmation_window_candles,
        "strategy_minimum_score": SCALPING_V2.signal.strategy_minimum_score,
        "regime_lookback_candles": SCALPING_V2.signal.regime_lookback_candles,
        **{
            field: getattr(stale, field) for field in TIME_STOP_SEARCH_FIELDS
        },
    }


def _baseline_control(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if rows and "boundary_ms" in rows[0]:
        config = _production_baseline_config()
        config.update({
            "risk_per_trade_bps": SCALPING_V2.risk.risk_per_trade_bps,
            "max_open_positions": SCALPING_V2.risk.max_open_positions,
            "total_open_risk_limit_bps": SCALPING_V2.risk.total_open_risk_limit_bps,
            "max_new_commands_per_cycle": SCALPING_V2.risk.max_new_commands_per_cycle,
            "minimum_planned_rr": SCALPING_V2.geometry.minimum_planned_rr,
        })
        simulated = chronological_portfolio_replay(rows, config)
        parity = baseline_parity(simulated, list(rows[0].get("__baseline_positions", [])))
        return {
            "BASELINE_CONFIG_HASH": TRADE_PARAMETERS.config_hash,
            "BASELINE_CONFIG_VERSION": TRADE_PARAMETERS.config_version,
            "BASELINE_EVALUATED": "YES", "BASELINE_DATASET_ROWS": len(rows),
            "BASELINE_ELIGIBLE_ROWS": simulated["trade_count"],
            "BASELINE_TRADES": simulated["trade_count"],
            "BASELINE_WIN_RATE": simulated["win_rate"],
            "BASELINE_GROSS_PNL": simulated["gross_pnl"],
            "BASELINE_FEES": simulated["fees"], "BASELINE_NET_PNL": simulated["net_pnl"],
            "BASELINE_NET_EXPECTANCY": simulated["net_expectancy_per_trade"],
            "BASELINE_PROFIT_FACTOR": simulated["profit_factor"],
            "BASELINE_MAX_DRAWDOWN": simulated["max_drawdown"],
            "BASELINE_AVG_HOLDING_SECONDS": simulated["average_holding_seconds"],
            "BASELINE_STOP_COUNT": simulated["stop_count"],
            "BASELINE_TARGET_COUNT": simulated["target_count"],
            "BASELINE_REPLAY_VALID": simulated["trade_count"] > 0,
            "PARAMETERS": config, "PARITY": parity,
        }
    eligible = [row for row in rows if _has_fields(row, OUTCOME_REPLAY_REQUIRED)]
    metrics = _metrics(eligible)
    return {
        "BASELINE_CONFIG_HASH": TRADE_PARAMETERS.config_hash,
        "BASELINE_CONFIG_VERSION": TRADE_PARAMETERS.config_version,
        "BASELINE_EVALUATED": "YES",
        "BASELINE_DATASET_ROWS": len(rows),
        "BASELINE_ELIGIBLE_ROWS": len(eligible),
        "BASELINE_TRADES": metrics["trade_count"],
        "BASELINE_WIN_RATE": metrics["win_rate"],
        "BASELINE_GROSS_PNL": metrics["gross_pnl"],
        "BASELINE_FEES": metrics["fees"],
        "BASELINE_NET_PNL": metrics["net_pnl"],
        "BASELINE_NET_EXPECTANCY": metrics["net_expectancy_per_trade"],
        "BASELINE_PROFIT_FACTOR": metrics["profit_factor"],
        "BASELINE_MAX_DRAWDOWN": metrics["max_drawdown"],
        "BASELINE_AVG_HOLDING_SECONDS": (
            None if metrics["average_holding_time"] is None
            else metrics["average_holding_time"] / 1000
        ),
        "BASELINE_STOP_COUNT": sum(row.get("exit_reason") == "STOP" for row in eligible),
        "BASELINE_TARGET_COUNT": sum(row.get("exit_reason") == "TARGET" for row in eligible),
        "BASELINE_REPLAY_VALID": bool(eligible),
        "PARAMETERS": _production_baseline_config(),
    }


def _search_validation_baseline(
    splits: dict[str, list[dict[str, Any]]], minimums: dict[str, int],
) -> dict[str, Any]:
    item, _consumed, _reason = _evaluate_config(
        _production_baseline_config(), splits, minimums,
        index=-1, stage="SEARCH_VALIDATION_BASELINE",
    )
    compact = compact_result(item)
    return {
        "population": "SEARCH_VALIDATION_BASELINE",
        "directly_comparable_to_candidates": True,
        "dataset_split": "VALIDATION",
        "trade_count": compact["trade_count"],
        "performance_class": compact["performance_class"],
        "insufficient_sample_gates": compact["insufficient_sample_gates"],
        "evaluation_contract": "SAME_DATASET_SPLIT_CUTOFF_COST_SNAPSHOT_AND_EVALUATOR",
    }


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, text=True,
        capture_output=True,
    ).stdout.strip()


def _stale_policy(config: dict[str, object]) -> StalePositionPolicyParameters:
    payload = SCALPING_V2.exit_policy.stale_position.model_dump(mode="python")
    payload.update({name: config[name] for name in TIME_STOP_SEARCH_FIELDS})
    return StalePositionPolicyParameters.model_validate(payload)


def _utc_from_ms(value: object) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def _historical_input(
    row: dict[str, Any], observation: dict[str, Any], *, extension_count: int,
) -> StalePositionInputs | None:
    required = (
        "evaluation_time_ms", "evaluation_closed_until_ms", "current_price",
        "highs", "lows", "exit_commission_bps", "spread_bps",
        "slippage_bps", "adverse_exit_reserve_bps", "commission_source",
    )
    if observation.get("historical_cost_evidence") is not True:
        return None
    if any(observation.get(name) is None for name in required):
        return None
    try:
        opened_ms = int(row["opened_at_ms"])
        evaluation_ms = int(observation["evaluation_time_ms"])
        closed_until_ms = int(observation["evaluation_closed_until_ms"])
        if not (opened_ms < closed_until_ms <= evaluation_ms <= int(row["closed_at_ms"])):
            return None
        highs = tuple(Decimal(str(value)) for value in observation["highs"])
        lows = tuple(Decimal(str(value)) for value in observation["lows"])
        if not highs or not lows:
            return None
        return StalePositionInputs(
            position_id=str(row["position_id"]), symbol=str(row["symbol"]),
            side=str(row["direction"]), opened_at=_utc_from_ms(opened_ms),
            evaluation_time=_utc_from_ms(evaluation_ms),
            evaluation_closed_until_ms=closed_until_ms,
            entry_price=Decimal(str(row["entry_price"])),
            current_price=Decimal(str(observation["current_price"])),
            quantity=Decimal(str(row["quantity"])),
            stop_price=Decimal(str(row["stop_price"])),
            target_price=Decimal(str(row["target_price"])),
            entry_fee_incurred=Decimal(str(row["entry_fee_incurred"])),
            exit_commission_bps=Decimal(str(observation["exit_commission_bps"])),
            spread_bps=Decimal(str(observation["spread_bps"])),
            slippage_bps=Decimal(str(observation["slippage_bps"])),
            adverse_exit_reserve_bps=Decimal(str(observation["adverse_exit_reserve_bps"])),
            highs=highs, lows=lows,
            setup_valid=observation.get("setup_valid"),
            momentum_valid=observation.get("momentum_valid"),
            remaining_ev_r=(
                None if observation.get("remaining_ev_r") is None
                else Decimal(str(observation["remaining_ev_r"]))
            ),
            extension_count=extension_count,
            commission_provenance={
                "source": str(observation["commission_source"]),
                "historical": True,
            },
        )
    except (KeyError, TypeError, ValueError, ArithmeticError):
        return None


def _split(rows: list[dict[str, Any]], seed: int) -> dict[str, list[dict[str, Any]]]:
    if rows and all(row.get("split") in {"CALIBRATION", "VALIDATION", "HOLDOUT"} for row in rows):
        return {name: [row for row in rows if row["split"] == name] for name in (
            "CALIBRATION", "VALIDATION", "HOLDOUT"
        )}
    ordered = sorted(rows, key=lambda row: (
        row.get("closed_at_ms", row.get("boundary_ms", 0)),
        row.get("position_id", row.get("candidate_id", "")),
    ))
    # Time-series research must never leak future observations through a random split.
    a, b = int(len(ordered) * .6), int(len(ordered) * .8)
    return {"CALIBRATION": ordered[:a], "VALIDATION": ordered[a:b], "HOLDOUT": ordered[b:]}


def _gate_result(row: dict[str, Any], config: dict[str, object]) -> tuple[bool, str]:
    signal_regime_checks = (
        (float(row.get("strategy_score", SCALPING_V2.signal.strategy_minimum_score)) >= float(config.get("strategy_minimum_score", 0)), "REJECT_STRATEGY_SCORE"),
        (int(row.get("regime_history_candles", SCALPING_V2.signal.regime_lookback_candles)) >= int(config.get("regime_lookback_candles", SCALPING_V2.signal.regime_lookback_candles)), "REJECT_REGIME_HISTORY"),
    )
    for passed, reason in signal_regime_checks:
        if not passed:
            return False, reason
    samples = int(row.get("probability_sample_size", 0))
    raw = row.get("p_win_raw")
    if raw is None:
        # Persisted pre-probability rows legitimately carry null computed
        # metrics. Missing evidence must reject the gate, never abort planning.
        def finite_or(value: object, unavailable: float) -> float:
            return unavailable if value is None else float(value)

        checks = (
            (finite_or(row.get("expected_ev_r"), -1e9) >= float(config["min_positive_ev_r"]), "REJECT_EV"),
            (finite_or(row.get("ev_reserve"), -1e9) >= float(config["min_ev_reserve_r"]), "REJECT_DYNAMIC_NET_RR"),
            (finite_or(row.get("net_edge_bps"), -1e9) >= float(config["min_net_edge_bps"]), "REJECT_MIN_NET_EDGE"),
            (samples >= int(config["bucket_min_sample"]), "REJECT_BUCKET_SAMPLE"),
            (finite_or(row.get("stop_distance_bps"), 1e9) <= float(config["stop_max_bps"]), "REJECT_STOP_MAX_BPS"),
            (finite_or(row.get("target_distance_bps"), -1e9) >= float(config["target_min_bps"]), "REJECT_TARGET_MIN_BPS"),
            (int(row.get("causal_reset_conditions", 0)) >= int(config["causal_reset_min_conditions"]), "REJECT_CAUSAL_DUPLICATE"),
            (int(row.get("one_min_confirmation_count", 0)) >= int(config["entry_refinement_1m_confirmation_count"]), "REJECT_OTHER"),
        )
        for passed, reason in checks:
            if not passed:
                return False, reason
        return True, "PASSED"
    target = float(row.get("target_distance_bps") or 0)
    stop = float(row.get("stop_distance_bps") or 0)
    base_cost = float(row.get("effective_total_cost_bps") or 0)
    adjusted_cost = max(0.0, base_cost
        - float(row.get("adverse_fill_reserve_bps") or 0)
        - 2 * float(row.get("entry_slippage_bps") or 0)
        + float(config["adverse_fill_reserve_bps"])
        + 2 * float(config["entry_slippage_bps"]))
    if min(target - adjusted_cost, stop + adjusted_cost) <= 0:
        return False, "REJECT_MIN_NET_EDGE"
    if samples < int(config["bucket_min_sample"]):
        return False, "REJECT_BUCKET_SAMPLE"
    bucket = EmpiricalSetupBucket(
        setup_type=str(row.get("setup_type", "UNKNOWN")),
        direction=str(row.get("direction", "UNKNOWN")),
        samples=samples, wins=max(0, min(samples, round(float(raw) * samples))),
        level="historical_authority", bucket_key="historical_authority",
    )
    decision = evaluate_expectancy(
        net_win_bps=target - adjusted_cost, net_loss_bps=stop + adjusted_cost,
        bucket=bucket, minimum_samples=int(config["bucket_min_sample"]),
        minimum_positive_ev_r=float(config["min_positive_ev_r"]),
        minimum_ev_reserve_r=float(config["min_ev_reserve_r"]),
        probability_confidence_level=float(config["probability_confidence_level"]),
        prior_alpha=float(config["prior_alpha"]), prior_beta=float(config["prior_beta"]),
    )
    checks = (
        (decision.admitted, "REJECT_DYNAMIC_NET_RR"),
        (target - adjusted_cost >= float(config["min_net_edge_bps"]), "REJECT_MIN_NET_EDGE"),
        (stop <= float(config["stop_max_bps"]), "REJECT_STOP_MAX_BPS"),
        (target >= float(config["target_min_bps"]), "REJECT_TARGET_MIN_BPS"),
        (int(row.get("causal_reset_conditions", 0)) >= int(config["causal_reset_min_conditions"]), "REJECT_CAUSAL_DUPLICATE"),
        (int(row.get("one_min_confirmation_count", 0)) >= int(config["entry_refinement_1m_confirmation_count"]), "REJECT_OTHER"),
    )
    for passed, reason in checks:
        if not passed:
            return False, reason
    return True, "PASSED"


def _admitted(row: dict[str, Any], config: dict[str, object]) -> bool:
    return _gate_result(row, config)[0]


def _gate_funnel(
    rows: list[dict[str, Any]], config: dict[str, object],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    admitted: list[dict[str, Any]] = []
    funnel: dict[str, int] = {"INPUT_ROWS": len(rows)}
    for row in rows:
        passed, reason = _gate_result(row, config)
        funnel[reason] = funnel.get(reason, 0) + 1
        if passed:
            admitted.append(row)
    funnel["PASSED_ROWS"] = len(admitted)
    funnel["REJECTED_ROWS"] = len(rows) - len(admitted)
    return admitted, dict(sorted(funnel.items()))


def _independent_gate_predicate_signature(
    rows: list[dict[str, Any]], config: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    """Fingerprint researched predicates without upstream-gate masking.

    The evaluation funnel remains sequential and fail-closed. Planning also
    needs independent row-level signatures so an early economics rejection
    cannot classify a later SIGNAL, REGIME, ENTRY, or GEOMETRY threshold as a
    behavioral no-op.
    """
    flags: dict[str, bytearray] = {
        name: bytearray() for name in (
            "strategy_minimum_score", "regime_lookback_candles",
            "stop_max_bps", "target_min_bps", "causal_reset_min_conditions",
            "entry_refinement_1m_confirmation_count",
        )
    }
    for row in rows:
        raw_probability = row.get("p_win_raw")
        if raw_probability is None:
            stop = (
                float("inf") if row.get("stop_distance_bps") is None
                else float(row["stop_distance_bps"])
            )
            target = (
                float("-inf") if row.get("target_distance_bps") is None
                else float(row["target_distance_bps"])
            )
        else:
            stop = float(row.get("stop_distance_bps") or 0)
            target = float(row.get("target_distance_bps") or 0)
        outcomes = {
            "strategy_minimum_score": (
                float(row.get("strategy_score", SCALPING_V2.signal.strategy_minimum_score))
                >= float(config["strategy_minimum_score"])
            ),
            "regime_lookback_candles": (
                int(row.get("regime_history_candles", SCALPING_V2.signal.regime_lookback_candles))
                >= int(config["regime_lookback_candles"])
            ),
            "stop_max_bps": stop <= float(config["stop_max_bps"]),
            "target_min_bps": target >= float(config["target_min_bps"]),
            "causal_reset_min_conditions": (
                int(row.get("causal_reset_conditions", 0))
                >= int(config["causal_reset_min_conditions"])
            ),
            "entry_refinement_1m_confirmation_count": (
                int(row.get("one_min_confirmation_count", 0))
                >= int(config["entry_refinement_1m_confirmation_count"])
            ),
        }
        for name, passed in outcomes.items():
            flags[name].append(passed)
    return {
        name: {
            "row_outcome_sha256": sha256(values).hexdigest(),
            "passed_rows": sum(values),
            "input_rows": len(values),
        }
        for name, values in sorted(flags.items())
    }


def _distribution(rows: list[dict[str, Any]], name: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        key = str(row.get(name, "UNKNOWN"))
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def _optional_mean(rows: list[dict[str, Any]], field: str) -> float | None:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    return sum(values) / len(values) if values else None


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    pnl = [float(row.get("net_pnl", 0)) for row in rows]
    gross = [float(row.get("gross_pnl", value + float(row.get("fees", 0)))) for row, value in zip(rows, pnl)]
    fees = [float(row.get("fees", 0)) for row in rows]
    wins = [value for value in pnl if value > 0]
    losses = [-value for value in pnl if value < 0]
    curve = peak = drawdown = 0.0
    for value in pnl:
        curve += value
        peak = max(peak, curve)
        drawdown = max(drawdown, peak - curve)
    hours = 0.0 if not rows else max(0.0, (
        max(float(row.get("closed_at_ms", 0)) for row in rows)
        - min(float(row.get("opened_at_ms", row.get("closed_at_ms", 0))) for row in rows)
    ) / 3_600_000)
    avg_win = sum(wins) / len(wins) if wins else None
    avg_loss = sum(losses) / len(losses) if losses else None
    gross_profit, gross_loss = sum(wins), sum(losses)
    return {
        "trade_count": count, "trades_per_hour": count / hours if hours else None,
        "trades_per_day": count / hours * 24 if hours else None,
        "win_rate": len(wins) / count if count else None,
        "average_win": avg_win, "average_loss": avg_loss,
        "payoff_ratio": avg_win / avg_loss if avg_win is not None and avg_loss else None,
        "gross_pnl": sum(gross), "fees": sum(fees), "net_pnl": sum(pnl),
        "net_expectancy_per_trade": sum(pnl) / count if count else None,
        "net_expectancy_per_hour": sum(pnl) / hours if hours else None,
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "max_drawdown": drawdown,
        "fee_to_gross_edge_ratio": sum(fees) / abs(sum(gross)) if sum(gross) else None,
        "stop_hit_rate": sum(row.get("exit_reason") == "STOP" for row in rows) / count if count else None,
        "target_hit_rate": sum(row.get("exit_reason") == "TARGET" for row in rows) / count if count else None,
        "average_holding_time": sum(float(row.get("holding_time_ms", 0)) for row in rows) / count if count else None,
        "mae_stats": {"mean": _optional_mean(rows, "mae")},
        "mfe_stats": {"mean": _optional_mean(rows, "mfe")},
        "symbol_distribution": _distribution(rows, "symbol"),
        "direction_distribution": _distribution(rows, "direction"),
        "setup_distribution": _distribution(rows, "setup_type"),
        "session_distribution": _distribution(rows, "session"),
        "rejection_reasons": _distribution(rows, "rejection_reason"),
    }


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _replay_time_stop(
    row: dict[str, Any], policy: StalePositionPolicyParameters,
    *, config_hash: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    observations = row.get("time_stop_observations")
    state = {
        "status": "UNREPLAYABLE_MISSING_MARKET_TIMELINE", "soft": False, "hard": False,
        "exit": False, "break_even": False, "seconds_saved": 0.0,
        "blocked_candidates": None, "unblocked_candidates": None,
    }
    if not isinstance(observations, list) or not observations:
        return row, state
    market_available, cost_available = _observation_capability(row)
    if not market_available:
        state["status"] = "UNREPLAYABLE_MISSING_MARKET_TIMELINE"
        return row, state
    if not cost_available:
        state["status"] = "UNREPLAYABLE_MISSING_COST_TIMELINE"
        return row, state
    extension_count = 0
    decision = None
    try:
        opened_ms = int(row["opened_at_ms"])
        actual_close_ms = int(row["closed_at_ms"])
        ordered = sorted(
            (
                item for item in observations
                if isinstance(item, dict)
                and opened_ms < int(item.get("evaluation_closed_until_ms", -1))
                <= int(item.get("evaluation_time_ms", -1)) <= actual_close_ms
            ),
            key=lambda item: int(item["evaluation_closed_until_ms"]),
        )
    except (TypeError, ValueError):
        ordered = []
    if not ordered:
        state["status"] = "UNREPLAYABLE_MISSING_TIME_STOP_OBSERVATIONS"
        return row, state
    for observation in ordered:
        inputs = _historical_input(row, observation, extension_count=extension_count)
        if inputs is None:
            state["status"] = "UNREPLAYABLE_MISSING_TIME_STOP_OBSERVATIONS"
            return row, state
        decision = evaluate_stale_position_shadow(
            inputs, policy=policy, config_hash=config_hash,
        )
        extension_count = decision.extension_count
        state["soft"] = bool(state["soft"] or decision.soft_timeout_reached)
        state["hard"] = bool(state["hard"] or decision.hard_timeout_reached)
        if decision.shadow_decision == "HYPOTHETICAL_EXIT":
            break
    if decision is None:
        state["status"] = "UNREPLAYABLE_MISSING_TIME_STOP_OBSERVATIONS"
        return row, state
    state["status"] = "REPLAYABLE"
    if decision.shadow_decision != "HYPOTHETICAL_EXIT":
        return row, state
    replayed = ChainMap({
        "closed_at_ms": int(decision.evaluated_at.timestamp() * 1000),
        "holding_time_ms": decision.holding_seconds * 1000,
        "net_pnl": float(decision.shadow_net_pnl),
        "gross_pnl": float(decision.shadow_gross_pnl),
        "fees": float(decision.shadow_fees),
        "exit_reason": decision.shadow_exit_reason,
    }, row)
    state["exit"] = True
    state["break_even"] = decision.shadow_exit_reason == "TIME_STOP_SHADOW_BREAK_EVEN_PROTECT"
    state["seconds_saved"] = max(
        0.0, (float(row["closed_at_ms"]) - replayed["closed_at_ms"]) / 1000,
    )
    candidates = row.get("causal_later_candidates")
    if isinstance(candidates, list) and all(
        isinstance(item, dict) and item.get("candidate_time_ms") is not None
        for item in candidates
    ):
        baseline_close = int(row["closed_at_ms"])
        exit_ms = int(replayed["closed_at_ms"])
        blocked = [
            item for item in candidates
            if int(row["opened_at_ms"]) < int(item["candidate_time_ms"]) <= baseline_close
        ]
        state["blocked_candidates"] = len(blocked)
        state["unblocked_candidates"] = sum(
            exit_ms < int(item["candidate_time_ms"]) <= baseline_close
            for item in blocked
        )
    return replayed, state


def _time_stop_metrics(
    rows: list[dict[str, Any]], config: dict[str, object], *, config_hash: str,
) -> dict[str, Any]:
    policy = _stale_policy(config)
    outcomes = [
        _replay_time_stop(row, policy, config_hash=config_hash) for row in rows
    ]
    replayed = [row for row, _state in outcomes]
    states = [state for _row, state in outcomes]
    baseline = _metrics(rows)
    time_stop = _metrics(replayed)
    holding_seconds = [float(row.get("holding_time_ms", 0)) / 1000 for row in replayed]
    evidence_states = [
        state for state in states if state["blocked_candidates"] is not None
    ]
    result = {
        **time_stop,
        "baseline": baseline,
        "time_stop": time_stop,
        "time_stop_exit_count": sum(bool(state["exit"]) for state in states),
        "soft_timeout_count": sum(bool(state["soft"]) for state in states),
        "hard_timeout_count": sum(bool(state["hard"]) for state in states),
        "break_even_protection_count": sum(bool(state["break_even"]) for state in states),
        "average_holding_seconds": (
            sum(holding_seconds) / len(holding_seconds) if holding_seconds else None
        ),
        "baseline_average_holding_seconds": (
            None if baseline["average_holding_time"] is None
            else baseline["average_holding_time"] / 1000
        ),
        "holding_p50": _percentile(holding_seconds, .50),
        "holding_p90": _percentile(holding_seconds, .90),
        "baseline_net_pnl": baseline["net_pnl"],
        "time_stop_net_pnl": time_stop["net_pnl"],
        "net_pnl_delta": time_stop["net_pnl"] - baseline["net_pnl"],
        "baseline_net_expectancy": baseline["net_expectancy_per_trade"],
        "time_stop_net_expectancy": time_stop["net_expectancy_per_trade"],
        "expectancy_delta": (
            None if baseline["net_expectancy_per_trade"] is None
            or time_stop["net_expectancy_per_trade"] is None else
            time_stop["net_expectancy_per_trade"] - baseline["net_expectancy_per_trade"]
        ),
        "baseline_profit_factor": baseline["profit_factor"],
        "time_stop_profit_factor": time_stop["profit_factor"],
        "baseline_max_drawdown": baseline["max_drawdown"],
        "time_stop_max_drawdown": time_stop["max_drawdown"],
        "fees_total": time_stop["fees"],
        "baseline_fees_total": baseline["fees"],
        "fees_per_trade": time_stop["fees"] / len(replayed) if replayed else None,
        "fee_drag_delta": time_stop["fees"] - baseline["fees"],
        "stale_position_seconds_saved": sum(float(state["seconds_saved"]) for state in states),
        "capacity_seconds_saved": sum(float(state["seconds_saved"]) for state in states),
        "candidates_blocked_while_position_open": (
            sum(int(state["blocked_candidates"]) for state in evidence_states)
            if evidence_states else None
        ),
        "hypothetical_candidates_unblocked_after_stale_exit": (
            sum(int(state["unblocked_candidates"]) for state in evidence_states)
            if evidence_states else None
        ),
        "replay_status": _distribution(states, "status"),
        "rows_total": len(rows),
        "rows_replayable": sum(state["status"] == "REPLAYABLE" for state in states),
        "rows_unreplayable": sum(
            str(state["status"]).startswith("UNREPLAYABLE") for state in states
        ),
        "rows_partially_replayable": sum(
            state["status"] != "REPLAYABLE"
            and _has_fields(row, OUTCOME_REPLAY_REQUIRED)
            for row, state in zip(rows, states, strict=True)
        ),
    }
    return result


def _dataset_options(
    search: dict[str, Any], *, max_rows: int | None = None,
    from_value: str | None = None, to_value: str | None = None,
) -> DatasetOptions:
    raw = search.get("dataset", {})
    if isinstance(raw, dict):
        source = str(raw.get("source", DATASET_SOURCE))
        profile = str(raw.get("profile", ""))
        primary_timeframe = str(raw.get("primary_timeframe", ""))
        closed_only = raw.get("closed_only", False)
        selection_mode = str(raw.get("selection_mode", ""))
        configured_max = raw.get("max_rows")
        configured_from, configured_to = raw.get("from"), raw.get("to")
    else:
        raise SweepExpectedError("DATASET_CONFIG_INVALID")
    if (
        profile != "trade-5m-v2" or primary_timeframe != "5m"
        or closed_only is not False
    ):
        raise SweepExpectedError("DATASET_CONFIG_INVALID")
    if max_rows is not None:
        selection_mode, configured_max = "LATEST_N_UNTIL_CUTOFF", max_rows
    if selection_mode not in {"ALL_UNTIL_CUTOFF", "LATEST_N_UNTIL_CUTOFF"}:
        raise SweepExpectedError("DATASET_SELECTION_MODE_INVALID")
    try:
        maximum = None if configured_max is None else int(configured_max)
    except (TypeError, ValueError):
        raise SweepExpectedError("MAX_ROWS_OUT_OF_RANGE") from None
    if selection_mode == "LATEST_N_UNTIL_CUTOFF" and (maximum is None or maximum < 1):
        raise SweepExpectedError("MAX_ROWS_OUT_OF_RANGE")
    if selection_mode == "ALL_UNTIL_CUTOFF" and maximum is not None:
        raise SweepExpectedError("DATASET_CONFIG_INVALID")
    start = _parse_utc(from_value if from_value is not None else configured_from)
    end = _parse_utc(to_value if to_value is not None else configured_to)
    if start is not None and end is not None and start >= end:
        raise SweepExpectedError("INVALID_DATE_RANGE")
    return DatasetOptions(
        source, profile, primary_timeframe, False, selection_mode, maximum,
        start, end,
    )


def _validate_search(search: object) -> dict[str, Any]:
    if not isinstance(search, dict):
        raise SweepExpectedError("SEARCH_SPACE_INVALID")
    space = search.get("search_space")
    if (
        search.get("schema_version") != 2
        or not isinstance(space, dict)
        or "risk_per_trade" in space
        or any(not isinstance(values, list) or not values for values in space.values())
    ):
        raise SweepExpectedError("SEARCH_SPACE_INVALID")
    targeted = search.get("search", {}).get("strategy") == "targeted" and "calibration" in search
    if not targeted and not TIME_STOP_SEARCH_FIELDS.issubset(space):
        raise SweepExpectedError("SEARCH_SPACE_INVALID")
    calibration = search.get("calibration", {})
    artifact = search.get("artifact", {})
    if (
        not isinstance(calibration, dict)
        or calibration.get("baseline_set_id") != "scalping-v2-set-2"
        or tuple(calibration.get("targeted_families", ())) != ACTIVE_RESEARCH_FAMILIES
        or tuple(calibration.get("frozen_families", ())) != FROZEN_RESEARCH_FAMILIES
        or not isinstance(artifact, dict)
        or artifact.get("schema_version") != 2
    ):
        raise SweepExpectedError("RESEARCH_AUTHORITY_INVALID")
    if targeted:
        try:
            validate_targeted_space(search)
        except (KeyError, TypeError, ValueError):
            raise SweepExpectedError("SEARCH_SPACE_INVALID") from None
    if int(search["seed"]) != int(search["search"]["seed"]):
        raise SweepExpectedError("RUN_SEED_MISMATCH")
    return search


def _local_schema_heads() -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            ["python", "-m", "alembic", "heads"], cwd=PROJECT_ROOT,
            check=True, text=True, capture_output=True, timeout=30,
        )
        return tuple(
            line.split()[0] for line in completed.stdout.splitlines()
            if line.strip() and "(head)" in line
        )
    except (OSError, subprocess.SubprocessError):
        raise SweepExpectedError("SCHEMA_DISCOVERY_FAILED") from None


def _prepare_output(
    search: dict[str, Any], run_id: str | None, *, resume: bool,
) -> tuple[str, Path]:
    root = Path(str(search.get("output_root", "artifacts/scalping_v2_parameter_sweep")))
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    identifier = run_id or generate_run_id(root)
    if not identifier or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for character in identifier):
        raise SweepExpectedError("RUN_ID_INVALID")
    output = root / identifier
    try:
        if resume:
            if not output.is_dir():
                raise SweepExpectedError("RESUME_RUN_NOT_FOUND")
        else:
            output.mkdir(parents=True, exist_ok=False)
        probe = output / ".write-probe"
        probe.write_text("ok", encoding="ascii")
        probe.unlink()
    except FileExistsError:
        raise SweepExpectedError(
            "RUN_ID_ALREADY_EXISTS; Use a new --run-id or --resume for a compatible interrupted run."
        ) from None
    except OSError:
        raise SweepExpectedError("OUTPUT_NOT_WRITABLE") from None
    return identifier, output


def _preflight_database(
    database: ReadOnlyResearchDatabase,
) -> tuple[str, str, tuple[str, ...], dict[str, str]]:
    heads = _local_schema_heads()
    try:
        with database.connection() as connection:
            read_only = database.execute_select(
                connection, text("SELECT current_setting('transaction_read_only')")
            ).scalar_one()
            schema_head = database.execute_select(
                connection, text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            tables = tuple(sorted(inspect(connection).get_table_names()))
    except SweepExpectedError:
        raise
    except SQLAlchemyError:
        raise SweepExpectedError("SCHEMA_DISCOVERY_FAILED") from None
    if str(read_only).lower() != "on":
        raise SweepExpectedError("DATABASE_SESSION_NOT_READ_ONLY")
    if schema_head not in heads:
        raise SweepExpectedError("SCHEMA_HEAD_MISMATCH")
    if not REQUIRED_TABLES.issubset(tables):
        raise SweepExpectedError("REQUIRED_TABLES_NOT_AVAILABLE")
    probes = {
        "INSERT": "INSERT INTO paper_positions SELECT * FROM paper_positions WHERE false",
        "UPDATE": "UPDATE paper_positions SET symbol = symbol WHERE false",
        "DELETE": "DELETE FROM paper_positions WHERE false",
        "DDL": "CREATE TEMP TABLE parameter_sweep_write_probe (id integer)",
    }
    rejected: dict[str, str] = {}
    for name, statement in probes.items():
        accepted = False
        try:
            with database.engine.connect() as connection:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                if connection.execute(
                    text("SELECT current_setting('transaction_read_only')")
                ).scalar_one() != "on":
                    raise SweepExpectedError("DATABASE_SESSION_NOT_READ_ONLY")
                connection.execute(text(statement))
                accepted = True
                connection.rollback()
        except SweepExpectedError:
            raise
        except SQLAlchemyError:
            rejected[name] = "REJECTED"
        if accepted:
            raise SweepExpectedError("DATABASE_WRITE_GUARD_FAILED")
    return str(read_only).upper(), str(schema_head), tables, rejected


def _write_preflight(path: Path, payload: dict[str, Any]) -> None:
    DEFAULT_ARTIFACT_WRITER.atomic_json(path, payload, operation="preflight_replace")


def _print_preflight(payload: Mapping[str, object]) -> None:
    print("PARAMETER_SWEEP_PREFLIGHT = PASS")
    for key in (
        "DATASET_SOURCE", "DATABASE_BINDING", "DATABASE_SESSION", "SCHEMA_HEAD",
        "PROFILE", "ROWS_AVAILABLE", "CONFIGURATIONS_PLANNED", "OUTPUT_DIR",
        "SECRET_OUTPUT",
    ):
        print(f"{key} = {payload[key]}")


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _atomic_json(path: Path, payload: object) -> None:
    try:
        DEFAULT_ARTIFACT_WRITER.atomic_json(path, payload, operation=f"{path.name}:replace")
    except ArtifactWriteError as error:
        if path.name == "CHECKPOINT.json":
            raise SweepExpectedError("CHECKPOINT_WRITE_FAILED") from error
        raise


def _timing(started: datetime, finished: datetime | None = None) -> dict[str, object]:
    end = finished or datetime.now(timezone.utc)
    seconds = max(0.0, (end - started).total_seconds())
    whole = int(seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, secs = divmod(remainder, 60)
    return {
        "RUN_STARTED_AT": started.isoformat(),
        "RUN_FINISHED_AT": end.isoformat(),
        "RUN_DURATION_SECONDS": round(seconds, 6),
        "RUN_DURATION_HUMAN": f"{hours:02d}:{minutes:02d}:{secs:02d}",
    }


def _stream_json_array(source: Path, target: Path, *, rejected_only: bool = False) -> None:
    rendered: list[str] = []
    with source.open(encoding="utf-8") as incoming:
        for line in incoming:
            item = json.loads(line)
            status = item.get("evaluation_status", item.get("result_status"))
            if not rejected_only or status != "ACCEPTED":
                rendered.append(json.dumps(item, indent=2, sort_keys=True))
    DEFAULT_ARTIFACT_WRITER.atomic_text(
        target, "[\n" + ",\n".join(rendered) + "\n]\n",
        operation=f"{target.name}:replace",
    )


def _evaluate_config(
    params: dict[str, object], splits: Mapping[str, list[dict[str, Any]]],
    minimums: Mapping[str, int], *, index: int, stage: str,
) -> tuple[dict[str, Any], bool, str | None]:
    item: dict[str, Any] = {
        "result_index": index, "stage": stage, "parameters": params,
        "config_hash": _config_hash(params),
    }
    if any(rows and "boundary_ms" in rows[0] for rows in splits.values()):
        item["INPUT_ROWS"] = sum(len(rows) for rows in splits.values())
        item["REPLAYABLE_ROWS"] = sum(
            bool(row.get("market_path_1m")) for rows in splits.values() for row in rows
        )
        item["PARTIALLY_REPLAYABLE_ROWS"] = item["INPUT_ROWS"]-item["REPLAYABLE_ROWS"]
        item["UNREPLAYABLE_ROWS"] = item["PARTIALLY_REPLAYABLE_ROWS"]
        results = {
            name.lower(): chronological_portfolio_replay(rows, params)
            for name, rows in splits.items()
        }
        item.update(results)
        item["gate_funnel"] = {
            name: value["funnel"] for name, value in results.items()
        }
        item["split_status"] = {
            name: ("PASS" if value["trade_count"] > 0 else "NO_TRADES_EXPLICIT_FUNNEL")
            for name, value in results.items()
        }
        # Holdout is reported but never participates in selection/ranking.
        validation = results["validation"]
        item["result_status"] = "ACCEPTED" if validation["trade_count"] > 0 else "REJECTED"
        reason = None if validation["trade_count"] > 0 else "VALIDATION_NO_TRADES_EXPLICIT_FUNNEL"
        return item, True, reason
    all_rows = [row for name in ("CALIBRATION", "VALIDATION", "HOLDOUT") for row in splits[name]]
    reasons = [_replay_reason(row) for row in all_rows]
    item.update({
        "INPUT_ROWS": len(all_rows),
        "REPLAYABLE_ROWS": sum(reason == "REPLAYABLE" for reason in reasons),
        "PARTIALLY_REPLAYABLE_ROWS": sum(
            reason != "REPLAYABLE" and _has_fields(row, OUTCOME_REPLAY_REQUIRED)
            for row, reason in zip(all_rows, reasons, strict=True)
        ),
        "UNREPLAYABLE_ROWS": sum(reason != "REPLAYABLE" for reason in reasons),
    })
    try:
        _stale_policy(params)
    except (TypeError, ValueError) as error:
        item.update({
            "result_status": "PRUNED_INVALID", "invalid_reason": str(error),
            "split_status": {name: "PRUNED_INVALID" for name in (
                "calibration", "validation", "holdout"
            )},
        })
        for name in ("calibration", "validation", "holdout"):
            item[name] = _metrics([])
        return item, False, "STRUCTURAL_INVALID"
    admitted_cal, calibration_funnel = _gate_funnel(splits["CALIBRATION"], params)
    item["gate_funnel"] = {"calibration": calibration_funnel}
    item["calibration"] = _time_stop_metrics(
        admitted_cal, params, config_hash=item["config_hash"],
    )
    if len(admitted_cal) < int(minimums["calibration"]):
        reason = (
            "CALIBRATION_ALL_ROWS_REJECTED_BY_EXPLICIT_GATES"
            if not admitted_cal else "CALIBRATION_INSUFFICIENT_SAMPLE"
        )
        item["validation"] = _metrics([])
        item["holdout"] = _metrics([])
        item["split_status"] = {
            "calibration": "INSUFFICIENT_SAMPLE", "validation": "NOT_EVALUATED_EARLY_REJECT",
            "holdout": "NOT_EVALUATED_EARLY_REJECT",
        }
        item["result_status"] = "EARLY_REJECTED"
        item["early_reject_reason"] = reason
        return item, True, reason
    statuses = {"calibration": "PASS"}
    admitted_validation, validation_funnel = _gate_funnel(splits["VALIDATION"], params)
    item["gate_funnel"]["validation"] = validation_funnel
    item["validation"] = _time_stop_metrics(
        admitted_validation, params, config_hash=item["config_hash"],
    )
    statuses["validation"] = (
        "PASS" if len(admitted_validation) >= int(minimums["validation"])
        else "INSUFFICIENT_SAMPLE"
    )
    if item["validation"]["rows_replayable"] == 0:
        statuses["validation"] = "INSUFFICIENT_REPLAY_DATA"
    # Holdout is evaluated only after search metrics and never feeds stage/ranking.
    admitted_holdout, holdout_funnel = _gate_funnel(splits["HOLDOUT"], params)
    item["gate_funnel"]["holdout"] = holdout_funnel
    item["holdout"] = _time_stop_metrics(
        admitted_holdout, params, config_hash=item["config_hash"],
    )
    statuses["holdout"] = (
        "PASS" if len(admitted_holdout) >= int(minimums["holdout"])
        else "INSUFFICIENT_SAMPLE"
    )
    item["split_status"] = statuses
    item["result_status"] = (
        "ACCEPTED" if statuses["validation"] == "PASS" else "REJECTED"
    )
    return item, True, None


def _stage_for(plan: SearchPlan, evaluated: int) -> str:
    boundary = 0
    for stage in plan.staged_search_plan:
        boundary += int(stage["budget"])
        if evaluated < boundary:
            return str(stage["stage"])
    return str(plan.staged_search_plan[-1]["stage"])


def _aggregate_results(output: Path) -> dict[str, object]:
    rows = list(iter_results(output / "RESULTS.jsonl"))
    ranked = rank_results(rows)[: RESEARCH_PARAMETERS.artifact.top_config_count]
    return {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "ranked_without_holdout": ranked,
        "pareto_frontier": pareto_frontier(ranked),
        "holdout_used_for_search": False,
        "selection_bias_guard": selection_bias_guard(hypothesis_count=len(rows), independent_observations=max((int(row.get("opportunity_count") or 0) for row in rows), default=0)),
    }


def _run_impl(
    search_path: Path, *, run_id: str | None = None, max_configs: int | None = None,
    max_rows: int | None = None, from_value: str | None = None,
    to_value: str | None = None, database_url: str | None = None,
    preflight_only: bool = False, verbose: bool = False, resume: bool = False,
    mode: ResearchMode = ResearchMode.ALL,
    stop_after_batches: int | None = None,
    event_sink: Callable[[SweepEvent], None] | None = None,
    stop_requested: Callable[[], bool] | None = None,
) -> Path:
    run_started = datetime.now(timezone.utc)
    try:
        search = _validate_search(yaml.safe_load(search_path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        raise SweepExpectedError("CONFIG_FILE_NOT_FOUND") from None
    except yaml.YAMLError:
        raise SweepExpectedError("SEARCH_SPACE_INVALID") from None
    space = active_search_space(search) if search.get("search", {}).get("strategy") == "targeted" else search["search_space"]
    options = _dataset_options(search, max_rows=max_rows, from_value=from_value, to_value=to_value)
    identifier, output = _prepare_output(search, run_id, resume=resume)
    status_store = StatusStore(
        output / "STATUS.json",
        SweepRunStatus(
            run_id=identifier,
            research_mode=mode.value,
            state=RunState.RESUMING.value if resume else RunState.PREFLIGHT.value,
            phase=RunState.RESUMING.value if resume else RunState.PREFLIGHT.value,
            started_at=run_started.isoformat(),
            resume_available=resume,
            engine_version=SCHEMA_VERSION,
        ),
    )

    def emit(event_type: EventType, **payload: Any) -> None:
        if event_sink is not None:
            event_sink(SweepEvent.create(event_type, identifier, **payload))

    status_store.update()
    emit(
        EventType.RUN_RESUMED if resume else EventType.RUN_STARTED,
        output_dir=str(output), research_mode=mode.value,
    )
    emit(EventType.PREFLIGHT_STARTED, checks=(
        "database", "read_only", "dataset", "configuration",
    ))
    database: ReadOnlyResearchDatabase | None = None
    binding_source, session_mode, schema_head = "NOT_REQUIRED_OFFLINE_JSON", "NOT_APPLICABLE", "NOT_APPLICABLE"
    write_rejections: dict[str, str] = {}
    manifest_path = output / "DATASET_MANIFEST.json"
    snapshot_path = output / "DATASET_SNAPSHOT.json"
    dataset_manifest: dict[str, Any] | None = None
    try:
        if options.source in {DATASET_SOURCE, LEGACY_DATASET_SOURCE}:
            binding = resolve_database_binding(explicit_url=database_url)
            binding_source = binding.source
            database = ReadOnlyResearchDatabase(binding)
            session_mode, schema_head, _tables, write_rejections = _preflight_database(database)
        if resume:
            try:
                dataset_manifest = _json(manifest_path)
                rows = json.loads(
                    snapshot_path.read_text(encoding="utf-8"),
                    object_hook=_snapshot_json_hook,
                )
            except (FileNotFoundError, json.JSONDecodeError):
                raise SweepExpectedError("RESUME_DATASET_MANIFEST_MISMATCH") from None
            if (
                not isinstance(dataset_manifest, dict)
                or dataset_manifest.get("manifest_version") != DATASET_MANIFEST_VERSION
                or dataset_manifest.get("run_id") != identifier
                or dataset_manifest.get("profile") != options.profile
                or dataset_manifest.get("primary_timeframe") != options.primary_timeframe
                or dataset_manifest.get("baseline_set_id")
                != RESEARCH_PARAMETERS.calibration.baseline_set_id
                or dataset_manifest.get("dataset_source") != options.source
                or dataset_manifest.get("manifest_hash")
                != _config_hash({
                    key: value for key, value in dataset_manifest.items()
                    if key != "manifest_hash"
                })
                or not isinstance(rows, list)
            ):
                raise SweepExpectedError("RESUME_DATASET_MANIFEST_MISMATCH")
            if dataset_manifest.get("dataset_fingerprint") != _config_hash({
                    "manifest_version": DATASET_MANIFEST_VERSION,
                    "source": options.source,
                    "profile": options.profile,
                    "primary_timeframe": options.primary_timeframe,
                    "schema_head": dataset_manifest.get("source_schema_version"),
                    "rows": rows,
                }):
                raise SweepExpectedError("RESUME_DATASET_MUTATED")
            _validate_dataset_authority(rows, options)
        else:
            rows = _load_rows(options, database)
            if rows:
                _validate_dataset_authority(rows, options)
                dataset_manifest = _manifest_from_rows(
                    run_id=identifier, options=options, rows=rows,
                    schema_head=schema_head,
                )
                DEFAULT_ARTIFACT_WRITER.atomic_text(
                    snapshot_path,
                    json.dumps(rows, indent=2, sort_keys=True, default=_snapshot_json_default),
                    operation="dataset_snapshot_create",
                )
                DEFAULT_ARTIFACT_WRITER.atomic_json(
                    manifest_path, dataset_manifest, operation="dataset_manifest_create",
                )
    except SweepExpectedError as error:
        _write_preflight(output / "PREFLIGHT.json", {
            "PARAMETER_SWEEP_PREFLIGHT": "FAILED", "REASON": error.reason,
            "RUN_ID": identifier, "SECRET_OUTPUT": 0,
        })
        status_store.update(
            state=RunState.FAILED.value, phase=RunState.PREFLIGHT.value,
            failure_reason=error.reason, resume_available=False,
        )
        emit(EventType.RUN_FAILED, reason=error.reason, resume_available=False)
        raise
    finally:
        if database is not None:
            database.dispose()
    if not rows:
        _write_preflight(output / "PREFLIGHT.json", {
            "PARAMETER_SWEEP_PREFLIGHT": "FAILED", "REASON": "DATASET_EMPTY", "SECRET_OUTPUT": 0,
            "RUN_STARTED_AT": run_started.isoformat(),
            "RUN_FAILED_AT": datetime.now(timezone.utc).isoformat(),
        })
        status_store.update(
            state=RunState.FAILED.value, phase=RunState.PREFLIGHT.value,
            failure_reason="DATASET_EMPTY", resume_available=False,
        )
        emit(EventType.RUN_FAILED, reason="DATASET_EMPTY", resume_available=False)
        raise SweepExpectedError("DATASET_EMPTY")
    emit(EventType.PREFLIGHT_COMPLETED, dataset_rows=len(rows), source=options.source)
    status_store.update(state=RunState.PLANNING.value, phase=RunState.PLANNING.value)
    emit(EventType.SEARCH_PLANNING_STARTED)
    resolved_seed = int(search["search"]["seed"])
    splits = _split(rows, resolved_seed)
    coverage = _dataset_coverage(rows)
    baseline = _baseline_control(rows)
    historical_summary = rows[0].get("__historical_summary", {}) if rows else {}
    replay_capabilities = rows[0].get("__replay_capabilities", {}) if rows else {}
    source_inventory = rows[0].get("__source_inventory", []) if rows else []
    baseline_config = _production_baseline_config()
    search_validation_baseline = _search_validation_baseline(
        splits, search["minimum_samples"],
    )
    sensitivity: dict[str, Any] | None = None
    if search.get("search", {}).get("strategy") == "targeted":
        def behavior_signature(config: dict[str, object]) -> dict[str, Any]:
            return {
                name: {
                    "sequential_funnel": _gate_funnel(split_rows, config)[1],
                    "independent_research_predicates": (
                        _independent_gate_predicate_signature(split_rows, config)
                    ),
                }
                for name, split_rows in sorted(splits.items())
            }
        try:
            sensitivity = sensitivity_preflight(search, baseline_config, behavior_signature)
        except ValueError as error:
            raise SweepExpectedError(str(error)) from None
        space = sensitivity["active_dimensions"]
    parameter_registry = build_parameter_registry(active_search_space(search) if sensitivity else space)
    plan = ParameterSweepSearchPlanner().plan(
        dataset_rows=len(rows), space=space, search=search.get("search", {}),
        max_configs_override=max_configs, validation_rows=len(splits["VALIDATION"]),
        holdout_rows=len(splits["HOLDOUT"]),
        available_replay_rows=int(coverage["TIME_STOP_REPLAY_ELIGIBLE_ROWS"]),
        mode=mode,
    )
    targeted_candidates = None
    behavioral_aliases: dict[str, list[dict[str, Any]]] = {}
    if sensitivity is not None:
        effective_search = {**search, "search_space": space}
        mode_candidates = staged_candidates(effective_search, baseline_config)
        if mode.selected_stage is not None:
            mode_candidates = (
                item for item in mode_candidates
                if item.stage == mode.selected_stage
            )
        targeted_candidates, behavioral_aliases = deduplicate_behavioral_configs(
            mode_candidates,
            lambda overrides: behavior_signature({**baseline_config, **overrides}),
        )
        if not targeted_candidates:
            raise SweepExpectedError("NO_PLANNED_EVALUATIONS_FOR_MODE")
        plan = replace(
            plan,
            evaluation_budget=min(plan.evaluation_budget, len(targeted_candidates)),
            effective_search_space_size=len(targeted_candidates),
        )
        sensitivity["behaviorally_distinct_count"] = len(targeted_candidates)
        sensitivity["behavioral_aliases"] = behavioral_aliases
    git_commit = _git_commit()
    assert dataset_manifest is not None
    dataset_fingerprint = str(dataset_manifest["dataset_fingerprint"])
    search_space_hash = _config_hash(space)
    research_hash = _config_hash(search)
    plan_state = _search_plan_state(space, plan)
    search_plan_hash = _config_hash({
        "space": space, "plan": plan.safe_dict(), "minimum_samples": search["minimum_samples"],
    })
    replay_diagnostics = _replay_diagnostics(rows, coverage)
    status_store.update(
        planned_configs=plan.evaluation_budget,
        dataset_fingerprint=dataset_fingerprint,
        dataset_manifest_hash=str(dataset_manifest["manifest_hash"]),
        dataset_cutoff_at=str(dataset_manifest["dataset_cutoff_at"]),
        dataset_period_start_ms=int(dataset_manifest["historical_period_start_ms"]),
        dataset_period_end_ms=int(dataset_manifest["historical_period_end_ms"]),
        config_hash=TRADE_PARAMETERS.config_hash,
        search_space_hash=search_space_hash,
        search_dimensions=list(plan_state.search_dimensions),
        dimension_values=plan_state.dimension_values,
        conditional_dimensions=list(plan_state.conditional_dimensions),
        replay_diagnostics=replay_diagnostics.as_dict(),
        resolved_seed=resolved_seed,
    )
    emit(
        EventType.SEARCH_PLANNED,
        **plan_state.as_dict(),
        replay_diagnostics=replay_diagnostics.as_dict(),
        resolved_seed=resolved_seed,
    )
    checkpoint_path = output / "CHECKPOINT.json"
    checkpoint = {
        "run_id": identifier, "git_commit": git_commit,
        "config_hash": TRADE_PARAMETERS.config_hash,
        "search_space_hash": search_space_hash,
        "search_plan_hash": search_plan_hash,
        "research_config_hash": research_hash,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "dataset_manifest_hash": dataset_manifest["manifest_hash"],
        "engine_version": SCHEMA_VERSION,
        "dataset_fingerprint": dataset_fingerprint,
        "strategy": plan.selected_strategy, "seed": resolved_seed,
        "requested_seed": resolved_seed, "resolved_seed": resolved_seed,
        "research_mode": mode.value, "stage": "NOT_STARTED",
        "profile": options.profile,
        "primary_timeframe": options.primary_timeframe,
        "baseline_set_id": RESEARCH_PARAMETERS.calibration.baseline_set_id,
        "evaluated_count": 0, "accepted_count": 0, "rejected_count": 0,
        "pruned_count": 0, "early_reject_count": 0, "failed_count": 0,
        "insufficient_count": 0, "durable_result_count": 0,
        "last_durable_result_index": -1, "last_candidate_offset": -1,
        "checkpoint_count": 0, "early_reject_reasons": {}, "completed": False,
        "RUN_STARTED_AT": run_started.isoformat(), "RUN_FINISHED_AT": None,
        "RUN_DURATION_SECONDS": None, "RUN_DURATION_HUMAN": None,
        "STATUS": "RUNNING",
    }
    if resume:
        try:
            existing = _json(checkpoint_path)
        except (FileNotFoundError, json.JSONDecodeError):
            raise SweepExpectedError("RESUME_CHECKPOINT_NOT_AVAILABLE") from None
        if existing.get("run_id") != identifier or existing.get("dataset_manifest_hash") != checkpoint["dataset_manifest_hash"] or existing.get("dataset_fingerprint") != dataset_fingerprint:
            raise SweepExpectedError("RESUME_DATASET_MANIFEST_MISMATCH")
        if existing.get("research_mode") != mode.value:
            raise SweepExpectedError("RESUME_RESEARCH_MODE_MISMATCH")
        if existing.get("profile") != options.profile:
            raise SweepExpectedError("RESUME_PROFILE_MISMATCH")
        if existing.get("primary_timeframe") != options.primary_timeframe:
            raise SweepExpectedError("RESUME_TIMEFRAME_MISMATCH")
        if existing.get("baseline_set_id") != RESEARCH_PARAMETERS.calibration.baseline_set_id:
            raise SweepExpectedError("RESUME_BASELINE_SET_MISMATCH")
        if existing.get("search_plan_hash") != search_plan_hash or existing.get("search_space_hash") != search_space_hash or existing.get("strategy") != checkpoint["strategy"] or existing.get("seed") != checkpoint["seed"] or existing.get("resolved_seed") != checkpoint["resolved_seed"]:
            raise SweepExpectedError("RESUME_SEARCH_PLAN_MISMATCH")
        if existing.get("research_config_hash") != research_hash:
            raise SweepExpectedError("RESUME_RESEARCH_CONFIG_MISMATCH")
        if existing.get("artifact_schema_version") != ARTIFACT_SCHEMA_VERSION:
            raise SweepExpectedError("RESUME_ARTIFACT_SCHEMA_MISMATCH")
        if existing.get("config_hash") != TRADE_PARAMETERS.config_hash:
            raise SweepExpectedError("RESUME_CONFIG_MISMATCH")
        if existing.get("engine_version") != SCHEMA_VERSION:
            raise SweepExpectedError("RESUME_ENGINE_INCOMPATIBLE")
        checkpoint = existing
        try:
            run_started = datetime.fromisoformat(str(checkpoint["RUN_STARTED_AT"]))
        except (KeyError, TypeError, ValueError):
            raise SweepExpectedError("RESUME_CHECKPOINT_NOT_AVAILABLE") from None
        status_store.update(
            state=RunState.RESUMING.value,
            phase=RunState.RESUMING.value,
            started_at=run_started.isoformat(),
            completed_configs=int(checkpoint["evaluated_count"]),
            accepted_configs=int(checkpoint["accepted_count"]),
            rejected_configs=int(checkpoint["rejected_count"]),
            error_configs=int(checkpoint["failed_count"]),
            insufficient_configs=int(checkpoint.get("insufficient_count", 0)),
            evaluation_status_counts=dict(checkpoint.get("evaluation_status_counts") or {}),
            performance_class_counts=dict(checkpoint.get("performance_class_counts") or checkpoint.get("classification_counts") or {}),
            resolved_seed=resolved_seed,
            last_checkpoint_at=datetime.now(timezone.utc).isoformat(),
            resume_available=True,
        )
        emit(
            EventType.CONFIG_PROGRESS,
            completed=int(checkpoint["evaluated_count"]),
            planned=plan.evaluation_budget,
            accepted=int(checkpoint["accepted_count"]),
            rejected=int(checkpoint["rejected_count"]),
            errors=int(checkpoint["failed_count"]),
            insufficient=int(checkpoint.get("insufficient_count", 0)),
            evaluation_status_counts=dict(checkpoint.get("evaluation_status_counts") or {}),
            performance_class_counts=dict(checkpoint.get("performance_class_counts") or checkpoint.get("classification_counts") or {}),
        )
    preflight = {
        "RUN_ID": identifier, "CONFIG_HASH": TRADE_PARAMETERS.config_hash,
        "PARAMETER_SWEEP_PREFLIGHT": "PASS", "PROJECT_ROOT_FOUND": PROJECT_ROOT.is_dir(),
        "CONFIG_FILE_FOUND": search_path.is_file(), "TRADE_PARAMETERS_FOUND": CONFIG_PATH.is_file(),
        "DATABASE_BINDING_FOUND": database is not None, "DATABASE_CONNECTION_OK": database is not None,
        "DATABASE_SESSION_READ_ONLY": session_mode == "ON", "SCHEMA_HEAD_OK": schema_head != "NOT_APPLICABLE",
        "REQUIRED_TABLES_AVAILABLE": database is not None, "TRADE_5M_V2_DATASET_AVAILABLE": True,
        "DATASET_ROWS_GT_ZERO": True, "CONFIG_HASH_AVAILABLE": True, "SEARCH_SPACE_VALID": True,
        "OUTPUT_DIRECTORY_WRITABLE": True, "PRODUCTION_MUTATION_GUARD_ACTIVE": True,
        "WRITE_ATTEMPT_INSERT": write_rejections.get("INSERT", "NOT_APPLICABLE"),
        "WRITE_ATTEMPT_UPDATE": write_rejections.get("UPDATE", "NOT_APPLICABLE"),
        "WRITE_ATTEMPT_DELETE": write_rejections.get("DELETE", "NOT_APPLICABLE"),
        "WRITE_ATTEMPT_DDL": write_rejections.get("DDL", "NOT_APPLICABLE"),
        "DATASET_SOURCE": "PRODUCTION_PAPER_READONLY" if database is not None else "OFFLINE_JSON",
        "DATABASE_BINDING": binding_source, "DATABASE_SESSION": "READ_ONLY" if session_mode == "ON" else session_mode,
        "SCHEMA_HEAD": schema_head, "PROFILE": options.profile,
        "PRIMARY_TIMEFRAME": options.primary_timeframe,
        "BASELINE_SET_ID": RESEARCH_PARAMETERS.calibration.baseline_set_id,
        "RESEARCH_MODE": mode.value, "ROWS_AVAILABLE": len(rows),
        "DATASET_ROWS": len(rows), "RAW_SEARCH_SPACE_SIZE": plan.raw_search_space_size,
        "SEARCH_STRATEGY": plan.selected_strategy, "EXHAUSTIVE": "YES" if plan.selected_strategy == "EXHAUSTIVE_LAZY" else "NO",
        "MAX_EVALUATED_CONFIGS": plan.evaluation_budget, "CONFIGURATIONS_PLANNED": plan.evaluation_budget,
        "BATCH_SIZE": plan.batch_size, "SEED": resolved_seed,
        "REQUESTED_SEED": resolved_seed, "RESOLVED_SEED": resolved_seed,
        "MEMORY_PLAN": "SAFE",
        "ESTIMATED_ACTIVE_BATCH_MEMORY_MB": plan.estimated_active_batch_memory_mb,
        "STATISTICAL_SEARCH_WARNING": plan.statistical_warning,
        "PROMOTION_EVALUATION_ALLOWED": "YES",
        "CANDIDATE_PROMOTION_ELIGIBLE": "NO",
        "EFFECTIVE_SEARCH_SPACE_SIZE": plan.effective_search_space_size,
        "INVALID_COMBINATIONS_GENERATED": 0,
        "CONDITIONAL_DIMENSION_COLLAPSE": "YES" if plan.conditional_dimension_collapse else "NO",
        "BASELINE_EVALUATED": baseline["BASELINE_EVALUATED"],
        "BASELINE_ELIGIBLE_ROWS": baseline["BASELINE_ELIGIBLE_ROWS"],
        "BASELINE_TRADES": baseline["BASELINE_TRADES"],
        "TIME_STOP_REPLAY_ELIGIBLE_ROWS": coverage["TIME_STOP_REPLAY_ELIGIBLE_ROWS"],
        "FULL_REPLAY_ELIGIBLE_ROWS": coverage["FULL_REPLAY_ELIGIBLE_ROWS"],
        "DATASET_FINGERPRINT": dataset_fingerprint,
        "DATASET_MANIFEST_HASH": dataset_manifest["manifest_hash"],
        "DATASET_CUTOFF_AT": dataset_manifest["dataset_cutoff_at"],
        "HISTORICAL_PERIOD_START_MS": dataset_manifest["historical_period_start_ms"],
        "HISTORICAL_PERIOD_END_MS": dataset_manifest["historical_period_end_ms"],
        "RUN_STARTED_AT": run_started.isoformat(),
        "OUTPUT_DIR": _display_path(output), "SECRET_OUTPUT": 0,
    }
    _write_preflight(output / "PREFLIGHT.json", preflight)
    search_plan_artifact = plan.safe_dict()
    search_plan_artifact.update({
        "RUN_ID": identifier,
        "DATASET_FINGERPRINT": dataset_fingerprint,
        "DATASET_MANIFEST_HASH": dataset_manifest["manifest_hash"],
        "DATASET_CUTOFF_AT": dataset_manifest["dataset_cutoff_at"],
        "SEARCH_PLAN_HASH": search_plan_hash,
        "CONFIG_HASH": TRADE_PARAMETERS.config_hash,
        "SEARCH_SPACE_HASH": search_space_hash,
        "SEARCH_DIMENSIONS": list(plan_state.search_dimensions),
        "DIMENSION_VALUES": plan_state.dimension_values,
        "CONDITIONAL_DIMENSIONS": list(plan_state.conditional_dimensions),
        "REQUESTED_SEED": resolved_seed,
        "RESOLVED_SEED": resolved_seed,
    })
    _atomic_json(output / "SEARCH_PLAN.json", search_plan_artifact)
    _print_preflight(preflight)
    for key in ("RAW_SEARCH_SPACE_SIZE", "SEARCH_STRATEGY", "EXHAUSTIVE", "MAX_EVALUATED_CONFIGS", "BATCH_SIZE", "SEED", "STATISTICAL_SEARCH_WARNING", "PROMOTION_EVALUATION_ALLOWED", "CANDIDATE_PROMOTION_ELIGIBLE", "MEMORY_PLAN"):
        print(f"{key} = {preflight[key]}")
    if preflight_only:
        _atomic_json(checkpoint_path, checkpoint)
        status_store.update(
            state=RunState.CANCELLED.value, phase=RunState.PREFLIGHT.value,
            resume_available=True, last_checkpoint_at=datetime.now(timezone.utc).isoformat(),
        )
        return output
    run_config = {
        "run_id": identifier,
        "research_mode": mode.value,
        "schema_version": SCHEMA_VERSION,
        "seed": resolved_seed, "requested_seed": resolved_seed,
        "resolved_seed": resolved_seed, "sampler_seed": resolved_seed,
        "search": plan.safe_dict(),
        "dataset": {"source": options.source, "profile": options.profile, "primary_timeframe": options.primary_timeframe, "closed_only": False, "selection_mode": options.selection_mode, "max_rows": options.maximum_rows},
        "dataset_period": {"from_ms": min(row.get("opened_at_ms", row.get("boundary_ms")) for row in rows), "to_ms": max(row.get("closed_at_ms", row.get("boundary_ms")) for row in rows)},
        "sample_sizes": {key: len(value) for key, value in splits.items()},
        "source_data_provenance": dataset_fingerprint, "dataset_fingerprint": dataset_fingerprint,
        "dataset_manifest_hash": dataset_manifest["manifest_hash"],
        "dataset_manifest": "DATASET_MANIFEST.json",
        "dataset_snapshot": "DATASET_SNAPSHOT.json",
        "dataset_cutoff_at": dataset_manifest["dataset_cutoff_at"],
        "dataset_row_count": len(rows),
        "dataset_min_opened_at": min(row.get("opened_at_ms", row.get("boundary_ms")) for row in rows),
        "dataset_max_closed_at": max(row.get("closed_at_ms", row.get("boundary_ms")) for row in rows),
        "dataset_profile": options.profile,
        "dataset_primary_timeframe": options.primary_timeframe,
        "baseline_set_id": RESEARCH_PARAMETERS.calibration.baseline_set_id,
        "dataset_source": options.source,
        "authoritative_trade_parameters": str(CONFIG_PATH),
        "baseline_config_hash": TRADE_PARAMETERS.config_hash, "search_space_hash": search_space_hash,
        "historical_baseline_control": {
            **baseline,
            "POPULATION": "HISTORICAL_BASELINE_CONTROL",
            "DIRECTLY_COMPARABLE_TO_CANDIDATES": "NO",
            "CONFIG_FINGERPRINT_COMPOSITION": dataset_manifest.get("composition", {}).get("configuration_fingerprint", {}),
        },
        "search_validation_baseline": search_validation_baseline,
        "baseline_control": baseline, "dataset_coverage": coverage,
        "RUN_STARTED_AT": run_started.isoformat(), "RUN_FINISHED_AT": None,
        "RUN_DURATION_SECONDS": None, "RUN_DURATION_HUMAN": None,
        "time_stop_policy_schema": "StalePositionPolicyParameters",
        "time_stop_evaluator": "app.engine_paper.stale_position_shadow.evaluate_stale_position_shadow",
        "search_space_config": str(search_path), "git_commit": git_commit,
        "database_binding": binding_source, "database_session": "READ_ONLY" if session_mode == "ON" else session_mode,
        "schema_head": schema_head, "production_mutations": 0, "production_config_writes": 0,
        "approvals_created": 0, "commands_created": 0, "positions_created": 0, "binance_order_api_calls": 0,
    }
    run_config.update({
        "historical_data_universe": historical_summary,
        "replay_capabilities": replay_capabilities,
        "parameter_registry": parameter_registry,
        "baseline_parity": baseline.get("PARITY", {}),
        "holdout_used_for_search": False,
    })
    registry_artifact = {
        **(sensitivity or {
            "declared_families": [], "active_families": [],
            "active_dimensions": space, "no_op_dimensions": {}, "excluded_dimensions": {},
            "raw_config_count": plan.raw_search_space_size,
            "unique_effective_config_count": plan.effective_search_space_size,
        }),
        "dimensions": parameter_registry,
    }
    _atomic_json(output / "PARAMETER_REGISTRY.json", registry_artifact)
    if historical_summary:
        _atomic_json(output / "HISTORICAL_DATASET_SUMMARY.json", historical_summary)
        _atomic_json(output / "REPLAY_CAPABILITIES.json", replay_capabilities)
        _atomic_json(output / "BASELINE_PARITY.json", baseline.get("PARITY", {}))
        _atomic_json(output / "HISTORICAL_DATA_SOURCE_INVENTORY.json", source_inventory)
    if not resume:
        DEFAULT_ARTIFACT_WRITER.atomic_text(
            output / "RUN_CONFIG.yaml", yaml.safe_dump(run_config, sort_keys=False),
            operation="run_config_replace",
        )
    status_store.update(
        state=RunState.REPLAY_VALIDATION.value,
        phase=RunState.REPLAY_VALIDATION.value,
        current_config_index=None,
        current_config=None,
    )
    emit(
        EventType.REPLAY_VALIDATION_STARTED,
        replay_diagnostics=replay_diagnostics.as_dict(),
    )
    contract_failure = None
    if int(baseline["BASELINE_ELIGIBLE_ROWS"]) == 0 or int(baseline["BASELINE_TRADES"]) == 0:
        contract_failure = "BASELINE_REPLAY_INVALID"
    elif (
        replay_capabilities and not any(
            value.get("STATUS") == "READY" for value in replay_capabilities.values()
        )
    ) or (not replay_capabilities and int(coverage["TIME_STOP_REPLAY_ELIGIBLE_ROWS"]) == 0):
        contract_failure = "NO_REPLAYABLE_ROWS_FOR_REQUIRED_DIMENSIONS"
    if contract_failure is not None:
        structured_error = _structured_replay_error(contract_failure)
        failed_at = datetime.now(timezone.utc)
        failure_timing = _timing(run_started, failed_at)
        failure_timing["RUN_FAILED_AT"] = failure_timing.pop("RUN_FINISHED_AT")
        checkpoint.update(failure_timing)
        checkpoint.update({
            "STATUS": "FAILED", "FAILURE_CODE": structured_error.error_code,
            "FAILURE_REASON": contract_failure, "completed": False,
            "SEARCH_ABORTED_BEFORE_5000_CONFIGS": "YES",
        })
        _atomic_json(checkpoint_path, checkpoint)
        run_config.update(failure_timing)
        run_config.update({
            "STATUS": "FAILED", "FAILURE_CODE": structured_error.error_code,
            "FAILURE_REASON": contract_failure,
        })
        DEFAULT_ARTIFACT_WRITER.atomic_text(
            output / "RUN_CONFIG.yaml", yaml.safe_dump(run_config, sort_keys=False),
            operation="run_config_replace",
        )
        preflight.update({
            "PARAMETER_SWEEP_PREFLIGHT": "FAILED", "REASON": contract_failure,
            "STATUS": "FAILED", "FAILURE_CODE": structured_error.error_code,
            "SEARCH_ABORTED_BEFORE_5000_CONFIGS": "YES", **failure_timing,
        })
        _write_preflight(output / "PREFLIGHT.json", preflight)
        DEFAULT_ARTIFACT_WRITER.atomic_text(
            output / "REPORT.md",
            "# Scalping v2 parameter sweep\n\n"
            "## RUN SUMMARY\n\n"
            f"- RUN_ID: `{identifier}`\n- STATUS: `FAILED`\n"
            f"- FAILURE_CODE: `{structured_error.error_code}`\n"
            f"- FAILURE_REASON: `{contract_failure}`\n"
            f"- RUN_STARTED_AT: `{failure_timing['RUN_STARTED_AT']}`\n"
            f"- RUN_FAILED_AT: `{failure_timing['RUN_FAILED_AT']}`\n"
            f"- RUN_DURATION_SECONDS: {failure_timing['RUN_DURATION_SECONDS']}\n\n"
            "## FROZEN DATASET\n\n"
            f"- Cutoff: `{dataset_manifest['dataset_cutoff_at']}`\n"
            f"- Period: `{dataset_manifest['historical_period_start_ms']}..{dataset_manifest['historical_period_end_ms']}`\n"
            f"- Manifest hash: `{dataset_manifest['manifest_hash']}`\n\n"
            "## SEARCH PLAN\n\n"
            f"- RAW_SEARCH_SPACE_SIZE: {plan.raw_search_space_size}\n"
            f"- PLANNED_CONFIGS: {plan.evaluation_budget}\n"
            f"- PROCESSED_CONFIGS: 0\n"
            f"- SELECTED_STRATEGY: `{plan.selected_strategy}`\n\n"
            "## BASELINE CONTROL\n\n"
            f"- BASELINE_EVALUATED: `YES`\n- BASELINE_TRADES: {baseline['BASELINE_TRADES']}\n"
            f"- BASELINE_ELIGIBLE_ROWS: {baseline['BASELINE_ELIGIBLE_ROWS']}\n\n"
            "## REPLAY CAPABILITY\n\n"
            f"- DATASET_ROWS: {len(rows)}\n"
            f"- OUTCOME_REPLAY_ROWS: {replay_diagnostics.outcome_replay_rows}\n"
            f"- TIME_STOP_REPLAY_ELIGIBLE_ROWS: {coverage['TIME_STOP_REPLAY_ELIGIBLE_ROWS']}\n"
            f"- FULL_REPLAY_ELIGIBLE_ROWS: {coverage['FULL_REPLAY_ELIGIBLE_ROWS']}\n"
            f"- POST_INSTRUMENTATION_ROWS: {replay_diagnostics.post_instrumentation_rows}\n"
            f"- MISSING_MARKET_TIMELINE_ROWS: {replay_diagnostics.missing_market_timeline_rows}\n"
            f"- MISSING_COST_TIMELINE_ROWS: {replay_diagnostics.missing_cost_timeline_rows}\n"
            f"- Unavailable reasons: `{json.dumps(coverage['REPLAY_REASON_COUNTS'], sort_keys=True)}`\n\n"
            "## SAFETY\n\n- Production mutations: `0`; Binance order calls: `0`; LIVE unchanged.\n",
            operation="report_replace",
        )
        status_store.update(
            state=RunState.FAILED.value, phase=RunState.REPLAY_VALIDATION.value,
            planned_configs=plan.evaluation_budget, completed_configs=0,
            current_config_index=None, current_config=None,
            finished_at=failed_at.isoformat(),
            duration_seconds=float(failure_timing["RUN_DURATION_SECONDS"]),
            failure_reason=contract_failure,
            failure_code=structured_error.error_code,
            error_title_ru=structured_error.error_title_ru,
            error_message_ru=structured_error.error_message_ru,
            error_details=structured_error.error_details,
            replay_diagnostics=replay_diagnostics.as_dict(),
            error_configs=1, resume_available=False,
        )
        emit(EventType.INTEGRITY_CHECK_STARTED, terminal_state="FAILED_BEFORE_EVALUATION")

        def failed_integrity_file(name: str, passed: bool, error: str | None) -> None:
            emit(EventType.INTEGRITY_FILE_CHECKED, file=name, passed=passed, error=error)

        failed_integrity = verify_artifacts(
            output,
            expected_run_id=identifier,
            expected_dataset_fingerprint=dataset_fingerprint,
            expected_config_hash=TRADE_PARAMETERS.config_hash,
            expected_count=0,
            terminal_state="FAILED_BEFORE_EVALUATION",
            on_file_checked=failed_integrity_file,
        )
        emit(
            EventType.INTEGRITY_CHECK_COMPLETED,
            status=failed_integrity["integrity_status"], integrity=failed_integrity,
        )
        emit(
            EventType.RUN_FAILED,
            reason=contract_failure,
            **structured_error.as_dict(),
            replay_diagnostics=replay_diagnostics.as_dict(),
            failed_before_first_config=True,
            completed=0,
            planned=plan.evaluation_budget,
            current_config_index=None,
            resume_available=False,
        )
        raise SweepExpectedError(contract_failure)
    jsonl = output / "RESULTS.jsonl"
    csv_path = output / "RESULTS.csv"
    csv_fields = ["result_index", "config_hash", "stage", "result_status", "validation_expectancy", "validation_drawdown", "validation_trades", "parameters_json"]
    result_writer = DurableResultWriter(
        output, csv_fields,
        transform=lambda value: compact_result(
            value,
            baseline_config_hash=TRADE_PARAMETERS.config_hash,
            research_config_hash=research_hash,
        ),
    )
    candidate_variants = _conditional_variants(space)
    if plan.selected_strategy == "TARGETED_STAGED":
        targeted_items = iter(targeted_candidates or ())
        candidate_source = enumerate(targeted_items)
    else:
        candidate_source = enumerate(_candidate_indices(plan))
    batch_active = 0
    batches_this_call = 0
    finalist_candidates: list[tuple[tuple[float, float, int], str, list[dict[str, Any]]]] = []
    counterfactual_count = 0
    counterfactual_examples: list[dict[str, Any]] = []
    if not jsonl.exists():
        DEFAULT_ARTIFACT_WRITER.atomic_text(jsonl, "", operation="results_jsonl_initialize")
    if not csv_path.exists():
        result_writer._write_csv([])
    with result_writer._lock:
        for candidate_offset, raw_value in candidate_source:
            if candidate_offset <= int(checkpoint["last_candidate_offset"]):
                continue
            if int(checkpoint["evaluated_count"]) >= plan.evaluation_budget:
                break
            current_stage = raw_value.stage if plan.selected_strategy == "TARGETED_STAGED" else _stage_for(plan, int(checkpoint["evaluated_count"]))
            next_index = int(checkpoint["last_durable_result_index"]) + 1
            candidate = raw_value.overrides if plan.selected_strategy == "TARGETED_STAGED" else _candidate_config(
                space, raw_value, conditional_variants=candidate_variants,
            )
            resolved_config = {**baseline_config, **candidate}
            changed_parameters = {
                key: value for key, value in candidate.items()
                if baseline_config.get(key) != value
            }
            status_store.update(
                state=RunState.RUNNING_CONFIG.value,
                phase=RunState.RUNNING_CONFIG.value,
                current_config_index=next_index + 1,
                current_config=resolved_config,
            )
            emit(
                EventType.CONFIG_STARTED,
                index=next_index + 1, planned=plan.evaluation_budget,
                changed_parameters=changed_parameters,
                resolved_config=resolved_config,
                stage=current_stage,
                parameter_family=next((family for family, names in search.get("calibration", {}).get("parameter_families", {}).items() if set(changed_parameters) & set(names)), "BASELINE"),
            )
            emit(
                EventType.CONFIG_PROGRESS,
                completed=int(checkpoint["evaluated_count"]),
                planned=plan.evaluation_budget,
            )
            item, consumed_budget, early_reason = _evaluate_config(
                resolved_config, splits, search["minimum_samples"],
                index=next_index, stage=current_stage,
            )
            item["overrides"] = changed_parameters
            item["run_id"] = identifier
            item["resolved_seed"] = resolved_seed
            for split_name in ("calibration", "validation", "holdout"):
                for trade in item.get(split_name, {}).get("trades", []):
                    if trade.get("historically_rejected"):
                        counterfactual_count += 1
                        if len(counterfactual_examples) < RESEARCH_PARAMETERS.artifact.max_counterfactual_examples:
                            counterfactual_examples.append({
                                "opportunity_id": trade.get("causal_opportunity") or trade.get("candidate_id"),
                                "baseline_disposition": "HISTORICALLY_REJECTED",
                                "counterfactual_config": item.get("config_hash"),
                                "counterfactual_disposition": "SIMULATED_TRADE",
                                "reason_changed": f"{trade.get('historical_rejection_reason')}->{trade.get('exit_reason')}",
                            })
            validation_metrics = item.get("validation", {})
            if item.get("result_status") == "ACCEPTED":
                detailed = []
                for split_name in ("calibration", "validation", "holdout"):
                    for trade in item.get(split_name, {}).get("trades", [])[: RESEARCH_PARAMETERS.artifact.max_detailed_trades_per_config]:
                        detailed.append({"config_id": item["config_hash"], "split": split_name, "resolved_seed": resolved_seed, **compact_trade(trade, str(dataset_manifest["manifest_hash"]))})
                score = (
                    float(validation_metrics.get("net_expectancy_per_trade") or -1e12),
                    -float(validation_metrics.get("max_drawdown") or 0),
                    int(validation_metrics.get("trade_count") or 0),
                )
                finalist_candidates.append((score, item["config_hash"], detailed))
                finalist_candidates.sort(reverse=True, key=lambda value: (value[0], value[1]))
                del finalist_candidates[RESEARCH_PARAMETERS.artifact.finalist_config_count:]
            emit(EventType.CONFIG_COMPLETED, index=next_index + 1, result=item)
            status_store.update(
                state=RunState.WRITING_RESULT.value,
                phase=RunState.WRITING_RESULT.value,
            )
            emit(EventType.RESULT_WRITE_STARTED, index=next_index + 1)
            result_writer.append(item)
            result_class = compact_result(item)["performance_class"]
            status_store.update(
                current_stage=current_stage,
                current_parameter_family=next((family for family, names in search.get("calibration", {}).get("parameter_families", {}).items() if set(changed_parameters) & set(names)), "BASELINE"),
                artifact_bytes=sum(path.stat().st_size for path in output.glob("*") if path.is_file()),
                artifact_soft_budget_bytes=RESEARCH_PARAMETERS.artifact.soft_total_bytes,
                artifact_hard_budget_bytes=RESEARCH_PARAMETERS.artifact.hard_total_bytes,
                negative_expectancy_configs=status_store.status.negative_expectancy_configs + int(result_class == "NEGATIVE_EXPECTANCY"),
                promising_configs=status_store.status.promising_configs + int(result_class == "PROMISING_RESEARCH"),
                validation_candidate_configs=status_store.status.validation_candidate_configs + int(result_class == "VALIDATION_CANDIDATE"),
            )
            emit(EventType.RESULT_WRITE_COMPLETED, index=next_index + 1)
            checkpoint["last_candidate_offset"] = candidate_offset
            checkpoint["last_durable_result_index"] = item["result_index"]
            checkpoint["stage"] = current_stage
            if consumed_budget:
                checkpoint["evaluated_count"] = int(checkpoint["evaluated_count"]) + 1
                if item["result_status"] == "ACCEPTED":
                    checkpoint["accepted_count"] = int(checkpoint["accepted_count"]) + 1
                else:
                    checkpoint["rejected_count"] = int(checkpoint["rejected_count"]) + 1
                if item["result_status"] == "EARLY_REJECTED":
                    checkpoint["early_reject_count"] = int(checkpoint["early_reject_count"]) + 1
            else:
                checkpoint["pruned_count"] = int(checkpoint["pruned_count"]) + 1
            if early_reason and consumed_budget:
                reasons = checkpoint.setdefault("early_reject_reasons", {})
                reasons[early_reason] = int(reasons.get(early_reason, 0)) + 1
            checkpoint["checkpoint_count"] = int(checkpoint["checkpoint_count"]) + 1
            checkpoint["durable_result_count"] = len(result_writer.read_all())
            _atomic_json(checkpoint_path, checkpoint)
            checkpoint_at = datetime.now(timezone.utc).isoformat()
            result_status = str(item["result_status"])
            insufficient = result_class == "INSUFFICIENT_SAMPLE"
            if insufficient:
                checkpoint["insufficient_count"] = int(checkpoint.get("insufficient_count", 0)) + 1
                _atomic_json(checkpoint_path, checkpoint)
            live_semantics = aggregate_result_semantics(
                result_writer.read_all(),
                error_count=int(checkpoint["failed_count"]),
            )
            checkpoint["evaluation_status_counts"] = live_semantics["evaluation_status_counts"]
            checkpoint["performance_class_counts"] = live_semantics["performance_class_counts"]
            checkpoint["classification_counts"] = live_semantics["performance_class_counts"]
            _atomic_json(checkpoint_path, checkpoint)
            status_store.update(
                completed_configs=int(checkpoint["evaluated_count"]),
                accepted_configs=live_semantics["accepted_configs"],
                rejected_configs=live_semantics["rejected_configs"],
                insufficient_configs=int(checkpoint.get("insufficient_count", 0)),
                error_configs=int(checkpoint["failed_count"]),
                evaluation_status_counts=live_semantics["evaluation_status_counts"],
                performance_class_counts=live_semantics["performance_class_counts"],
                last_checkpoint_at=checkpoint_at,
                resume_available=True,
            )
            emit(
                EventType.CHECKPOINT_WRITTEN,
                index=next_index + 1, at=checkpoint_at,
                completed=int(checkpoint["evaluated_count"]),
                accepted=live_semantics["accepted_configs"],
                rejected=live_semantics["rejected_configs"],
                errors=int(checkpoint["failed_count"]),
                insufficient=status_store.status.insufficient_configs,
                evaluation_status_counts=live_semantics["evaluation_status_counts"],
                performance_class_counts=live_semantics["performance_class_counts"],
                artifact_bytes=sum(path.stat().st_size for path in output.glob("*") if path.is_file()),
                artifact_soft_budget_bytes=RESEARCH_PARAMETERS.artifact.soft_total_bytes,
                artifact_hard_budget_bytes=RESEARCH_PARAMETERS.artifact.hard_total_bytes,
                negative_expectancy=status_store.status.negative_expectancy_configs,
                promising=status_store.status.promising_configs,
                validation_candidates=status_store.status.validation_candidate_configs,
            )
            if stop_requested is not None and stop_requested():
                checkpoint["STATUS"] = "CANCELLED"
                checkpoint["completed"] = False
                _atomic_json(checkpoint_path, checkpoint)
                status_store.update(
                    state=RunState.CANCELLED.value,
                    phase=RunState.CANCELLED.value,
                    cancel_requested=True,
                    resume_available=True,
                )
                emit(
                    EventType.RUN_CANCELLED,
                    completed=int(checkpoint["evaluated_count"]), resume_available=True,
                )
                return output
            batch_active += 1
            if batch_active >= plan.batch_size:
                batches_this_call += 1
                batch_active = 0
                if stop_after_batches is not None and batches_this_call >= stop_after_batches:
                    return output
    status_store.update(state=RunState.FINALIZING.value, phase=RunState.FINALIZING.value)
    emit(EventType.RUN_FINALIZING)
    checkpoint["completed"] = int(checkpoint["evaluated_count"]) == plan.evaluation_budget
    finished_timing = _timing(run_started)
    checkpoint.update(finished_timing)
    checkpoint["STATUS"] = "COMPLETED" if checkpoint["completed"] else "INCOMPLETE"
    _atomic_json(checkpoint_path, checkpoint)
    _stream_json_array(jsonl, output / "RESULTS.json")
    _stream_json_array(jsonl, output / "REJECTED_CONFIGS.json", rejected_only=True)
    all_result_rows = list(iter_results(jsonl))
    accepted_rows = [row for row in all_result_rows if row["evaluation_status"] == "ACCEPTED"]
    rejected_rows = [row for row in all_result_rows if row["evaluation_status"] != "ACCEPTED"]
    canonical_semantics = aggregate_result_semantics(
        all_result_rows, error_count=int(checkpoint["failed_count"]),
    )
    checkpoint["insufficient_count"] = canonical_semantics["insufficient_configs"]
    checkpoint["classification_counts"] = canonical_semantics["classification_counts"]
    checkpoint["evaluation_status_counts"] = canonical_semantics["evaluation_status_counts"]
    checkpoint["performance_class_counts"] = canonical_semantics["performance_class_counts"]
    checkpoint["validation_readiness"] = canonical_semantics["validation_readiness"]
    _atomic_json(checkpoint_path, checkpoint)
    status_store.update(
        insufficient_configs=canonical_semantics["insufficient_configs"],
        accepted_configs=canonical_semantics["accepted_configs"],
        rejected_configs=canonical_semantics["rejected_configs"],
        error_configs=canonical_semantics["error_configs"],
        validation_candidate_configs=canonical_semantics["promotable_candidate_count"],
        classification_counts=canonical_semantics["classification_counts"],
        evaluation_status_counts=canonical_semantics["evaluation_status_counts"],
        performance_class_counts=canonical_semantics["performance_class_counts"],
        validation_readiness=canonical_semantics["validation_readiness"],
    )
    DEFAULT_ARTIFACT_WRITER.atomic_text(output / "ACCEPTED_CONFIGS.jsonl", "".join(json.dumps(row, sort_keys=True) + "\n" for row in accepted_rows) or "\n", operation="accepted_configs_v2")
    DEFAULT_ARTIFACT_WRITER.atomic_text(output / "REJECTED_CONFIGS.jsonl", "".join(json.dumps(row, sort_keys=True) + "\n" for row in rejected_rows) or "\n", operation="rejected_configs_v2")
    finalist_rows = [trade for _score, _config_id, trades in finalist_candidates for trade in trades]
    DEFAULT_ARTIFACT_WRITER.atomic_text(output / "FINALIST_TRADES.jsonl", "".join(json.dumps(row, sort_keys=True) + "\n" for row in finalist_rows) or "\n", operation="finalist_trades_v2")
    top = _aggregate_results(output)
    _atomic_json(output / "TOP_CONFIGS.json", top)
    _atomic_json(output / "RUN_MANIFEST.json", {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "run_id": identifier,
        "dataset_manifest_ref": "DATASET_MANIFEST.json",
        "baseline_set_id": RESEARCH_PARAMETERS.calibration.baseline_set_id,
        "baseline_config_hash": TRADE_PARAMETERS.config_hash,
        "research_config_hash": research_hash,
        "search_space_hash": search_space_hash,
        "engine_compatibility": SCHEMA_VERSION,
        "seed": resolved_seed,
        "requested_seed": resolved_seed,
        "resolved_seed": resolved_seed,
        "sampler_seed": resolved_seed,
    })
    try:
        size_status = enforce_size_budget(output)
    except ArtifactSizeBudgetExceeded as error:
        raise SweepExpectedError(str(error)) from error
    _atomic_json(output / "ARTIFACT_SIZES.json", size_status)
    configs_per_observation = int(checkpoint["evaluated_count"]) / len(rows)
    run_config.update(finished_timing)
    DEFAULT_ARTIFACT_WRITER.atomic_text(
        output / "RUN_CONFIG.yaml", yaml.safe_dump(run_config, sort_keys=False),
        operation="run_config_replace",
    )
    try:
        opportunity_funnel = build_opportunity_funnel(
            all_result_rows, counterfactual_count=counterfactual_count,
            counterfactual_examples=counterfactual_examples,
            error_count=int(checkpoint["failed_count"]),
        )
    except ValueError as error:
        raise SweepExpectedError(str(error)) from None
    aggregate_funnel = opportunity_funnel["AGGREGATE_FUNNEL"]
    _atomic_json(output / "OPPORTUNITY_FUNNEL.json", opportunity_funnel)
    coverage_table = "\n".join(
        f"| {item['FIELD']} | {item['ROWS_PRESENT']} | {item['ROWS_MISSING']} | "
        f"{item['COVERAGE_PERCENT']} | {item['REPLAY_REQUIRED']} |"
        for item in coverage["FIELD_COVERAGE"]
    )
    split_table = "\n".join(
        f"| {name} | {len(split_rows)} | "
        f"{_dataset_coverage(split_rows)['TIME_STOP_REPLAY_ELIGIBLE_ROWS']} | "
        f"{len(split_rows) - _dataset_coverage(split_rows)['TIME_STOP_REPLAY_ELIGIBLE_ROWS']} |"
        for name, split_rows in splits.items()
    )
    report = f"""# Scalping v2 parameter sweep

## RUN SUMMARY

- RUN_ID: `{identifier}`
- RUN_STARTED_AT: `{finished_timing['RUN_STARTED_AT']}`
- RUN_FINISHED_AT: `{finished_timing['RUN_FINISHED_AT']}`
- RUN_DURATION_SECONDS: {finished_timing['RUN_DURATION_SECONDS']}
- RUN_DURATION_HUMAN: `{finished_timing['RUN_DURATION_HUMAN']}`
- STATUS: `{checkpoint['STATUS']}`

## RUNTIME

- Git commit: `{git_commit}`; schema: `{schema_head}`; database session: `{'READ_ONLY' if session_mode == 'ON' else session_mode}`.
- Production mutations/config writes/approvals/commands/positions: `0`; Binance order calls: `0`; LIVE unchanged.

## DATASET COVERAGE

- Source/profile/rows: `{preflight['DATASET_SOURCE']}` / `{options.profile}` / {len(rows)}
- Fingerprint: `{dataset_fingerprint}`
- Frozen cutoff: `{dataset_manifest['dataset_cutoff_at']}`
- Frozen historical period: `{dataset_manifest['historical_period_start_ms']}..{dataset_manifest['historical_period_end_ms']}`
- Dataset manifest hash: `{dataset_manifest['manifest_hash']}`
- Historical market 1m / 5m rows: {historical_summary.get('MARKET_1M_ROWS', 'N/A')} / {historical_summary.get('MARKET_5M_ROWS', 'N/A')}
- Opportunity universe / persisted closed trades: {historical_summary.get('TOTAL_OPPORTUNITY_UNIVERSE', 'N/A')} / {historical_summary.get('PERSISTED_CLOSED_POSITIONS', 'N/A')}
- Reconstructed-only / historically rejected opportunities: {historical_summary.get('TOTAL_RECONSTRUCTED_ONLY_CANDIDATES', 'N/A')} / {historical_summary.get('TOTAL_HISTORICALLY_REJECTED', 'N/A')}

| FIELD | ROWS_PRESENT | ROWS_MISSING | COVERAGE_PERCENT | REPLAY_REQUIRED |
|---|---:|---:|---:|---|
{coverage_table}

## HISTORICAL_BASELINE_CONTROL

- BASELINE_CONFIG_HASH: `{baseline['BASELINE_CONFIG_HASH']}`
- BASELINE_CONFIG_VERSION: `{baseline['BASELINE_CONFIG_VERSION']}`
- BASELINE_EVALUATED: `YES`; BASELINE_REPLAY_VALID: `{'YES' if baseline['BASELINE_REPLAY_VALID'] else 'NO'}`
- BASELINE_DATASET_ROWS / ELIGIBLE_ROWS / TRADES: {baseline['BASELINE_DATASET_ROWS']} / {baseline['BASELINE_ELIGIBLE_ROWS']} / {baseline['BASELINE_TRADES']}
- BASELINE_NET_PNL / EXPECTANCY / PF: {baseline['BASELINE_NET_PNL']} / {baseline['BASELINE_NET_EXPECTANCY']} / {baseline['BASELINE_PROFIT_FACTOR']}
- DIRECTLY_COMPARABLE_TO_CANDIDATES: `NO`

## SEARCH_VALIDATION_BASELINE

- SAME_SPLIT_COMPARISON: `YES`
- VALIDATION_TRADES: {search_validation_baseline['trade_count']}
- PERFORMANCE_CLASS: `{search_validation_baseline['performance_class']}`
- INSUFFICIENT_SAMPLE_GATES: `{json.dumps(search_validation_baseline['insufficient_sample_gates'], sort_keys=True)}`

## REPLAY CAPABILITY

- OUTCOME_ONLY_REPLAY_ROWS: {coverage['OUTCOME_ONLY_REPLAY_ROWS']}
- TIME_STOP_REPLAY_ELIGIBLE_ROWS: {coverage['TIME_STOP_REPLAY_ELIGIBLE_ROWS']}
- FULL_REPLAY_ELIGIBLE_ROWS: {coverage['FULL_REPLAY_ELIGIBLE_ROWS']}
- PRE/POST_TIME_STOP_INSTRUMENTATION_ROWS: {coverage['PRE_TIME_STOP_INSTRUMENTATION_ROWS']} / {coverage['POST_TIME_STOP_INSTRUMENTATION_ROWS']}
- Exact unavailable reasons: `{json.dumps(coverage['REPLAY_REASON_COUNTS'], sort_keys=True)}`
- Per-family capabilities: `{json.dumps(replay_capabilities, sort_keys=True)}`
- TIME_STOP source: `RECONSTRUCTED_FROM_MARKET_HISTORY`; persisted shadow rows are optional parity evidence.

| SPLIT | rows_total | rows_replayable | rows_unreplayable |
|---|---:|---:|---:|
{split_table}

## GATE REJECTION FUNNEL

- Aggregate exact counts: `{json.dumps(dict(sorted(aggregate_funnel.items())), sort_keys=True)}`
- `ALL_TRADES_FILTERED` without reason: `NO`
- Counterfactual historically rejected opportunities are present in `OPPORTUNITY_FUNNEL.json`.
- COUNTERFACTUAL_REJECTED_OPPORTUNITIES_SIMULATED: {counterfactual_count}

## SEARCH PLAN

- Raw search-space size: {plan.raw_search_space_size}
- Effective conditional search-space size: {plan.effective_search_space_size}
- Invalid combinations generated: `0`; conditional dimension collapse: `{'YES' if plan.conditional_dimension_collapse else 'NO'}`
- Selected strategy: `{plan.selected_strategy}`
- Requested/resolved/sampler seed: {resolved_seed}/{resolved_seed}/{resolved_seed}
- Evaluation budget: {plan.evaluation_budget}
- Staged plan: `{json.dumps(plan.staged_search_plan)}`
- Holdout used for search/refinement/ranking: `NO`

## RESULTS

- Actual evaluated configs: {checkpoint['evaluated_count']}; pruned invalid: {checkpoint['pruned_count']}
- Accepted/rejected/failed: {canonical_semantics['accepted_configs']}/{canonical_semantics['rejected_configs']}/{canonical_semantics['error_configs']}
- EVALUATION_STATUS_COUNTS: `{json.dumps(canonical_semantics['evaluation_status_counts'], sort_keys=True)}`
- PERFORMANCE_CLASS_COUNTS: `{json.dumps(canonical_semantics['performance_class_counts'], sort_keys=True)}`
- CLASSIFICATION_COUNTS: `{json.dumps(canonical_semantics['performance_class_counts'], sort_keys=True)}`
- INSUFFICIENT_CONFIGS: {canonical_semantics['insufficient_configs']}
- VALIDATION_READINESS: `{json.dumps(canonical_semantics['validation_readiness'], sort_keys=True)}`
- TOP contains only accepted, validation-evaluated configs with metrics; Pareto uses the same eligible set.

## TIME-STOP ANALYSIS

- Runtime and research reuse `StalePositionPolicyParameters` and `evaluate_stale_position_shadow`.
- Persisted `scalping_stale_position_shadow_diagnostics` observations are consumed in causal timestamp order.
- Current prices or commissions never replace missing historical evidence.

## STATISTICAL SUFFICIENCY

- Configs per observation: {configs_per_observation:.6f}
- Statistical warning: `{plan.statistical_warning}`
- PROMOTION_EVALUATION_ALLOWED: `YES`
- CANDIDATE_PROMOTION_ELIGIBLE: `{'YES' if canonical_semantics['candidate_promotion_eligible'] else 'NO'}`
- Holdout is evaluated for reporting only and never influences search/refinement/ranking.
"""
    DEFAULT_ARTIFACT_WRITER.atomic_text(
        output / "REPORT.md", report, operation="report_replace",
    )
    status_store.update(
        state=RunState.VERIFYING_ARTIFACTS.value,
        phase=RunState.VERIFYING_ARTIFACTS.value,
    )
    emit(EventType.INTEGRITY_CHECK_STARTED)

    def integrity_file(name: str, passed: bool, error: str | None) -> None:
        emit(EventType.INTEGRITY_FILE_CHECKED, file=name, passed=passed, error=error)

    integrity = verify_artifacts(
        output,
        expected_run_id=identifier,
        expected_dataset_fingerprint=dataset_fingerprint,
        expected_config_hash=TRADE_PARAMETERS.config_hash,
        expected_count=int(checkpoint["last_durable_result_index"]) + 1,
        on_file_checked=integrity_file,
    )
    emit(
        EventType.INTEGRITY_CHECK_COMPLETED,
        status=integrity["integrity_status"], integrity=integrity,
    )
    if integrity["integrity_status"] != "PASS":
        checkpoint["STATUS"] = "FAILED_INTEGRITY"
        checkpoint["completed"] = False
        _atomic_json(checkpoint_path, checkpoint)
        status_store.update(
            state=RunState.FAILED.value,
            phase=RunState.VERIFYING_ARTIFACTS.value,
            failure_reason="ARTIFACT_INTEGRITY_FAILED",
            resume_available=True,
        )
        emit(
            EventType.RUN_FAILED,
            reason="ARTIFACT_INTEGRITY_FAILED", resume_available=True,
        )
        raise SweepExpectedError("ARTIFACT_INTEGRITY_FAILED")
    DEFAULT_ARTIFACT_WRITER.append_text(
        output / "REPORT.md",
        "\n## ARTIFACT INTEGRITY\n\n- Integrity status: `PASS`.\n",
        operation="report_append_integrity",
    )
    status_store.update(
        state=RunState.COMPLETED.value, phase=RunState.COMPLETED.value,
        completed_configs=int(checkpoint["evaluated_count"]),
        finished_at=str(finished_timing["RUN_FINISHED_AT"]),
        duration_seconds=float(finished_timing["RUN_DURATION_SECONDS"]),
        resume_available=False,
    )
    emit(
        EventType.RUN_COMPLETED,
        completed=int(checkpoint["evaluated_count"]),
        duration_seconds=finished_timing["RUN_DURATION_SECONDS"],
        integrity="PASS",
    )
    print("BASELINE_EVALUATED = YES")
    print(f"BASELINE_TRADES = {baseline['BASELINE_TRADES']}")
    print(f"DATASET_ROWS = {len(rows)}")
    print(f"TIME_STOP_REPLAY_ELIGIBLE_ROWS = {coverage['TIME_STOP_REPLAY_ELIGIBLE_ROWS']}")
    print(f"FULL_REPLAY_ELIGIBLE_ROWS = {coverage['FULL_REPLAY_ELIGIBLE_ROWS']}")
    print(f"CONFIGURATIONS_EVALUATED = {checkpoint['evaluated_count']}")
    print("ALL_TRADES_FILTERED_WITHOUT_REASON = NO")
    for key in ("RUN_STARTED_AT", "RUN_FINISHED_AT", "RUN_DURATION_SECONDS"):
        print(f"{key} = {finished_timing[key]}")
    print("PRODUCTION_MUTATIONS = 0")
    return output


class ParameterSweepEngine:
    """Headless lifecycle shared by CLI, GUI controller, and tests."""

    def __init__(self, event_sink: Callable[[SweepEvent], None] | None = None) -> None:
        self.event_sink = event_sink
        self._cancel = threading.Event()
        self._run_id: str | None = None
        self._status_path: Path | None = None

    def request_stop_after_current(self) -> None:
        self._cancel.set()
        if self._run_id and self.event_sink:
            self.event_sink(SweepEvent.create(EventType.CANCEL_REQUESTED, self._run_id))
        if self._status_path and self._status_path.is_file():
            try:
                value = json.loads(self._status_path.read_text(encoding="utf-8"))
                value.update({
                    "state": RunState.CANCEL_REQUESTED.value,
                    "cancel_requested": True,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                _atomic_json(self._status_path, value)
            except (OSError, json.JSONDecodeError):
                pass

    def run(self, search_path: Path, **options: Any) -> Path:
        self._cancel.clear()
        self._run_id = options.get("run_id")
        if self._run_id:
            try:
                config = yaml.safe_load(Path(search_path).read_text(encoding="utf-8"))
                root = Path(str(config.get("output_root", "artifacts/scalping_v2_parameter_sweep")))
                if not root.is_absolute():
                    root = PROJECT_ROOT / root
                self._status_path = root / self._run_id / "STATUS.json"
            except (OSError, AttributeError, yaml.YAMLError):
                self._status_path = None
        try:
            return run(
                search_path,
                event_sink=self.event_sink,
                stop_requested=self._cancel.is_set,
                **options,
            )
        finally:
            self._status_path = None


def _heartbeat(status_path: Path, stop: threading.Event, interval: float) -> None:
    while not stop.wait(interval):
        try:
            value = json.loads(status_path.read_text(encoding="utf-8"))
            if value.get("state") in {
                RunState.COMPLETED.value, RunState.FAILED.value,
                RunState.CANCELLED.value,
            }:
                return
            value["updated_at"] = datetime.now(timezone.utc).isoformat()
            _atomic_json(status_path, value)
        except (OSError, json.JSONDecodeError):
            continue


def _sanitized_error(output: Path, error: BaseException) -> None:
    text_value = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    for key in ("DATABASE_URL", PROTECTED_READONLY_KEY, PROTECTED_RUNTIME_KEY):
        secret = os.environ.get(key)
        if secret:
            text_value = text_value.replace(secret, "[REDACTED]")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    numbered = output / f"ERROR.{stamp}.{os.getpid()}.{threading.get_ident()}.log"
    DEFAULT_ARTIFACT_WRITER.atomic_text(numbered, text_value, operation="error_snapshot")
    DEFAULT_ARTIFACT_WRITER.append_text(
        output / "ERROR.log", f"\n===== {stamp} =====\n{text_value}",
        operation="error_history_append",
    )


def run(
    search_path: Path, *, run_id: str | None = None, max_configs: int | None = None,
    max_rows: int | None = None, from_value: str | None = None,
    to_value: str | None = None, database_url: str | None = None,
    preflight_only: bool = False, verbose: bool = False, resume: bool = False,
    stop_after_batches: int | None = None,
    event_sink: Callable[[SweepEvent], None] | None = None,
    stop_requested: Callable[[], bool] | None = None,
    use_lock: bool = True,
    mode: ResearchMode | str = ResearchMode.ALL,
) -> Path:
    """Run the authoritative research engine with lock and heartbeat protection."""
    search_path = Path(search_path)
    try:
        canonical_mode = parse_research_mode(mode)
    except ValueError:
        raise SweepExpectedError("UNSUPPORTED_RESEARCH_MODE") from None
    try:
        search = _validate_search(yaml.safe_load(search_path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        raise SweepExpectedError("CONFIG_FILE_NOT_FOUND") from None
    except yaml.YAMLError:
        raise SweepExpectedError("SEARCH_SPACE_INVALID") from None
    output_root = Path(str(search.get("output_root", "artifacts/scalping_v2_parameter_sweep")))
    if not output_root.is_absolute():
        output_root = PROJECT_ROOT / output_root
    identifier = run_id or generate_run_id(output_root)
    existing_status_path = output_root / identifier / "STATUS.json"
    if resume and existing_status_path.is_file():
        try:
            existing_status = json.loads(existing_status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing_status = {}
        if existing_status.get("resume_available") is False:
            raise SweepExpectedError("RESUME_NOT_AVAILABLE")
    lock = SingleRunLock(output_root / ".parameter_sweep.lock", identifier)
    heartbeat_stop = threading.Event()
    heartbeat = threading.Thread(
        target=_heartbeat,
        args=(output_root / identifier / "STATUS.json", heartbeat_stop, 5.0),
        name=f"parameter-sweep-heartbeat-{identifier}",
        daemon=True,
    )
    if use_lock:
        lock.acquire()
    heartbeat.start()
    try:
        return _run_impl(
            search_path,
            run_id=identifier,
            max_configs=max_configs,
            max_rows=max_rows,
            from_value=from_value,
            to_value=to_value,
            database_url=database_url,
            preflight_only=preflight_only,
            verbose=verbose,
            resume=resume,
            stop_after_batches=stop_after_batches,
            event_sink=event_sink,
            stop_requested=stop_requested,
            mode=canonical_mode,
        )
    except BaseException as error:
        output = output_root / identifier
        if output.is_dir():
            try:
                _sanitized_error(output, error)
            except BaseException:
                pass
            if isinstance(error, SweepExpectedError) and not resume:
                status_path = output / "STATUS.json"
                try:
                    value = json.loads(status_path.read_text(encoding="utf-8"))
                    if value.get("state") not in {
                        RunState.COMPLETED.value, RunState.FAILED.value,
                        RunState.CANCELLED.value,
                    }:
                        value.update({
                            "state": RunState.FAILED.value,
                            "failure_reason": error.reason,
                            "failure_code": error.reason,
                            "resume_available": False,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        })
                        _atomic_json(status_path, value)
                except (OSError, json.JSONDecodeError):
                    pass
            if isinstance(error, SweepExpectedError) and error.reason == "CHECKPOINT_WRITE_FAILED":
                status_path = output / "STATUS.json"
                try:
                    value = json.loads(status_path.read_text(encoding="utf-8"))
                    value.update({
                        "state": RunState.FAILED.value,
                        "phase": RunState.WRITING_RESULT.value,
                        "failure_reason": "CHECKPOINT_WRITE_FAILED",
                        "failure_code": "CHECKPOINT_WRITE_FAILED",
                        "error_title_ru": "Не удалось сохранить контрольную точку",
                        "error_message_ru": "Результаты сохранены, запуск безопасно остановлен до следующей конфигурации.",
                        "error_details": {
                            "operation": "checkpoint_replace",
                            "path": str(output / "CHECKPOINT.json"),
                        },
                        "resume_available": True,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })
                    DEFAULT_ARTIFACT_WRITER.atomic_json(
                        status_path, value, operation="status_checkpoint_failure",
                    )
                except BaseException:
                    pass
        raise
    finally:
        heartbeat_stop.set()
        heartbeat.join(timeout=1.0)
        if use_lock:
            lock.release()


def main() -> None:
    from .cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
