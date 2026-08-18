"""Fail-closed schema compatibility for the Readonly PAPER projection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, String, inspect
from sqlalchemy.engine import Connection

from app.db.paper_models import (
    PaperAccountBaselineRecord,
    PaperExitDecisionRecord,
    PaperExitEvaluationCursorRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)


PAPER_SCHEMA_MINIMUM: Final = "0015_trading_universe_activation"
PAPER_SCHEMA_MAXIMUM: Final = "0016_control_mobile_device_security"
PAPER_SCHEMA_COMPATIBILITY_LABEL: Final = (
    f"{PAPER_SCHEMA_MINIMUM}..{PAPER_SCHEMA_MAXIMUM}"
)

# These are the relations actually queried by PaperReadonlyReportingService.
# Extra tables and extra columns are intentionally compatible.
PAPER_REQUIRED_MODELS: Final = (
    PaperAccountBaselineRecord,
    PaperPositionRecord,
    PaperOrderRecord,
    PaperFillRecord,
    PaperExitEvaluationCursorRecord,
    PaperExitDecisionRecord,
    PaperJournalEntryRecord,
)
PAPER_REQUIRED_SCHEMA_OBJECTS: Final = (
    "alembic_version",
    *(model.__table__.name for model in PAPER_REQUIRED_MODELS),
)


@dataclass(frozen=True, slots=True)
class PaperSchemaContractResult:
    compatible: bool
    issues: tuple[str, ...] = ()


def _lineage(revision: str, scripts: ScriptDirectory) -> tuple[str, ...]:
    values: list[str] = []
    current = scripts.get_revision(revision)
    while current is not None:
        values.append(current.revision)
        parent = current.down_revision
        if parent is None:
            break
        if not isinstance(parent, str):
            raise ValueError("AMBIGUOUS_ALEMBIC_LINEAGE")
        current = scripts.get_revision(parent)
    return tuple(values)


def revision_is_supported(revisions: tuple[str, ...]) -> bool:
    """Accept one known linear revision within the explicit compatibility range."""
    if len(revisions) != 1 or not revisions[0]:
        return False
    try:
        roots = (Path.cwd(), Path(__file__).resolve().parents[2])
        root = next(
            candidate
            for candidate in roots
            if (candidate / "alembic.ini").is_file()
            and (candidate / "alembic").is_dir()
        )
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "alembic"))
        scripts = ScriptDirectory.from_config(config)
        current = revisions[0]
        return (
            PAPER_SCHEMA_MINIMUM in _lineage(current, scripts)
            and current in _lineage(PAPER_SCHEMA_MAXIMUM, scripts)
        )
    except (OSError, KeyError, StopIteration, TypeError, ValueError, CommandError):
        return False


def _type_signature(value: object) -> tuple[object, ...]:
    if isinstance(value, String):
        return ("string", value.length)
    if isinstance(value, Numeric):
        return ("numeric", value.precision, value.scale)
    if isinstance(value, DateTime):
        return ("datetime", bool(value.timezone))
    if isinstance(value, BigInteger):
        return ("bigint",)
    if isinstance(value, Integer):
        return ("integer",)
    if isinstance(value, Boolean):
        return ("boolean",)
    return (type(value).__name__.casefold(),)


def inspect_required_paper_schema(connection: Connection) -> PaperSchemaContractResult:
    """Validate required tables, columns, types, nullability, and primary keys."""
    issues: list[str] = []
    try:
        inspector = inspect(connection)
        present_tables = set(inspector.get_table_names(schema="public"))
        for model in PAPER_REQUIRED_MODELS:
            table = model.__table__
            if table.name not in present_tables:
                issues.append(f"MISSING_TABLE:{table.name}")
                continue
            actual_columns = {
                str(column["name"]): column
                for column in inspector.get_columns(table.name, schema="public")
            }
            for expected in table.columns:
                actual = actual_columns.get(expected.name)
                if actual is None:
                    issues.append(f"MISSING_COLUMN:{table.name}.{expected.name}")
                    continue
                if _type_signature(actual["type"]) != _type_signature(expected.type):
                    issues.append(f"INCOMPATIBLE_TYPE:{table.name}.{expected.name}")
                if bool(actual["nullable"]) != bool(expected.nullable):
                    issues.append(f"INCOMPATIBLE_NULLABILITY:{table.name}.{expected.name}")
            actual_pk = tuple(
                inspector.get_pk_constraint(table.name, schema="public").get(
                    "constrained_columns"
                )
                or ()
            )
            expected_pk = tuple(column.name for column in table.primary_key.columns)
            if actual_pk != expected_pk:
                issues.append(f"INCOMPATIBLE_PRIMARY_KEY:{table.name}")
    except Exception:
        return PaperSchemaContractResult(False, ("SCHEMA_METADATA_UNREADABLE",))
    return PaperSchemaContractResult(not issues, tuple(issues))


__all__ = [
    "PAPER_REQUIRED_SCHEMA_OBJECTS",
    "PAPER_SCHEMA_COMPATIBILITY_LABEL",
    "PAPER_SCHEMA_MAXIMUM",
    "PAPER_SCHEMA_MINIMUM",
    "PaperSchemaContractResult",
    "inspect_required_paper_schema",
    "revision_is_supported",
]
