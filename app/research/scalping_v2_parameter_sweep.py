"""Manual deterministic offline parameter sweep for Scalping v2."""

from __future__ import annotations

import argparse
import csv
from collections import ChainMap
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import subprocess
from typing import Any, Iterator, Mapping

import yaml
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.engine import Connection, URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config.trade_parameters import (
    CONFIG_PATH, SCALPING_V2, TRADE_PARAMETERS, StalePositionPolicyParameters,
)
from app.db.paper_models import (
    PaperExecutionCommandRecord, PaperOrderRecord, PaperPositionRecord,
    ScalpingOpportunityRecord, ScalpingOutcomeDiagnosticRecord,
)
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.engine_paper.scalping_policy_v2 import EmpiricalSetupBucket, evaluate_expectancy
from app.engine_paper.stale_position_shadow import (
    StalePositionInputs, evaluate_stale_position_shadow,
)

SCHEMA_VERSION = "SCALPING_V2_PARAMETER_SWEEP/2"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTECTED_BINDING_PATH = PROJECT_ROOT / ".env.production.local"
PROTECTED_READONLY_KEY = "TRADERS_READONLY_API_DATABASE_URL"
PROTECTED_RUNTIME_KEY = "TRADERS_PAPER_RUNTIME_DATABASE_URL"
DATASET_SOURCE = "production_paper_readonly"
LEGACY_DATASET_SOURCE = "postgres-paper-outcomes-readonly"
DEFAULT_MAX_ROWS = 5_000
REQUIRED_TABLES = frozenset({
    "alembic_version", "paper_positions", "paper_orders",
    "paper_execution_commands", "online_pipeline_runs",
    "online_pipeline_results",
})
TIME_STOP_SEARCH_FIELDS = frozenset({
    "soft_timeout_seconds", "hard_timeout_seconds",
    "min_target_progress_at_soft_timeout", "min_mfe_bps_at_soft_timeout",
    "min_remaining_ev_r_at_soft_timeout", "extension_seconds", "max_extensions",
    "break_even_activation_target_progress", "net_break_even_protection_enabled",
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
    closed_only: bool = True
    maximum_rows: int = DEFAULT_MAX_ROWS
    from_time: datetime | None = None
    to_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class SearchPlan:
    raw_search_space_size: int
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

    def safe_dict(self) -> dict[str, object]:
        return {
            "RAW_SEARCH_SPACE_SIZE": self.raw_search_space_size,
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
        }


class ParameterSweepSearchPlanner:
    """Transparent deterministic planner for exhaustive or bounded exploration."""

    BYTES_PER_ACTIVE_CONFIG = 256 * 1024
    MAX_ACTIVE_BATCH_MEMORY_MB = 64.0

    @staticmethod
    def raw_cardinality(space: Mapping[str, list[object]]) -> int:
        return math.prod(len(values) for values in space.values())

    def plan(
        self, *, dataset_rows: int, space: Mapping[str, list[object]],
        search: Mapping[str, object], max_configs_override: int | None = None,
        validation_rows: int = 0, holdout_rows: int = 0,
        available_replay_rows: int = 0,
    ) -> SearchPlan:
        raw = self.raw_cardinality(space)
        strategy = str(search.get("strategy", "auto")).lower()
        if strategy not in {"auto", "exhaustive", "bounded"}:
            raise SweepExpectedError("SEARCH_SPACE_INVALID")
        seed = int(search.get("seed", 20260907))
        exhaustive_threshold = int(search.get("exhaustive_max_configs", 10_000))
        configured_budget = int(search.get("max_evaluated_configs", 5_000))
        per_observation = float(search.get("max_configs_per_observation", 100.0))
        statistical_cap = max(1, int(dataset_rows * per_observation))
        budget = min(raw, configured_budget, statistical_cap)
        if max_configs_override is not None:
            if max_configs_override <= 0:
                raise SweepExpectedError("SEARCH_SPACE_INVALID")
            budget = min(budget, max_configs_override)
        exhaustive = raw <= exhaustive_threshold and strategy != "bounded"
        if strategy == "exhaustive" and raw > exhaustive_threshold:
            raise SweepExpectedError("UNSAFE_EXHAUSTIVE_SEARCH")
        selected = "EXHAUSTIVE_LAZY" if exhaustive else "AUTO_BOUNDED"
        requested_batch = int(search.get("batch_size", 100))
        safe_batch = int(
            self.MAX_ACTIVE_BATCH_MEMORY_MB * 1024 * 1024
            / self.BYTES_PER_ACTIVE_CONFIG
        )
        batch = min(requested_batch, safe_batch, budget)
        if batch < 1:
            raise SweepExpectedError("UNSAFE_MEMORY_PLAN")
        fractions = (
            float(search.get("stage1_fraction", .60)),
            float(search.get("stage2_fraction", .30)),
            float(search.get("stage3_fraction", .10)),
        )
        if any(value < 0 for value in fractions) or not math.isclose(sum(fractions), 1.0):
            raise SweepExpectedError("SEARCH_SPACE_INVALID")
        counts = [int(budget * fractions[0]), int(budget * fractions[1])]
        counts.append(budget - sum(counts))
        stages = tuple(
            {"stage": name, "budget": count, "uses_holdout": False}
            for name, count in zip(
                ("BROAD_EXPLORATION", "VALIDATION_REFINEMENT", "LOCAL_REFINEMENT"),
                counts, strict=True,
            )
        )
        minimum_validation = int(search.get("minimum_validation_sample", 20))
        minimum_holdout = int(search.get("minimum_holdout_sample", 20))
        warning = (
            "LARGE_HYPOTHESIS_SPACE_SMALL_SAMPLE"
            if raw > exhaustive_threshold and dataset_rows < configured_budget else "NONE"
        )
        promotion = (
            warning == "NONE" and validation_rows >= minimum_validation
            and holdout_rows >= minimum_holdout and budget == raw
        )
        return SearchPlan(
            raw, {name: len(values) for name, values in sorted(space.items())},
            available_replay_rows, selected, budget, batch, seed, stages,
            "RAW_SPACE_WITHIN_EXHAUSTIVE_THRESHOLD" if exhaustive
            else "RAW_SPACE_EXCEEDS_SAFE_EXHAUSTIVE_THRESHOLD",
            warning, promotion,
            round(batch * self.BYTES_PER_ACTIVE_CONFIG / 1024 / 1024, 3),
        )


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
    size = plan.raw_search_space_size
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


def _production_rows(
    database: ReadOnlyResearchDatabase,
    options: DatasetOptions,
) -> list[dict[str, Any]]:
    """Load bounded PAPER truth through the SELECT-only research adapter."""
    if not 1 <= options.maximum_rows <= DEFAULT_MAX_ROWS:
        raise SweepExpectedError("MAX_ROWS_OUT_OF_RANGE")
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
    rows: list[dict[str, Any]] = []
    for position, command, result, outcome, opportunity in records:
        diagnostic = _nested(
            result.paper_payload_json, "paper_context", "scalping_geometry_diagnostics"
        ) or {}
        fees = float(position.entry_fees + position.exit_fees)
        net_pnl = float(position.realized_pnl or 0)
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
            # Historical closed rows without timestamped market/cost observations
            # remain explicitly unreplayable; current commission is never substituted.
            "time_stop_observations": [],
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


def _config_hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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
    ordered = sorted(rows, key=lambda row: (row.get("closed_at_ms", 0), row.get("position_id", "")))
    random.Random(seed).shuffle(ordered)
    a, b = int(len(ordered) * .6), int(len(ordered) * .8)
    return {"CALIBRATION": ordered[:a], "VALIDATION": ordered[a:b], "HOLDOUT": ordered[b:]}


def _admitted(row: dict[str, Any], config: dict[str, object]) -> bool:
    samples = int(row.get("probability_sample_size", 0))
    raw = row.get("p_win_raw")
    if raw is None:
        # Backward-compatible offline fixtures may carry already-computed EV.
        return (
            float(row.get("expected_ev_r", -1e9)) >= float(config["min_positive_ev_r"])
            and float(row.get("ev_reserve", -1e9)) >= float(config["min_ev_reserve_r"])
            and float(row.get("net_edge_bps", -1e9)) >= float(config["min_net_edge_bps"])
            and samples >= int(config["bucket_min_sample"])
            and float(row.get("stop_distance_bps", 1e9)) <= float(config["stop_max_bps"])
            and float(row.get("target_distance_bps", -1e9)) >= float(config["target_min_bps"])
            and int(row.get("causal_reset_conditions", 0)) >= int(config["causal_reset_min_conditions"])
            and int(row.get("one_min_confirmation_count", 0)) >= int(config["entry_refinement_1m_confirmation_count"])
        )
    target = float(row.get("target_distance_bps") or 0)
    stop = float(row.get("stop_distance_bps") or 0)
    base_cost = float(row.get("effective_total_cost_bps") or 0)
    adjusted_cost = max(0.0, base_cost
        - float(row.get("adverse_fill_reserve_bps") or 0)
        - 2 * float(row.get("entry_slippage_bps") or 0)
        + float(config["adverse_fill_reserve_bps"])
        + 2 * float(config["entry_slippage_bps"]))
    if min(target - adjusted_cost, stop + adjusted_cost) <= 0:
        return False
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
    return (
        decision.admitted
        and target - adjusted_cost >= float(config["min_net_edge_bps"])
        and stop <= float(config["stop_max_bps"])
        and target >= float(config["target_min_bps"])
        and int(row.get("causal_reset_conditions", 0)) >= int(config["causal_reset_min_conditions"])
        and int(row.get("one_min_confirmation_count", 0)) >= int(config["entry_refinement_1m_confirmation_count"])
    )


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
        "status": "UNREPLAYABLE", "soft": False, "hard": False,
        "exit": False, "break_even": False, "seconds_saved": 0.0,
        "blocked_candidates": None, "unblocked_candidates": None,
    }
    if not isinstance(observations, list) or not observations:
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
        state["status"] = "INSUFFICIENT_DATA"
        return row, state
    for observation in ordered:
        inputs = _historical_input(row, observation, extension_count=extension_count)
        if inputs is None:
            state["status"] = "INSUFFICIENT_DATA"
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
        state["status"] = "INSUFFICIENT_DATA"
        return row, state
    state["status"] = "REPLAYED"
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
    }
    return result


