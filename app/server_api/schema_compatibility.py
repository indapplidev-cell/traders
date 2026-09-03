"""Fail-closed dual-schema capability detection for the Readonly runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String, inspect, text
from sqlalchemy.engine import Connection

from app.db.paper_models import (
    PaperAccountBaselineRecord, PaperExitDecisionRecord,
    PaperExecutionCommandRecord,
    PaperExitEvaluationCursorRecord, PaperFillRecord, PaperJournalEntryRecord,
    PaperOrderRecord, PaperPlanExecutionOutcomeRecord, PaperPositionRecord,
    TradingUniverseRuntimeStateRecord,
)
from app.engine_market_data.continuous_sync_state import MarketDataSyncState
from app.engine_market_data.db.candle_tables import CANDLE_MODELS
from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun


READONLY_SCHEMA_0016: Final = "0016_control_mobile_device_security"
READONLY_SCHEMA_0017: Final = "0017_parallel_trade_profiles"
READONLY_SCHEMA_0018: Final = "0018_promote_5m_production_search"
READONLY_SCHEMA_0019: Final = "0019_first_class_15m_domain"
READONLY_SCHEMA_0020: Final = "0020_paper_plan_execution_outcomes"
READONLY_SCHEMA_0021: Final = "0021_independent_scalping_profile_v2"
READONLY_SCHEMA_0022: Final = "0022_scalping_v2_paper_simulation_policy"
READONLY_SCHEMA_0023: Final = "0023_scalping_v2_journal_causality"
PAPER_SCHEMA_MINIMUM: Final = "0015_trading_universe_activation"
PAPER_SCHEMA_MAXIMUM: Final = READONLY_SCHEMA_0023
PAPER_SCHEMA_COMPATIBILITY_LABEL: Final = f"{PAPER_SCHEMA_MINIMUM}|{PAPER_SCHEMA_MAXIMUM}"


class ReadonlySchemaCapability(StrEnum):
    BASE_MARKET_READONLY = "BASE_MARKET_READONLY"
    ANALYSIS_READONLY = "ANALYSIS_READONLY"
    SETUP_READONLY = "SETUP_READONLY"
    PAPER_READONLY = "PAPER_READONLY"
    I18N_READONLY = "I18N_READONLY"
    PARALLEL_TRADE_PROFILES = "PARALLEL_TRADE_PROFILES"
    PAPER_PLAN_EXECUTION_OUTCOMES = "PAPER_PLAN_EXECUTION_OUTCOMES"


BASE_READONLY_CAPABILITIES: Final = frozenset({
    ReadonlySchemaCapability.BASE_MARKET_READONLY,
    ReadonlySchemaCapability.ANALYSIS_READONLY,
    ReadonlySchemaCapability.SETUP_READONLY,
    ReadonlySchemaCapability.PAPER_READONLY,
    ReadonlySchemaCapability.I18N_READONLY,
})
PAPER_REQUIRED_MODELS: Final = (
    PaperAccountBaselineRecord, PaperExecutionCommandRecord,
    PaperPositionRecord, PaperOrderRecord,
    PaperFillRecord, PaperExitEvaluationCursorRecord, PaperExitDecisionRecord,
    PaperJournalEntryRecord,
)
BASE_REQUIRED_MODELS: Final = (
    *tuple(CANDLE_MODELS.values()), MarketDataSyncState, OnlinePipelineRun,
    OnlinePipelineResultRow, TradingUniverseRuntimeStateRecord, *PAPER_REQUIRED_MODELS,
)
PROFILE_COLUMNS: Final = {
    "online_pipeline_runs": ("trade_profile_id", "profile_mode"),
    "online_pipeline_results": ("trade_profile_id", "profile_mode"),
}
PAPER_REQUIRED_SCHEMA_OBJECTS: Final = (
    "alembic_version", *(model.__table__.name for model in PAPER_REQUIRED_MODELS),
)


@dataclass(frozen=True, slots=True)
class PaperSchemaContractResult:
    compatible: bool
    issues: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReadonlySchemaCapabilityResult:
    compatible: bool
    revision: str | None
    capabilities: frozenset[ReadonlySchemaCapability] = frozenset()
    issues: tuple[str, ...] = ()

    def has(self, capability: ReadonlySchemaCapability) -> bool:
        return capability in self.capabilities


class ReadonlySchemaCapabilityBridge:
    """Startup-activated immutable snapshot shared by all query adapters."""

    def __init__(self) -> None:
        self._result: ReadonlySchemaCapabilityResult | None = None

    def activate(self, result: ReadonlySchemaCapabilityResult) -> None:
        if not result.compatible:
            raise RuntimeError("READONLY_SCHEMA_CAPABILITY_CHECK_FAILED:" + ",".join(result.issues))
        if self._result is not None and self._result != result:
            raise RuntimeError("READONLY_SCHEMA_CAPABILITY_CHANGED_DURING_STARTUP")
        self._result = result

    def snapshot(self) -> ReadonlySchemaCapabilityResult:
        if self._result is None:
            raise RuntimeError("READONLY_SCHEMA_CAPABILITY_NOT_ACTIVATED")
        return self._result


def revision_is_supported(revisions: tuple[str, ...]) -> bool:
    """Retain the legacy PAPER contract; runtime startup uses stricter capabilities."""
    return len(revisions) == 1 and revisions[0] in {
        PAPER_SCHEMA_MINIMUM, READONLY_SCHEMA_0016, READONLY_SCHEMA_0017,
        READONLY_SCHEMA_0018, READONLY_SCHEMA_0019, READONLY_SCHEMA_0020,
        READONLY_SCHEMA_0021, READONLY_SCHEMA_0022, READONLY_SCHEMA_0023,
    }


def _type_signature(value: object) -> tuple[object, ...]:
    if isinstance(value, String): return ("string", value.length)
    if isinstance(value, Numeric): return ("numeric", value.precision, value.scale)
    if isinstance(value, DateTime): return ("datetime", bool(value.timezone))
    if isinstance(value, BigInteger): return ("bigint",)
    if isinstance(value, Integer): return ("integer",)
    if isinstance(value, Boolean): return ("boolean",)
    return (type(value).__name__.casefold(),)


def _validate_model(inspector, tables: set[str], model, issues: list[str], *, excluded=frozenset()) -> None:
    table = model.__table__
    if table.name not in tables:
        issues.append(f"MISSING_TABLE:{table.name}")
        return
    actual_columns = {str(col["name"]): col for col in inspector.get_columns(table.name, schema="public")}
    for expected in table.columns:
        if expected.name in excluded: continue
        actual = actual_columns.get(expected.name)
        if actual is None:
            issues.append(f"MISSING_COLUMN:{table.name}.{expected.name}")
            continue
        if _type_signature(actual["type"]) != _type_signature(expected.type):
            issues.append(f"INCOMPATIBLE_TYPE:{table.name}.{expected.name}")
        if bool(actual["nullable"]) != bool(expected.nullable):
            issues.append(f"INCOMPATIBLE_NULLABILITY:{table.name}.{expected.name}")
    actual_pk = tuple(inspector.get_pk_constraint(table.name, schema="public").get("constrained_columns") or ())
    expected_pk = tuple(column.name for column in table.primary_key.columns)
    if actual_pk != expected_pk: issues.append(f"INCOMPATIBLE_PRIMARY_KEY:{table.name}")


def inspect_readonly_schema_capabilities(connection: Connection) -> ReadonlySchemaCapabilityResult:
    """Validate a supported exact schema shape and derive capabilities from evidence."""
    issues: list[str] = []
    revision: str | None = None
    try:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names(schema="public"))
        if "alembic_version" not in tables:
            return ReadonlySchemaCapabilityResult(False, None, issues=("MISSING_TABLE:alembic_version",))
        revisions = tuple(str(value) for value in connection.execute(
            text("SELECT version_num FROM alembic_version ORDER BY version_num")
        ).scalars())
        if len(revisions) != 1:
            return ReadonlySchemaCapabilityResult(False, None, issues=("AMBIGUOUS_ALEMBIC_STATE",))
        revision = revisions[0]
        if revision not in {
            READONLY_SCHEMA_0016, READONLY_SCHEMA_0017,
            READONLY_SCHEMA_0018, READONLY_SCHEMA_0019, READONLY_SCHEMA_0020,
            READONLY_SCHEMA_0021, READONLY_SCHEMA_0022, READONLY_SCHEMA_0023,
        }:
            return ReadonlySchemaCapabilityResult(False, revision, issues=(f"UNSUPPORTED_REVISION:{revision}",))
        for model in BASE_REQUIRED_MODELS:
            _validate_model(inspector, tables, model, issues,
                            excluded=frozenset(PROFILE_COLUMNS.get(model.__table__.name, ())))
        if revision in {
            READONLY_SCHEMA_0020, READONLY_SCHEMA_0021, READONLY_SCHEMA_0022,
            READONLY_SCHEMA_0023,
        }:
            _validate_model(
                inspector, tables, PaperPlanExecutionOutcomeRecord, issues
            )
        actual_profiles = {}
        for table_name, names in PROFILE_COLUMNS.items():
            columns = {str(col["name"]): col for col in inspector.get_columns(table_name, schema="public")}
            actual_profiles[table_name] = {name: columns[name] for name in names if name in columns}
        present_count = sum(len(values) for values in actual_profiles.values())
        expected_count = sum(len(values) for values in PROFILE_COLUMNS.values())
        if revision == READONLY_SCHEMA_0016:
            if present_count: issues.append("AMBIGUOUS_0016_PROFILE_COLUMNS_PRESENT")
        else:
            if present_count != expected_count: issues.append("PARTIAL_0017_PROFILE_COLUMNS")
            for model in (OnlinePipelineRun, OnlinePipelineResultRow):
                table = model.__table__
                for name in PROFILE_COLUMNS[table.name]:
                    actual = actual_profiles[table.name].get(name)
                    expected = table.columns[name]
                    if actual is None: continue
                    if _type_signature(actual["type"]) != _type_signature(expected.type):
                        issues.append(f"INCOMPATIBLE_TYPE:{table.name}.{name}")
                    if bool(actual["nullable"]) != bool(expected.nullable):
                        issues.append(f"INCOMPATIBLE_NULLABILITY:{table.name}.{name}")
            unique_names = {str(item.get("name")) for item in inspector.get_unique_constraints("online_pipeline_runs", schema="public")}
            index_names = {str(item.get("name")) for item in inspector.get_indexes("online_pipeline_runs", schema="public")}
            check_names = {str(item.get("name")) for item in inspector.get_check_constraints("online_pipeline_runs", schema="public")}
            if "uq_online_pipeline_profile_window" not in unique_names: issues.append("MISSING_PROFILE_UNIQUE_CONSTRAINT")
            if "ix_online_pipeline_profile_boundary" not in index_names: issues.append("MISSING_PROFILE_BOUNDARY_INDEX")
            if "ck_online_pipeline_trade_profile" not in check_names: issues.append("MISSING_PROFILE_CHECK_CONSTRAINT")
    except Exception:
        return ReadonlySchemaCapabilityResult(False, revision, issues=("SCHEMA_METADATA_UNREADABLE",))
    capabilities = BASE_READONLY_CAPABILITIES
    if revision in {
        READONLY_SCHEMA_0017, READONLY_SCHEMA_0018, READONLY_SCHEMA_0019,
        READONLY_SCHEMA_0020, READONLY_SCHEMA_0021, READONLY_SCHEMA_0022,
        READONLY_SCHEMA_0023,
    } and not issues:
        capabilities = capabilities | {ReadonlySchemaCapability.PARALLEL_TRADE_PROFILES}
    if revision in {
        READONLY_SCHEMA_0020, READONLY_SCHEMA_0021, READONLY_SCHEMA_0022,
        READONLY_SCHEMA_0023,
    } and not issues:
        capabilities = capabilities | {
            ReadonlySchemaCapability.PAPER_PLAN_EXECUTION_OUTCOMES
        }
    return ReadonlySchemaCapabilityResult(not issues, revision,
        frozenset(capabilities) if not issues else frozenset(), tuple(issues))


def inspect_required_paper_schema(connection: Connection) -> PaperSchemaContractResult:
    issues: list[str] = []
    try:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names(schema="public"))
        for model in PAPER_REQUIRED_MODELS: _validate_model(inspector, tables, model, issues)
    except Exception:
        return PaperSchemaContractResult(False, ("SCHEMA_METADATA_UNREADABLE",))
    return PaperSchemaContractResult(not issues, tuple(issues))


__all__ = [
    "BASE_READONLY_CAPABILITIES", "PAPER_REQUIRED_SCHEMA_OBJECTS",
    "PAPER_SCHEMA_COMPATIBILITY_LABEL", "PAPER_SCHEMA_MAXIMUM", "PAPER_SCHEMA_MINIMUM",
    "READONLY_SCHEMA_0018", "READONLY_SCHEMA_0019", "READONLY_SCHEMA_0020", "READONLY_SCHEMA_0021",
    "PaperSchemaContractResult", "ReadonlySchemaCapability",
    "ReadonlySchemaCapabilityBridge", "ReadonlySchemaCapabilityResult",
    "inspect_readonly_schema_capabilities", "inspect_required_paper_schema",
    "revision_is_supported",
]
