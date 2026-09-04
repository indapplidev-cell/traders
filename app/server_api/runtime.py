"""Production composition root and canonical executable for the read-only API."""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import timezone

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from uvicorn import run as run_server

from app.server_api.app_factory import create_app
from app.server_api.repositories.protocols import ApiRepositories
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter
from app.server_api.trading_funnel import TradingFunnelReadRepository
from app.server_api.runtime_config import RuntimeConfig
from app.server_api.schema_compatibility import (
    ReadonlySchemaCapabilityBridge,
    inspect_readonly_schema_capabilities,
)
from app.server_api.schemas.paper import PaperControlStatus
from app.engine_safety.paper_production_control import PaperProductionSafetyControl
from app.engine_safety.production_control_root import resolve_production_control_root
from app.engine_paper.first_canary_correlation import (
    PaperFirstCanaryState,
    SqlAlchemyPaperFirstCanaryStore,
)
from app.engine_paper.continuous_authority import (
    PaperContinuousAuthorityStore, SCALPING_V2_RISK_PER_TRADE_BPS,
)
from app.server_api.paper_runtime_observation import (
    ProductionPaperRuntimeObservationSource,
    load_production_identity,
)


APPLICATION_NAME = "traders-readonly-api"
FACTORY_REFERENCE = "app.server_api.runtime:create_runtime_app"


def _budget_semantics(budget) -> dict[str, dict[str, str]]:
    if budget is None:
        return {}
    updated_at = budget.updated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    daily = {
        "window": "UTC_TRADING_DAY",
        "reset_boundary": "00:00:00Z",
        "updated_at": updated_at,
    }
    sources = {
        "daily_command_budget": (budget.daily_command_budget_unit, budget.budget_policy_source),
        "commands_used_today": (budget.daily_command_budget_unit, "PAPER_CONTINUOUS_COMMAND_EVENT_LEDGER"),
        "daily_realized_loss_budget": (budget.daily_realized_loss_budget_unit, budget.budget_policy_source),
        "realized_pnl_today": ("USDT", "CLOSED_PAPER_TRADE_NET_PNL"),
        "realized_loss_today": (budget.daily_realized_loss_budget_unit, "CLOSED_PAPER_TRADE_NET_LOSS"),
        "daily_risk_budget_bps": (budget.daily_risk_budget_unit, budget.budget_policy_source),
        "risk_used_today_bps": (budget.daily_risk_budget_unit, "PAPER_CONTINUOUS_COMMAND_EVENT_LEDGER"),
        "max_consecutive_losses": (budget.loss_streak_unit, budget.budget_policy_source),
        "loss_streak": (budget.loss_streak_unit, "CLOSED_PAPER_TRADE_NET_PNL"),
    }
    return {
        field: {"unit": unit, "source": source, **daily}
        for field, (unit, source) in sources.items()
    }


def _create_engine(config: RuntimeConfig) -> Engine:
    options = (
        "-c default_transaction_read_only=on "
        f"-c statement_timeout={config.statement_timeout_ms} "
        f"-c application_name={APPLICATION_NAME}"
    )
    return create_engine(
        config.connection_url,
        pool_pre_ping=True,
        pool_size=config.pool_size,
        max_overflow=0,
        pool_timeout=config.pool_timeout_seconds,
        connect_args={"options": options},
    )


def _repositories(
    engine: Engine, capabilities: ReadonlySchemaCapabilityBridge | None = None
) -> ApiRepositories:
    sessions = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    adapter = SqlAlchemyReadAdapter(sessions, schema_capabilities=capabilities)
    funnel = TradingFunnelReadRepository(
        sessions, adapter.active_trading_universe, schema_capabilities=capabilities
    )
    return ApiRepositories(
        health=adapter,
        markets=adapter,
        analysis=adapter,
        setups=adapter,
        incidents=adapter,
        dashboard=adapter,
        paper=adapter,
        universe=adapter,
        funnel=funnel,
    )


