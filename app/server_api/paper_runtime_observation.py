"""Fail-closed production PAPER runtime observation for the Readonly API."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperOrderRecord,
    PaperPlanExecutionOutcomeRecord,
    PaperPositionRecord,
)

from app.engine_paper.production_approval import (
    PaperProductionApprovalReadiness,
    PaperProductionApprovalRequest,
    PaperProductionApprovalScope,
    PaperProductionApprovalSourceAdapter,
    SYMBOL_ALLOWLIST as APPROVAL_SYMBOLS,
)
from app.engine_market_data.continuous_sync_config import FRESHNESS_ALLOWANCE_MS
from app.engine_market_data.freshness_monitor import close_boundary_ms
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_paper.production_market_data import (
    SYMBOL_ALLOWLIST as MARKET_SYMBOLS,
    TIMEFRAME_ALLOWLIST,
)
from app.engine_paper.production_preparation import (
    IDENTITY_KEYS,
    PRODUCTION_PAPER_RUNTIME_ROLE,
    RUNTIME_GRANTS,
    PaperProductionAccountIdentityBinding,
)
from app.engine_safety.production_wal_archive import inspect_wal_continuity, wal_segment_identity
from app.server_api.schemas.paper import PaperControlStatus
from app.server_api.services.paper_reporting import PaperRuntimeObservation
from app.server_api.mapping.contract import utc_text
from app.engine_safety.production_control_root import resolve_production_control_root
from app.operator_control.runtime_health import read_paper_runtime_health


PRODUCTION_RUNTIME_ROOT: Final = Path("/run/traders-paper-runtime")
PRODUCTION_IDENTITY_ROOT: Final = Path("/run/traders-paper-identity")
PRODUCTION_RECOVERY_ROOT: Final = Path("/run/traders-recovery")
PRODUCTION_MARKET_HEALTH_ROOT: Final = Path("/run/traders-market-data-health")
RUNTIME_CONFIGURATION_NAME: Final = "paper-runtime.disabled.json"
IDENTITY_CONFIGURATION_NAME: Final = "paper-identity.json"
MINIMUM_PITR_WINDOW_SECONDS: Final = 86_400
MAX_JSON_BYTES: Final = 16 * 1024
MAX_MARKET_HEALTH_JSON_BYTES: Final = 256 * 1024
MAX_WAL_DAEMON_AGE_SECONDS: Final = 1_200
MAX_MARKET_HEALTH_AGE_SECONDS: Final = 180
_START_WAL = re.compile(
    r"^START WAL LOCATION: (?P<lsn>[0-9A-F]+/[0-9A-F]+) \(file (?P<file>[0-9A-F]{24})\)$",
    re.MULTILINE,
)
_START_TIMELINE = re.compile(r"^START TIMELINE: (?P<timeline>[0-9]+)$", re.MULTILINE)


def _json_object(path: Path, *, max_bytes: int = MAX_JSON_BYTES) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size > max_bytes:
        raise ValueError("PRODUCTION_OBSERVATION_ARTIFACT_INVALID")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("PRODUCTION_OBSERVATION_ARTIFACT_INVALID")
    return value


def load_production_identity(
    root: Path = PRODUCTION_IDENTITY_ROOT,
) -> PaperProductionAccountIdentityBinding:
    payload = _json_object(root / IDENTITY_CONFIGURATION_NAME)
    values = {key: payload.get(key) for key in IDENTITY_KEYS}
    if any(not isinstance(value, str) for value in values.values()):
        raise ValueError("PRODUCTION_IDENTITY_BINDING_INVALID")
    return PaperProductionAccountIdentityBinding.from_configuration(values)  # type: ignore[arg-type]


def _runtime_configuration_ready(root: Path) -> bool:
    try:
        payload = _json_object(root / RUNTIME_CONFIGURATION_NAME)
        return payload == {
            "auto_arm": False,
            "auto_start": False,
            "daemon_enabled": False,
            "dry_run": True,
            "live_enabled": False,
            "runtime_enabled": False,
            "scheduler_enabled": False,
            "state": "DEPLOYED_DISABLED",
        }
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def _runtime_principal_ready(session_factory: Callable[[], Session]) -> bool:
    try:
        with session_factory() as session, session.begin():
            role_exists = bool(session.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname=:role)"),
                {"role": PRODUCTION_PAPER_RUNTIME_ROLE},
            ).scalar_one())
            return role_exists and all(
                bool(session.execute(
                    text("SELECT has_table_privilege(:role,:relation,:operation)"),
                    {
                        "role": PRODUCTION_PAPER_RUNTIME_ROLE,
                        "relation": f"public.{grant.table}",
                        "operation": operation,
                    },
                ).scalar_one())
                for grant in RUNTIME_GRANTS
                for operation in grant.operations
            )
    except Exception:
        return False


def _market_data_readiness(
    root: Path,
    now: datetime,
) -> bool:
    """Validate the health artifact with the persisted adapter's grace semantics."""
    try:
        payload = _json_object(
            root / "latest_health.json", max_bytes=MAX_MARKET_HEALTH_JSON_BYTES,
        )
        generated = datetime.fromisoformat(str(payload["generated_at"]).replace("Z", "+00:00"))
        generated_ms = int(generated.timestamp() * 1000)
        snapshots = payload.get("snapshots")
        if (
            payload.get("overall_status") not in {"OK", "RECOVERING"}
            or payload.get("symbols") != list(MARKET_SYMBOLS)
            or payload.get("timeframes") != list(TIMEFRAME_ALLOWLIST)
            or not isinstance(snapshots, list)
            or len(snapshots) != len(MARKET_SYMBOLS) * len(TIMEFRAME_ALLOWLIST)
            or not 0 <= (now - generated.astimezone(timezone.utc)).total_seconds() <= MAX_MARKET_HEALTH_AGE_SECONDS
        ):
            return False
        expected = {(symbol, timeframe) for symbol in MARKET_SYMBOLS for timeframe in TIMEFRAME_ALLOWLIST}
        observed: set[tuple[str, str]] = set()
        for item in snapshots:
            if not isinstance(item, dict):
                return False
            timeframe = str(item.get("timeframe"))
            observed |= {(str(item.get("symbol")), timeframe)}
            stored = item.get("stored_open_time_ms")
            expected_open = item.get("expected_open_time_ms")
            base_safe = item.get("missing_count") == 0 and item.get("last_error") is None
            current = (
                item.get("status") == "OK"
                and item.get("freshness_lag_candles") == 0
                and stored == expected_open
            )
            within_grace = (
                timeframe in FRESHNESS_ALLOWANCE_MS
                and isinstance(stored, int)
                and isinstance(expected_open, int)
                and item.get("status") in {"OK", "RECOVERING"}
                and item.get("freshness_lag_candles") == 1
                and stored == expected_open - timeframe_to_milliseconds(timeframe)
                and generated_ms <= close_boundary_ms(expected_open, timeframe) + FRESHNESS_ALLOWANCE_MS[timeframe]
            )
            if not base_safe or not (current or within_grace):
                return False
        return observed == expected
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