def _dataset_options(
    search: dict[str, Any], *, max_rows: int | None = None,
    from_value: str | None = None, to_value: str | None = None,
) -> DatasetOptions:
    raw = search.get("dataset", {})
    if isinstance(raw, str):
        source, profile, closed_only = raw, "trade-5m-v2", True
        configured_max = DEFAULT_MAX_ROWS
        configured_from = configured_to = None
    elif isinstance(raw, dict):
        source = str(raw.get("source", DATASET_SOURCE))
        profile = str(raw.get("profile", "trade-5m-v2"))
        closed_only = raw.get("closed_only", True)
        configured_max = raw.get("max_rows", DEFAULT_MAX_ROWS)
        configured_from, configured_to = raw.get("from"), raw.get("to")
    else:
        raise SweepExpectedError("DATASET_CONFIG_INVALID")
    if profile != "trade-5m-v2" or closed_only is not True:
        raise SweepExpectedError("DATASET_CONFIG_INVALID")
    try:
        maximum = int(max_rows if max_rows is not None else configured_max)
    except (TypeError, ValueError):
        raise SweepExpectedError("MAX_ROWS_OUT_OF_RANGE") from None
    if not 1 <= maximum <= DEFAULT_MAX_ROWS:
        raise SweepExpectedError("MAX_ROWS_OUT_OF_RANGE")
    start = _parse_utc(from_value if from_value is not None else configured_from)
    end = _parse_utc(to_value if to_value is not None else configured_to)
    if start is not None and end is not None and start >= end:
        raise SweepExpectedError("INVALID_DATE_RANGE")
    return DatasetOptions(source, profile, True, maximum, start, end)