def _paper_control_status(
    control: PaperProductionSafetyControl,
    canaries: SqlAlchemyPaperFirstCanaryStore | None = None,
    continuous: PaperContinuousAuthorityStore | None = None,
) -> PaperControlStatus:
    """Observe the reconciled control state without acquiring/writing a lock."""
    state = control.read_authoritative()
    canary = None if canaries is None else canaries.current()
    budget = None if continuous is None else continuous.read()
    if state.state.value == "CONTINUOUS_ARMED":
        if (
            budget is None
            or budget.generation != state.generation
            or budget.control_mode != "CONTINUOUS"
            or budget.control_state not in {"CONTINUOUS_ARMED", "PAUSED_BY_RISK"}
        ):
            raise RuntimeError("CONTROL_CONTINUOUS_RECONCILIATION_FAILED")
    elif state.state.value == "ARMED":
        if (
            canary is None
            or canary.state not in {
                PaperFirstCanaryState.ARMED,
                PaperFirstCanaryState.ARMED_WAITING,
                PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL,
                PaperFirstCanaryState.RUNNING,
                PaperFirstCanaryState.POSITION_OPEN,
                PaperFirstCanaryState.POSITION_CLOSING,
                PaperFirstCanaryState.POSITION_CLOSED,
                PaperFirstCanaryState.RECONCILIATION_PENDING,
            }
            or canary.current_control_generation != state.generation
        ):
            raise RuntimeError("CONTROL_CANARY_RECONCILIATION_FAILED")
    canary_status = None
    if canary is not None:
        canary_status = (
            "WAITING_FOR_ELIGIBLE_APPROVAL"
            if canary.state is PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL
            else canary.state.value
        )
    limits_enforced = (
        budget is not None and budget.budget_enforcement_mode == "REAL_MONEY_LIMITED"
    )
    return PaperControlStatus(
        state=state.state.value,
        effective_state=(state.state.value if budget is None else budget.effective_state),
        generation=state.generation,
        health="HEALTHY",
        emergency_stop_available=True,
        audit_health="PASS",
        state_audit_reconciliation="PASS",
        canary_id=None if canary is None else canary.canary_id,
        canary_status=canary_status,
        canary_command_limit=None if canary is None else canary.max_new_commands,
        canary_command_count=None if canary is None else canary.command_count,
        canary_command_remaining=None if canary is None else max(0, canary.max_new_commands - canary.command_count),
        canary_command_budget_exhausted=None if canary is None else canary.command_count >= canary.max_new_commands,
        canary_open_position_limit=None if canary is None else canary.max_open_positions,
        canary_open_position_count=None if canary is None else canary.position_count,
        canary_open_position_remaining=None if canary is None else max(0, canary.max_open_positions - canary.position_count),
        canary_open_position_budget_exhausted=None if canary is None else canary.position_count >= canary.max_open_positions,
        canary_closed_trade_count=None if canary is None else int(canary.trade_report_available),
        authority_mode=("CONTINUOUS" if budget is not None else "FIRST_CANARY_HISTORICAL"),
        control_mode_version=None if budget is None else budget.mode_version,
        budget_policy_version=None if budget is None else budget.budget_policy_version,
        budget_policy_source=None if budget is None else budget.budget_policy_source,
        budget_enforcement_mode=None if budget is None else budget.budget_enforcement_mode,
        risk_per_trade_value=(None if budget is None else format(SCALPING_V2_RISK_PER_TRADE_BPS, "f")),
        risk_per_trade_unit=None if budget is None else "equity_basis_points",
        risk_per_trade_source=(
            None if budget is None else
            "SCALPING_V2_RUNTIME_PARAMETERS/risk_per_trade_bps"
        ),
        daily_loss_formula=(
            None if budget is None else
            "SUM(ABS(net_pnl)) WHERE closed_trade AND net_pnl < 0; UNIQUE(position_id)"
        ),
        daily_risk_formula=(
            None if budget is None else
            "SUM(scalping_v2.risk_per_trade_bps) PER UNIQUE(command_id)"
        ),
        budget_day=None if budget is None else budget.budget_day.isoformat(),
        budget_reset_at=(
            None if budget is None else
            budget.budget_reset_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        ),
        daily_command_budget_value=None if budget is None else budget.commands_used,
        daily_command_budget_limit=(budget.daily_command_budget if limits_enforced else None),
        daily_command_budget_unit=None if budget is None else budget.daily_command_budget_unit,
        daily_command_budget_source=None if budget is None else budget.budget_policy_source,
        daily_risk_used=None if budget is None else format(budget.risk_used_bps, "f"),
        daily_risk_limit=(format(budget.daily_risk_budget_bps, "f") if limits_enforced else None),
        daily_risk_unit=None if budget is None else budget.daily_risk_budget_unit,
        daily_risk_source=None if budget is None else budget.budget_policy_source,
        daily_realized_loss_used=None if budget is None else format(budget.realized_loss, "f"),
        daily_realized_loss_limit=(
            format(budget.daily_realized_loss_budget, "f") if limits_enforced else None
        ),
        daily_realized_loss_unit=(None if budget is None else budget.daily_realized_loss_budget_unit),
        daily_realized_loss_source=None if budget is None else budget.budget_policy_source,
        loss_streak_used=None if budget is None else budget.loss_streak,
        loss_streak_limit=(budget.max_consecutive_losses if limits_enforced else None),
        loss_streak_source=None if budget is None else budget.budget_policy_source,
        risk_pause=(None if budget is None else budget.control_state == "PAUSED_BY_RISK"),
        daily_command_budget=(budget.daily_command_budget if limits_enforced else None),
        commands_used_today=None if budget is None else budget.commands_used,
        daily_realized_loss_budget=(
            format(budget.daily_realized_loss_budget, "f") if limits_enforced else None
        ),
        realized_pnl_today=None if budget is None else format(budget.realized_pnl, "f"),
        realized_loss_today=None if budget is None else format(budget.realized_loss, "f"),
        daily_risk_budget_bps=(
            format(budget.daily_risk_budget_bps, "f") if limits_enforced else None
        ),
        risk_used_today_bps=None if budget is None else format(budget.risk_used_bps, "f"),
        max_consecutive_losses=(budget.max_consecutive_losses if limits_enforced else None),
        loss_streak=None if budget is None else budget.loss_streak,
        risk_pause_reason=None if budget is None else budget.pause_reason,
        budget_semantics=_budget_semantics(budget),
    )


