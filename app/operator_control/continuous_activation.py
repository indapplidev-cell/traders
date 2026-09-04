"""Explicit audited activation of continuous production PAPER authority."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from app.engine_paper.continuous_authority import PaperContinuousAuthorityStore
from app.engine_safety.paper_production_control import (
    ArmReadinessPreflight,
    PaperProductionArmingScope,
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
)
from app.engine_safety.production_control_root import resolve_production_control_root
from app.trading_universe.activation import SqlAlchemyTradingUniverseStore

from .runtime import DEFAULT_READONLY_INTERNAL_URL, READONLY_INTERNAL_URL_KEY, _production_canary_store


def _read_readiness() -> dict[str, object]:
    url = os.environ.get(READONLY_INTERNAL_URL_KEY, DEFAULT_READONLY_INTERNAL_URL).rstrip("/")
    with urllib.request.urlopen(url + "/api/v1/paper/readiness", timeout=10) as response:
        document = json.loads(response.read())
    data = document.get("data") if isinstance(document, dict) else None
    if response.status != 200 or not isinstance(data, dict):
        raise RuntimeError("READONLY_READINESS_UNAVAILABLE")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-generation", type=int, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--reason", default="USER_AUTHORIZED_CONTINUOUS_PAPER_DEPLOYMENT")
    parser.add_argument("--acknowledge-paper-only", action="store_true")
    parser.add_argument("--acknowledge-live-disabled", action="store_true")
    args = parser.parse_args(argv)
    if not args.acknowledge_paper_only or not args.acknowledge_live_disabled:
        raise SystemExit("ACTIVATION_ACKNOWLEDGEMENTS_REQUIRED")

    readiness = _read_readiness()
    preflight = ArmReadinessPreflight(
        schema_at_required_head=readiness.get("paper_schema_ready") is True,
        minimum_pitr_window_pass=int(readiness.get("pitr_contiguous_duration_seconds") or 0) >= 86400,
        market_data_adapter_ready=readiness.get("market_data_adapter_ready") is True,
        approval_source_adapter_ready=readiness.get("approval_source_adapter_ready") is True,
        wal_archive_health_pass=readiness.get("wal_ready") is True,
        wal_unresolved_failures_zero="WAL_UNRESOLVED_FAILURES" not in tuple(readiness.get("current_mutation_denial_reasons") or ()),
        pitr_chain_valid=readiness.get("pitr_ready") is True and readiness.get("pitr_physical_gap") is False,
        paper_runtime_explicitly_enabled=readiness.get("paper_runtime_enabled") is True,
        live_disabled=readiness.get("live_allowed") is False,
    )
    if not preflight.passed:
        raise SystemExit("ACTIVATION_PREFLIGHT_FAILED:" + ",".join(preflight.findings))

    _, engine = _production_canary_store()
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    universe = SqlAlchemyTradingUniverseStore(sessions).active_universe()
    if universe.version_id != "trading-universe-v2":
        raise SystemExit("ACTIVE_TRADING_UNIVERSE_V2_REQUIRED")
    control = PaperProductionSafetyControl(resolve_production_control_root(), acl_checker=lambda _path: True)
    before = control.read_authoritative()
    if before.state is PersistentState.CONTINUOUS_ARMED:
        # Recover only the exact host-side half of a previously interrupted
        # activation; never mint another generation or broaden its scope.
        if (
            before.generation != args.expected_generation + 1
            or before.arming_scope is None
            or before.arming_scope.max_new_commands != 1
            or before.arming_scope.max_open_positions != 1
            or before.arming_scope.allowed_symbols != tuple(sorted(universe.symbols))
        ):
            raise SystemExit("CONTINUOUS_ACTIVATION_RECOVERY_MISMATCH")
        after = before
    else:
        if before.state is not PersistentState.DISABLED or before.generation != args.expected_generation:
            raise SystemExit("CONTINUOUS_ACTIVATION_REQUIRES_MATCHING_DISABLED_GENERATION")
        after = control.transition(
            PersistentState.CONTINUOUS_ARMED,
            expected_generation=before.generation,
            reason=ReasonCode.CONTINUOUS_PAPER_ACTIVATION,
            acknowledge=True,
            acknowledge_paper_arming=True,
            preflight=preflight,
            arming_scope=PaperProductionArmingScope(1, 1, tuple(sorted(universe.symbols))),
        )
    snapshot = PaperContinuousAuthorityStore(sessions).activate(
        generation=after.generation, source=args.source, reason=args.reason,
        now=datetime.now(timezone.utc),
    )
    print(json.dumps({
        "status": "CONTINUOUS_ARMED", "generation": after.generation,
        "transition_id": after.transition_id, "mode": snapshot.control_mode,
        "mode_version": snapshot.mode_version,
        "budget_policy_version": snapshot.budget_policy_version,
        "budget_policy_source": snapshot.budget_policy_source,
        "budget_enforcement_mode": snapshot.budget_enforcement_mode,
        "budget_day": snapshot.budget_day.isoformat(),
        "budget_reset_at": snapshot.budget_reset_at.isoformat(),
        "live_allowed": False, "binance_order_calls": 0,
    }, sort_keys=True))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