def _validate_search(search: object) -> dict[str, Any]:
    if not isinstance(search, dict):
        raise SweepExpectedError("SEARCH_SPACE_INVALID")
    space = search.get("search_space")
    if (
        search.get("schema_version") != 2
        or not isinstance(space, dict)
        or "risk_per_trade" in space
        or not TIME_STOP_SEARCH_FIELDS.issubset(space)
        or any(not isinstance(values, list) or not values for values in space.values())
    ):
        raise SweepExpectedError("SEARCH_SPACE_INVALID")
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
    identifier = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not identifier or any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for character in identifier):
        raise SweepExpectedError("RUN_ID_INVALID")
    root = Path(str(search.get("output_root", "artifacts/scalping_v2_parameter_sweep")))
    if not root.is_absolute():
        root = PROJECT_ROOT / root
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


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
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _stream_json_array(source: Path, target: Path, *, rejected_only: bool = False) -> None:
    with source.open(encoding="utf-8") as incoming, target.open("w", encoding="utf-8") as outgoing:
        outgoing.write("[\n")
        first = True
        for line in incoming:
            item = json.loads(line)
            if rejected_only and item["result_status"] == "ACCEPTED":
                continue
            if not first:
                outgoing.write(",\n")
            outgoing.write(json.dumps(item, indent=2, sort_keys=True))
            first = False
        outgoing.write("\n]\n")