def create_runtime_app() -> FastAPI:
    """Compose the production ASGI application without connecting at import."""
    config = RuntimeConfig.from_environment()
    engine = _create_engine(config)
    schema_capabilities = ReadonlySchemaCapabilityBridge()
    repositories = _repositories(engine, schema_capabilities)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    control = PaperProductionSafetyControl(
        resolve_production_control_root(),
        # Docker Desktop does not project Windows ACL metadata into Linux.
        acl_checker=(lambda _path: True),
    )
    canaries = SqlAlchemyPaperFirstCanaryStore(sessions)
    continuous = PaperContinuousAuthorityStore(sessions)
    control_status = lambda: _paper_control_status(control, canaries, continuous)
    paper_runtime = ProductionPaperRuntimeObservationSource(sessions, control_status)
    try:
        production_identity = load_production_identity()
    except (OSError, ValueError):
        # The service may start for diagnostics, but readiness remains
        # fail-closed through the observation source when the binding is absent.
        production_identity = None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            with engine.connect() as connection:
                mode = connection.exec_driver_sql(
                    "SHOW transaction_read_only"
                ).scalar_one()
                if mode != "on":
                    raise RuntimeError(
                        "database session did not enforce the read-only boundary"
                    )
                schema_capabilities.activate(
                    inspect_readonly_schema_capabilities(connection)
                )
            yield
        finally:
            engine.dispose()

    app = create_app(
        repositories=repositories,
        paper_runtime=paper_runtime,
        paper_control_status=control_status,
        paper_production_identity=production_identity,
    )
    app.router.lifespan_context = lifespan
    app.state.runtime_config = config
    app.state.runtime_engine = engine
    app.state.runtime_repositories = repositories
    app.state.readonly_schema_capabilities = schema_capabilities
    return app


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APPLICATION_NAME,
        description="Run the Traders read-only API using its environment contract.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.2.0",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _parser().parse_args(argv)
    config = RuntimeConfig.from_environment()
    run_server(
        FACTORY_REFERENCE,
        factory=True,
        host=config.host,
        port=config.port,
        log_level=config.log_level,
        access_log=True,
        reload=False,
        workers=1,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