@dataclass(frozen=True, slots=True)
class PitrLineageObservation:
    wal_ready: bool = False
    pitr_ready: bool = False
    lineage_valid: bool = False
    lineage_start: datetime | None = None
    lineage_end: datetime | None = None
    contiguous_duration_seconds: int = 0
    physical_gap: bool | None = None


def _pitr_lineage(
    root: Path,
    now: datetime,
) -> PitrLineageObservation:
    """Return safe canonical lineage facts without exposing archive paths."""

    try:
        daemon = _json_object(root / "catalog" / "wal_ack_daemon_state.json")
        updated = datetime.fromisoformat(str(daemon["updated_at"]).replace("Z", "+00:00"))
        daemon_ready = (
            daemon.get("schema") == "TRADERS_ML_WAL_ACK_DAEMON_STATE_V1"
            and daemon.get("status") == "RUNNING"
            and daemon.get("error_class") == "NONE"
            and daemon.get("export_backlog_count") == 0
            and daemon.get("pending_archive_status_count") == 0
            and 0 <= (now - updated.astimezone(timezone.utc)).total_seconds() <= MAX_WAL_DAEMON_AGE_SECONDS
        )
        catalog = _json_object(root / "catalog" / "catalog.json")
        entries = catalog.get("entries")
        if catalog.get("schema") != "TRADERS_ML_BACKUP_CATALOG_V1" or not isinstance(entries, list):
            return PitrLineageObservation()
        bases = [
            item for item in entries
            if isinstance(item, dict)
            and item.get("artifact_type") == "BASE"
            and item.get("source_class") == "PRODUCTION"
            and item.get("verification_status") == "PUBLISHED"
            and item.get("recovery_anchor_valid") is True
        ]
        if not bases:
            return PitrLineageObservation()
        base = max(bases, key=lambda item: str(item.get("created_at", "")))
        relative = str(base.get("relative_path", ""))
        base_path = (root / relative)
        label = (base_path / "backup_label").read_text(encoding="utf-8")
        start = _START_WAL.search(label)
        timeline = _START_TIMELINE.search(label)
        archive_names = tuple(
            path.name for path in (root / "wal_archive").iterdir()
            if path.is_file() and wal_segment_identity(path.name) is not None
        )
        base_wal_names = tuple(
            path.name for path in (base_path / "pg_wal").iterdir()
            if path.is_file() and wal_segment_identity(path.name) is not None
        )
        if start is None or timeline is None or not archive_names:
            return PitrLineageObservation()
        latest = max(archive_names, key=lambda name: wal_segment_identity(name) or (-1, -1))
        continuity = inspect_wal_continuity(
            timeline=int(timeline.group("timeline")),
            base_start_lsn=start.group("lsn"),
            latest_archived_segment=latest,
            base_wal_segments=base_wal_names,
            archive_wal_segments=archive_names,
        )
        oldest = datetime.fromisoformat(str(base["created_at"]).replace("Z", "+00:00"))
        newest = datetime.fromtimestamp((root / "wal_archive" / latest).stat().st_mtime, timezone.utc)
        window = max(0, int((newest - oldest.astimezone(timezone.utc)).total_seconds()))
        wal_ready = daemon_ready and continuity.base_backup_chain_contiguous
        lineage_valid = continuity.base_backup_chain_contiguous and not continuity.physical_gap
        return PitrLineageObservation(
            wal_ready=wal_ready,
            pitr_ready=wal_ready and lineage_valid and window >= MINIMUM_PITR_WINDOW_SECONDS,
            lineage_valid=lineage_valid,
            lineage_start=oldest.astimezone(timezone.utc),
            lineage_end=newest,
            contiguous_duration_seconds=window,
            physical_gap=continuity.physical_gap,
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return PitrLineageObservation()


def _pitr_readiness(root: Path, now: datetime) -> tuple[bool, bool]:
    value = _pitr_lineage(root, now)
    return value.wal_ready, value.pitr_ready


class ProductionPaperRuntimeObservationSource:
    """Compose current production readiness without any mutation capability."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        control_status: Callable[[], PaperControlStatus],
        *,
        runtime_root: Path = PRODUCTION_RUNTIME_ROOT,
        identity_root: Path = PRODUCTION_IDENTITY_ROOT,
        recovery_root: Path = PRODUCTION_RECOVERY_ROOT,
        market_health_root: Path = PRODUCTION_MARKET_HEALTH_ROOT,
        runtime_health_root: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._control_status = control_status
        self._runtime_root = runtime_root
        self._identity_root = identity_root
        self._recovery_root = recovery_root
        self._market_health_root = market_health_root
        self._runtime_health_root = runtime_health_root or resolve_production_control_root()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._approval = PaperProductionApprovalSourceAdapter(session_factory)

    def _current_execution(self) -> dict[str, object] | None:
        """Project the latest persisted SELECTED lifecycle by exact run/command identity."""
        try:
            with self._session_factory() as session:
                row = session.execute(
                    select(
                        PaperPlanExecutionOutcomeRecord,
                        PaperExecutionCommandRecord.processing_status,
                        PaperPositionRecord.position_id,
                        PaperPositionRecord.state,
                    )
                    .outerjoin(
                        PaperExecutionCommandRecord,
                        PaperExecutionCommandRecord.command_id
                        == PaperPlanExecutionOutcomeRecord.command_id,
                    )
                    .outerjoin(
                        PaperOrderRecord,
                        (PaperOrderRecord.command_id
                         == PaperPlanExecutionOutcomeRecord.command_id)
                        & (PaperOrderRecord.order_role == "ENTRY"),
                    )
                    .outerjoin(
                        PaperPositionRecord,
                        PaperPositionRecord.entry_order_id == PaperOrderRecord.order_id,
                    )
                    .where(PaperPlanExecutionOutcomeRecord.selected_winner.is_(True))
                    .order_by(
                        PaperPlanExecutionOutcomeRecord.first_observed_at.desc(),
                        PaperPlanExecutionOutcomeRecord.pipeline_run_id.desc(),
                    )
                    .limit(1)
                ).one_or_none()
            if row is None:
                return None
            outcome, processing_status, position_id, position_state = row
            if outcome.command_id is not None:
                command_status = processing_status or "CREATED"
            else:
                command_status = {
                    "PLAN_OBSERVED": "PENDING_CREATE",
                    "BLOCKED_BY_POLICY": "BLOCKED",
                    "EXPIRED_BEFORE_EXECUTION": "EXPIRED",
                    "EXECUTION_FAILED": "FAILED",
                }.get(outcome.lifecycle_state, "NOT_CREATED")
            lifecycle_state = outcome.lifecycle_state
            if position_state == "OPEN":
                lifecycle_state = "POSITION_OPEN"
            elif position_state == "CLOSING":
                lifecycle_state = "POSITION_CLOSING"
            elif position_state == "CLOSED":
                lifecycle_state = "COMPLETED"
            return {
                "source_run_id": outcome.pipeline_run_id,
                "symbol": outcome.symbol,
                "trade_profile_id": outcome.trade_profile_id,
                "boundary_closed_at_ms": outcome.boundary_closed_at_ms,
                "candidate_id": outcome.candidate_id,
                "approval_id": outcome.final_approval_id,
                "plan_id": outcome.paper_plan_id,
                "approval_valid_until_ms": outcome.approval_valid_until_ms,
                "selector_state": outcome.selector_state,
                "selector_rank": outcome.selector_rank,
                "selected_at": utc_text(outcome.first_observed_at),
                "scheduler_last_observed_at": utc_text(outcome.updated_at),
                "policy_evaluated_at": utc_text(outcome.updated_at),
                "policy_generation": outcome.control_generation,
                "policy_reason_source": "READONLY_PAPER_READINESS_CURRENT_SNAPSHOT",
                "policy_source_timestamp": utc_text(outcome.updated_at),
                "lifecycle_state": lifecycle_state,
                "command_status": command_status,
                "command_id": outcome.command_id,
                "position_status": position_state or "NOT_REACHED",
                "position_id": position_id,
                "terminal_reason": (
                    outcome.terminal_reason
                    or outcome.selector_reason
                    or ("POSITION_CLOSED" if position_state == "CLOSED" else "NOT_REACHED")
                ),
                "attempt_count": outcome.attempt_count,
            }
        except Exception:
            return None

    def __call__(self) -> PaperRuntimeObservation:
        now = self._clock()
        market_ready = _market_data_readiness(self._market_health_root, now)
        approval_ready = False
        approval_availability = "NOT_AVAILABLE"
        try:
            approval = self._approval.read(PaperProductionApprovalRequest(
                PaperProductionApprovalScope(APPROVAL_SYMBOLS, max_run_lookback=8),
                "readonly-production-paper-readiness",
            ))
            approval_ready = approval.readiness in {
                PaperProductionApprovalReadiness.READY,
                PaperProductionApprovalReadiness.HEALTHY_NO_ELIGIBLE_APPROVAL,
            }
            approval_availability = approval.outcome.value
        except Exception:
            approval_ready = False
        runtime_config_ready = _runtime_configuration_ready(self._runtime_root)
        try:
            identity_ready = load_production_identity(self._identity_root) is not None
        except (OSError, ValueError):
            identity_ready = False
        pitr = _pitr_lineage(self._recovery_root, now)
        try:
            control = self._control_status()
            kill_switch_ready = (
                control.state in {"DISABLED", "ARMED", "CONTINUOUS_ARMED", "PAUSED_BY_RISK"}
                and control.effective_state == control.state
                and control.health == "HEALTHY"
                and control.audit_health == "PASS"
                and control.state_audit_reconciliation == "PASS"
                and control.emergency_stop_available
            )
        except Exception:
            kill_switch_ready = False
        principal_ready = _runtime_principal_ready(self._session_factory)
        # PITR inspection above may take longer than one publisher interval.
        # Compare the heartbeat with a clock sampled at the actual read point;
        # using the call-entry timestamp can misclassify a newly published
        # heartbeat as coming from the future.
        automatic_runtime = read_paper_runtime_health(
            self._runtime_health_root, now=self._clock()
        )
        automatic_ready = automatic_runtime is not None
        return PaperRuntimeObservation(
            environment="production",
            # This is readiness of the bounded operator runtime artifact, not a
            # daemon/process flag.  The authoritative deployed configuration
            # remains disabled until the separate ARM transition.
            runtime_enabled=automatic_ready and automatic_runtime.get("runtime_enabled") is True,
            daemon_enabled=automatic_ready and automatic_runtime.get("daemon_enabled") is True,
            scheduler_enabled=automatic_ready and automatic_runtime.get("scheduler_enabled") is True,
            dry_run=not automatic_ready,
            mutation_enabled=automatic_ready and automatic_runtime.get("mutation_enabled") is True,
            worker_running=(
                automatic_ready
                and automatic_runtime.get("approval_watcher_active") is True
                and automatic_runtime.get("selector_active") is True
                and automatic_runtime.get("execution_worker_active") is True
                and int(automatic_runtime.get("approval_ticks", 0)) > 0
                and int(automatic_runtime.get("execution_ticks", 0)) > 0
            ),
            operator_runner_running=False,
            current_execution=self._current_execution(),
            market_data_adapter_ready=market_ready,
            approval_source_adapter_ready=approval_ready,
            wal_ready=pitr.wal_ready,
            pitr_ready=pitr.pitr_ready,
            pitr_lineage_valid=pitr.lineage_valid,
            pitr_lineage_start=pitr.lineage_start,
            pitr_lineage_end=pitr.lineage_end,
            pitr_contiguous_duration_seconds=pitr.contiguous_duration_seconds,
            pitr_physical_gap=pitr.physical_gap,
            current_approval_availability=approval_availability,
            paper_principal_ready=principal_ready,
            production_identity_binding_ready=identity_ready,
            runtime_config_ready=runtime_config_ready and automatic_ready,
            kill_switch_ready=kill_switch_ready,
            canary_scope_valid=MARKET_SYMBOLS == APPROVAL_SYMBOLS,
            live_enabled=False,
        )


__all__ = [
    "ProductionPaperRuntimeObservationSource",
    "PRODUCTION_IDENTITY_ROOT",
    "PRODUCTION_MARKET_HEALTH_ROOT",
    "PRODUCTION_RECOVERY_ROOT",
    "PRODUCTION_RUNTIME_ROOT",
    "load_production_identity",
]