def _evaluate_config(
    params: dict[str, object], splits: Mapping[str, list[dict[str, Any]]],
    minimums: Mapping[str, int], *, index: int, stage: str,
) -> tuple[dict[str, Any], bool, str | None]:
    item: dict[str, Any] = {
        "result_index": index, "stage": stage, "parameters": params,
        "config_hash": _config_hash(params),
    }
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
    admitted_cal = [row for row in splits["CALIBRATION"] if _admitted(row, params)]
    item["calibration"] = _time_stop_metrics(
        admitted_cal, params, config_hash=item["config_hash"],
    )
    if len(admitted_cal) < int(minimums["calibration"]):
        reason = "ALL_TRADES_FILTERED" if not admitted_cal else "CALIBRATION_INSUFFICIENT_SAMPLE"
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
    admitted_validation = [row for row in splits["VALIDATION"] if _admitted(row, params)]
    item["validation"] = _time_stop_metrics(
        admitted_validation, params, config_hash=item["config_hash"],
    )
    statuses["validation"] = (
        "PASS" if len(admitted_validation) >= int(minimums["validation"])
        else "INSUFFICIENT_SAMPLE"
    )
    # Holdout is evaluated only after search metrics and never feeds stage/ranking.
    admitted_holdout = [row for row in splits["HOLDOUT"] if _admitted(row, params)]
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
    database_path = output / ".search-aggregate.sqlite3"
    connection = sqlite3.connect(database_path)
    connection.execute(
        "CREATE TABLE points(hash TEXT PRIMARY KEY, expectancy REAL, drawdown REAL, trades INTEGER)"
    )
    with (output / "RESULTS.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            if item["result_status"] != "ACCEPTED":
                continue
            metrics = item["validation"]
            connection.execute("INSERT INTO points VALUES (?,?,?,?)", (
                item["config_hash"], metrics["net_expectancy_per_trade"] or -1e99,
                metrics["max_drawdown"] or 0.0, metrics["trade_count"] or 0,
            ))
    connection.commit()
    top_hashes = [row[0] for row in connection.execute(
        "SELECT hash FROM points ORDER BY expectancy DESC, drawdown ASC, trades DESC LIMIT 10"
    )]
    frontier = [row[0] for row in connection.execute(
        "SELECT p.hash FROM points p WHERE NOT EXISTS (SELECT 1 FROM points o WHERE "
        "o.hash <> p.hash AND o.expectancy >= p.expectancy AND o.drawdown <= p.drawdown "
        "AND o.trades >= p.trades AND (o.expectancy > p.expectancy OR o.drawdown < p.drawdown OR o.trades > p.trades))"
    )]
    connection.close()
    database_path.unlink(missing_ok=True)
    selected: dict[str, dict[str, Any]] = {}
    with (output / "RESULTS.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            if item["config_hash"] in top_hashes:
                selected[item["config_hash"]] = item
    return {
        "ranked_without_holdout": [selected[value] for value in top_hashes],
        "pareto_frontier": frontier, "holdout_used_for_search": False,
    }


def run(
    search_path: Path, *, run_id: str | None = None, max_configs: int | None = None,
    max_rows: int | None = None, from_value: str | None = None,
    to_value: str | None = None, database_url: str | None = None,
    preflight_only: bool = False, verbose: bool = False, resume: bool = False,
    stop_after_batches: int | None = None,
) -> Path:
    try:
        search = _validate_search(yaml.safe_load(search_path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        raise SweepExpectedError("CONFIG_FILE_NOT_FOUND") from None
    except yaml.YAMLError:
        raise SweepExpectedError("SEARCH_SPACE_INVALID") from None
    space = search["search_space"]
    options = _dataset_options(search, max_rows=max_rows, from_value=from_value, to_value=to_value)
    identifier, output = _prepare_output(search, run_id, resume=resume)
    database: ReadOnlyResearchDatabase | None = None
    binding_source, session_mode, schema_head = "NOT_REQUIRED_OFFLINE_JSON", "NOT_APPLICABLE", "NOT_APPLICABLE"
    write_rejections: dict[str, str] = {}
    try:
        if options.source in {DATASET_SOURCE, LEGACY_DATASET_SOURCE}:
            binding = resolve_database_binding(explicit_url=database_url)
            binding_source = binding.source
            database = ReadOnlyResearchDatabase(binding)
            session_mode, schema_head, _tables, write_rejections = _preflight_database(database)
        rows = _load_rows(options, database)
    except SweepExpectedError as error:
        _write_preflight(output / "PREFLIGHT.json", {
            "PARAMETER_SWEEP_PREFLIGHT": "FAILED", "REASON": error.reason, "SECRET_OUTPUT": 0,
        })
        raise
    finally:
        if database is not None:
            database.dispose()
    if not rows:
        _write_preflight(output / "PREFLIGHT.json", {
            "PARAMETER_SWEEP_PREFLIGHT": "FAILED", "REASON": "DATASET_EMPTY", "SECRET_OUTPUT": 0,
        })
        raise SweepExpectedError("DATASET_EMPTY")
    splits = _split(rows, int(search["seed"]))
    plan = ParameterSweepSearchPlanner().plan(
        dataset_rows=len(rows), space=space, search=search.get("search", {}),
        max_configs_override=max_configs, validation_rows=len(splits["VALIDATION"]),
        holdout_rows=len(splits["HOLDOUT"]), available_replay_rows=sum(
            isinstance(row.get("time_stop_observations"), list)
            and bool(row.get("time_stop_observations")) for row in rows
        ),
    )
    git_commit, dataset_fingerprint = _git_commit(), _config_hash(rows)
    search_space_hash = _config_hash(space)
    checkpoint_path = output / "CHECKPOINT.json"
    checkpoint = {
        "run_id": identifier, "git_commit": git_commit,
        "config_hash": TRADE_PARAMETERS.config_hash,
        "search_space_hash": search_space_hash,
        "dataset_fingerprint": dataset_fingerprint,
        "strategy": plan.selected_strategy, "seed": plan.seed, "stage": "NOT_STARTED",
        "evaluated_count": 0, "accepted_count": 0, "rejected_count": 0,
        "pruned_count": 0, "early_reject_count": 0, "failed_count": 0,
        "last_durable_result_index": -1, "last_candidate_offset": -1,
        "checkpoint_count": 0, "early_reject_reasons": {}, "completed": False,
    }
    if resume:
        try:
            existing = _json(checkpoint_path)
        except (FileNotFoundError, json.JSONDecodeError):
            raise SweepExpectedError("RESUME_CHECKPOINT_NOT_AVAILABLE") from None
        immutable = ("run_id", "git_commit", "config_hash", "search_space_hash", "dataset_fingerprint", "strategy", "seed")
        if any(existing.get(key) != checkpoint[key] for key in immutable):
            raise SweepExpectedError("RESUME_FINGERPRINT_MISMATCH")
        checkpoint = existing
    preflight = {
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
        "SCHEMA_HEAD": schema_head, "PROFILE": options.profile, "ROWS_AVAILABLE": len(rows),
        "DATASET_ROWS": len(rows), "RAW_SEARCH_SPACE_SIZE": plan.raw_search_space_size,
        "SEARCH_STRATEGY": plan.selected_strategy, "EXHAUSTIVE": "YES" if plan.selected_strategy == "EXHAUSTIVE_LAZY" else "NO",
        "MAX_EVALUATED_CONFIGS": plan.evaluation_budget, "CONFIGURATIONS_PLANNED": plan.evaluation_budget,
        "BATCH_SIZE": plan.batch_size, "SEED": plan.seed, "MEMORY_PLAN": "SAFE",
        "ESTIMATED_ACTIVE_BATCH_MEMORY_MB": plan.estimated_active_batch_memory_mb,
        "STATISTICAL_SEARCH_WARNING": plan.statistical_warning,
        "PROMOTION_ELIGIBLE": "YES" if plan.promotion_eligible else "NO",
        "OUTPUT_DIR": _display_path(output), "SECRET_OUTPUT": 0,
    }
    _write_preflight(output / "PREFLIGHT.json", preflight)
    _atomic_json(output / "SEARCH_PLAN.json", plan.safe_dict())
    _print_preflight(preflight)
    for key in ("RAW_SEARCH_SPACE_SIZE", "SEARCH_STRATEGY", "EXHAUSTIVE", "MAX_EVALUATED_CONFIGS", "BATCH_SIZE", "SEED", "STATISTICAL_SEARCH_WARNING", "PROMOTION_ELIGIBLE", "MEMORY_PLAN"):
        print(f"{key} = {preflight[key]}")
    if preflight_only:
        _atomic_json(checkpoint_path, checkpoint)
        return output
    run_config = {
        "schema_version": SCHEMA_VERSION, "seed": search["seed"], "search": plan.safe_dict(),
        "dataset": {"source": options.source, "profile": options.profile, "closed_only": True, "max_rows": options.maximum_rows},
        "dataset_period": {"from_ms": min(row.get("opened_at_ms") for row in rows), "to_ms": max(row.get("closed_at_ms") for row in rows)},
        "sample_sizes": {key: len(value) for key, value in splits.items()},
        "source_data_provenance": dataset_fingerprint, "authoritative_trade_parameters": str(CONFIG_PATH),
        "baseline_config_hash": TRADE_PARAMETERS.config_hash, "search_space_hash": search_space_hash,
        "time_stop_policy_schema": "StalePositionPolicyParameters",
        "time_stop_evaluator": "app.engine_paper.stale_position_shadow.evaluate_stale_position_shadow",
        "search_space_config": str(search_path), "git_commit": git_commit,
        "database_binding": binding_source, "database_session": "READ_ONLY" if session_mode == "ON" else session_mode,
        "schema_head": schema_head, "production_mutations": 0, "production_config_writes": 0,
        "approvals_created": 0, "commands_created": 0, "positions_created": 0, "binance_order_api_calls": 0,
    }
    if not resume:
        (output / "RUN_CONFIG.yaml").write_text(yaml.safe_dump(run_config, sort_keys=False), encoding="utf-8")
    jsonl = output / "RESULTS.jsonl"
    csv_path = output / "RESULTS.csv"
    csv_fields = ["result_index", "config_hash", "stage", "result_status", "validation_expectancy", "validation_drawdown", "validation_trades", "parameters_json"]
    csv_new = not csv_path.exists()
    batch_active = 0
    batches_this_call = 0
    with jsonl.open("a", encoding="utf-8", buffering=1) as json_handle, csv_path.open("a", newline="", encoding="utf-8", buffering=1) as csv_handle:
        writer = csv.DictWriter(csv_handle, fieldnames=csv_fields)
        if csv_new:
            writer.writeheader()
        for candidate_offset, raw_index in enumerate(_candidate_indices(plan)):
            if candidate_offset <= int(checkpoint["last_candidate_offset"]):
                continue
            if int(checkpoint["evaluated_count"]) >= plan.evaluation_budget:
                break
            stage = _stage_for(plan, int(checkpoint["evaluated_count"]))
            item, consumed_budget, early_reason = _evaluate_config(
                _config_from_index(space, raw_index), splits, search["minimum_samples"],
                index=int(checkpoint["last_durable_result_index"]) + 1, stage=stage,
            )
            json_handle.write(json.dumps(item, sort_keys=True) + "\n")
            validation = item["validation"]
            writer.writerow({
                "result_index": item["result_index"], "config_hash": item["config_hash"],
                "stage": stage, "result_status": item["result_status"],
                "validation_expectancy": validation.get("net_expectancy_per_trade"),
                "validation_drawdown": validation.get("max_drawdown"),
                "validation_trades": validation.get("trade_count"),
                "parameters_json": json.dumps(item["parameters"], sort_keys=True),
            })
            json_handle.flush(); csv_handle.flush(); os.fsync(json_handle.fileno()); os.fsync(csv_handle.fileno())
            checkpoint["last_candidate_offset"] = candidate_offset
            checkpoint["last_durable_result_index"] = item["result_index"]
            checkpoint["stage"] = stage
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
            _atomic_json(checkpoint_path, checkpoint)
            batch_active += 1
            if batch_active >= plan.batch_size:
                batches_this_call += 1
                batch_active = 0
                if stop_after_batches is not None and batches_this_call >= stop_after_batches:
                    return output
    checkpoint["completed"] = int(checkpoint["evaluated_count"]) == plan.evaluation_budget
    _atomic_json(checkpoint_path, checkpoint)
    _stream_json_array(jsonl, output / "RESULTS.json")
    _stream_json_array(jsonl, output / "REJECTED_CONFIGS.json", rejected_only=True)
    top = _aggregate_results(output)
    _atomic_json(output / "TOP_CONFIGS.json", top)
    configs_per_observation = int(checkpoint["evaluated_count"]) / len(rows)
    report = f"""# Scalping v2 parameter sweep

## SEARCH PLANNING

- Raw search-space size: {plan.raw_search_space_size}
- Selected strategy: `{plan.selected_strategy}`
- Seed: {plan.seed}
- Evaluation budget: {plan.evaluation_budget}
- Staged plan: `{json.dumps(plan.staged_search_plan)}`
- Holdout used for search/refinement/ranking: `NO`

## MEMORY SAFETY

- Memory plan: `SAFE`
- Lazy config generation; raw space materialized: `NO`
- Batch size: {plan.batch_size}; estimated active batch memory: {plan.estimated_active_batch_memory_mb} MB
- Peak active batch size: {min(plan.batch_size, int(checkpoint['last_durable_result_index']) + 1)}
- Base rows are shared; replay uses bounded split-local overlays, not dataset copies.
- Incremental JSONL/CSV and disk-backed TOP/Pareto aggregation are enabled.

## STATISTICAL SUFFICIENCY

- Dataset source/profile/rows: `{preflight['DATASET_SOURCE']}` / `{options.profile}` / {len(rows)}
- Configs per observation: {configs_per_observation:.6f}
- Statistical warning: `{plan.statistical_warning}`
- Promotion eligible: `{'YES' if plan.promotion_eligible else 'NO'}`
- No production recommendation is emitted when promotion eligibility is `NO`.

## EXECUTION PROGRESS

- Actual evaluated configs: {checkpoint['evaluated_count']}
- Pruned invalid configs: {checkpoint['pruned_count']}
- Early rejected configs: {checkpoint['early_reject_count']}
- Early rejection reasons: `{json.dumps(checkpoint.get('early_reject_reasons', {}), sort_keys=True)}`
- Completed durable rows: {int(checkpoint['last_durable_result_index']) + 1}
- Accepted/rejected/failed: {checkpoint['accepted_count']}/{checkpoint['rejected_count']}/{checkpoint['failed_count']}
- Checkpoint count: {checkpoint['checkpoint_count']}; resume used: `{'YES' if resume else 'NO'}`

## TIME-STOP / STALE-POSITION ANALYSIS

- Runtime and replay share `StalePositionPolicyParameters` and `evaluate_stale_position_shadow`.
- Current commissions never replace missing historical causal cost evidence.
- Holdout is not ranked and does not influence search stages.

## SAFETY

- Database session: `{'READ_ONLY' if session_mode == 'ON' else session_mode}`.
- Production mutations/config writes/approvals/commands/positions: `0`.
- Binance order calls: `0`; LIVE remains disabled and untouched.
- Full results are streamed in `RESULTS.jsonl`, `RESULTS.csv`, and `RESULTS.json`.
"""
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    print(f"CONFIGURATIONS_EVALUATED = {checkpoint['evaluated_count']}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zero-setup, read-only Scalping v2 parameter sweep",
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-configs", type=int)
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--from", dest="from_value")
    parser.add_argument("--to", dest="to_value")
    parser.add_argument("--database-url", help="Explicit dev/test/admin override only")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    try:
        output = run(
            args.config, run_id=args.run_id, max_configs=args.max_configs,
            max_rows=args.max_rows, from_value=args.from_value,
            to_value=args.to_value, database_url=args.database_url,
            preflight_only=args.preflight_only, verbose=args.verbose,
            resume=args.resume,
        )
    except SweepExpectedError as error:
        print("PARAMETER_SWEEP_PREFLIGHT = FAILED")
        print(f"REASON = {error.reason}")
        raise SystemExit(2) from None
    report = output / "REPORT.md"
    print(report if report.exists() else output / "PREFLIGHT.json")


if __name__ == "__main__":
    main()
