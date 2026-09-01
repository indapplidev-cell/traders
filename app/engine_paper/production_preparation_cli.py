"""Approved preparation-only CLI; no trading or secret arguments exist."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Sequence

from app.engine_paper.production_preparation import (
    ALL_PREPARATION_ACTIONS,
    EXPECTED_FINAL_ALEMBIC,
    EXPECTED_START_ALEMBIC,
    SUPPORTED_PREPARATION_REVISIONS,
    PaperPreparationAction,
    PaperPreparationFinding,
    PaperPreparationPhase,
    PaperProductionExecutionAuthorization,
    PaperProductionIdentityError,
    PaperProductionPreparationMutationBudget,
    PaperProductionTargetGuard,
)
from app.engine_paper.production_preparation_backend import (
    PaperPreparationAdapterError,
    compose_production_preparation,
)


EXIT_SUCCESS = 0
EXIT_VALIDATION_BLOCKED = 2
EXIT_TARGET_MISMATCH = 3
EXIT_PRIVILEGE_DRIFT = 4
EXIT_BINDING_UNAVAILABLE = 5
EXIT_IDENTITY_UNAVAILABLE = 6
EXIT_EXECUTION_FAILURE = 7
ACKNOWLEDGEMENT = "I_ACKNOWLEDGE_PRODUCTION_PREPARATION_MUTATIONS"
ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_CONFIG = ROOT / "ops/production/paper-preparation.json"


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("DUPLICATE_CONFIGURATION_KEY")
        value[key] = item
    return value


def _load_config(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_json_object)
    except Exception:
        raise PaperPreparationAdapterError("PREPARATION_CONFIGURATION_UNAVAILABLE") from None
    if not isinstance(raw, dict):
        raise PaperPreparationAdapterError("PREPARATION_CONFIGURATION_INVALID")
    base = path.resolve().parent
    for key in ("identity_config", "protected_binding", "state_root", "compose_file"):
        if key in raw:
            candidate = Path(str(raw[key]))
            raw[key] = str(candidate if candidate.is_absolute() else (base / candidate).resolve())
    return raw


def _emit(payload: Mapping[str, object], *, stderr: bool = False) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")),
          file=(sys.stderr if stderr else sys.stdout))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paper-production-preparation")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--production", action="store_true",
                        help="trusted canonical production target binding")
    source.add_argument("--config", type=Path,
                        help="non-secret isolated preparation composition JSON")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    subparsers.add_parser("plan", help="secret-free, zero-mutation plan")
    subparsers.add_parser("status", help="sanitized target and readiness validation")
    execute = subparsers.add_parser("execute", help="explicit bounded preparation mutations")
    execute.add_argument("--ack", required=True)
    execute.add_argument("--actions", required=True,
                         help="comma-separated exact preparation action names")
    execute.add_argument("--orchestrate-schema-and-baseline", action="store_true")
    execute.add_argument("--initial-balance-usdt", choices=("100.00",))
    return parser


def _actions(raw: str) -> tuple[PaperPreparationAction, ...]:
    try:
        values = tuple(PaperPreparationAction(item) for item in raw.split(",") if item)
    except ValueError:
        raise PaperPreparationAdapterError("ACTION_SET_INVALID") from None
    if not values or len(values) != len(set(values)):
        raise PaperPreparationAdapterError("ACTION_SET_INVALID")
    return values


def _migrate(composition) -> bool:
    return composition.backend.migrate_to_final().changed


def _baseline(composition, balance: str) -> bool:
    return composition.backend.ensure_baseline(composition.identity, Decimal(balance)).changed


def _execute(composition, actions: tuple[PaperPreparationAction, ...], *, orchestrate: bool,
             balance: str | None):
    budget = PaperProductionPreparationMutationBudget()
    if not orchestrate:
        current_revision = composition.backend.current_revision()
        if current_revision not in SUPPORTED_PREPARATION_REVISIONS:
            raise PaperPreparationAdapterError("TARGET_MISMATCH")
        current_target = PaperProductionTargetGuard(
            database_target_id=composition.target.database_target_id,
            expected_start_alembic=current_revision,
        )
        authorization = PaperProductionExecutionAuthorization(ACKNOWLEDGEMENT, actions)
        return composition.executor.execute(composition.identity, current_target, budget, authorization)
    if balance != "100.00":
        raise PaperPreparationAdapterError("EXPLICIT_100_USDT_BASELINE_REQUIRED")
    current_revision = composition.backend.current_revision()
    if current_revision not in SUPPORTED_PREPARATION_REVISIONS:
        raise PaperPreparationAdapterError("TARGET_MISMATCH")
    current_target = PaperProductionTargetGuard(
        database_target_id=composition.target.database_target_id,
        expected_start_alembic=current_revision,
    )
    if not composition.backend.validate_target(current_target):
        raise PaperPreparationAdapterError("TARGET_MISMATCH")
    migration_changed = _migrate(composition) if current_revision != EXPECTED_FINAL_ALEMBIC else False
    final_target = PaperProductionTargetGuard(
        database_target_id=composition.target.database_target_id,
        expected_start_alembic=EXPECTED_FINAL_ALEMBIC,
    )
    deployment_actions = {
        PaperPreparationAction.DEPLOY_DISABLED_RUNTIME_CONFIGURATION,
        PaperPreparationAction.DEPLOY_READONLY_API_NARROW,
    }
    before = tuple(action for action in actions if action not in deployment_actions)
    after = tuple(action for action in actions if action in deployment_actions)
    first = composition.executor.execute(composition.identity, final_target, budget,
        PaperProductionExecutionAuthorization(ACKNOWLEDGEMENT, before))
    if first.finding is not PaperPreparationFinding.READY:
        return first
    baseline_changed = (False if composition.backend.baseline_ready(composition.identity)
                        else _baseline(composition, balance))
    if not after:
        return first
    second = composition.executor.execute(composition.identity, final_target, budget,
        PaperProductionExecutionAuthorization(ACKNOWLEDGEMENT, after))
    return type(first)(actions, first.executed_actions + second.executed_actions, second.finding,
        first.binding_present or second.binding_present,
        first.binding_valid or second.binding_valid,
        consumer_health=first.consumer_health,
        production_mutations=(first.production_mutations + second.production_mutations
                              + int(migration_changed) + int(baseline_changed)))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _load_config(PRODUCTION_CONFIG if args.production else args.config)
        composition = compose_production_preparation(config, production_mode=args.production)
        if args.mode == "plan":
            state = composition.backend.preparation_state(composition.identity)
            current_target = PaperProductionTargetGuard(
                database_target_id=composition.target.database_target_id,
                expected_start_alembic=state.alembic_revision,
            ) if state.alembic_revision in SUPPORTED_PREPARATION_REVISIONS else None
            target_ok = current_target is not None and composition.backend.validate_target(current_target)
            planned = composition.executor.plan(composition.identity)
            migration_required = state.alembic_revision != EXPECTED_FINAL_ALEMBIC
            plan_ok = target_ok and state.phase is not PaperPreparationPhase.INCOMPATIBLE
            deployment_actions = {
                PaperPreparationAction.DEPLOY_DISABLED_RUNTIME_CONFIGURATION,
                PaperPreparationAction.DEPLOY_READONLY_API_NARROW,
            }
            planned_before = [item.value for item in planned.planned_actions
                              if item not in deployment_actions]
            planned_after = [item.value for item in planned.planned_actions
                             if item in deployment_actions]
            planned_steps = (([f"MIGRATE_SCHEMA_TO_{EXPECTED_FINAL_ALEMBIC.split('_', 1)[0]}"]
                              if migration_required else [])
                             + planned_before
                             + (["ENSURE_ACCOUNT_BASELINE"] if not state.baseline_ready else [])
                             + planned_after)
            _emit({"action": "PLAN", "backend": "PostgresPaperProductionPreparationBackend",
                   "binding_adapter": "PaperProductionPreparationTargetBinding", "binding_ready": True,
                   "dry_run": True, "execute_composition_ready": True,
                   "identity_adapter": "PaperProductionIdentityConfigurationAdapter",
                   "mutations": 0, "result": "PASS" if plan_ok else "BLOCKED",
                   "target": "production", "target_verified": target_ok,
                   "preparation_phase": state.phase.value,
                   "migration_action_required": migration_required,
                   "migration_already_satisfied": state.schema_ready,
                   "planned_actions": [item.value for item in planned.planned_actions],
                   "planned_steps": planned_steps,
                   "baseline_action_required": not state.baseline_ready,
                   "privilege_drift": state.privilege_drift})
            if not target_ok:
                return EXIT_TARGET_MISMATCH
            return EXIT_PRIVILEGE_DRIFT if state.privilege_drift else (
                EXIT_SUCCESS if plan_ok else EXIT_VALIDATION_BLOCKED)
        if args.mode == "status":
            state = composition.backend.preparation_state(composition.identity)
            invariance = composition.backend.safe_invariance_counts()
            current_target = PaperProductionTargetGuard(
                database_target_id=composition.target.database_target_id,
                expected_start_alembic=state.alembic_revision,
            ) if state.alembic_revision in SUPPORTED_PREPARATION_REVISIONS else None
            target_ok = current_target is not None and composition.backend.validate_target(current_target)
            role_state = composition.backend.inspect_runtime_role() if target_ok else "NOT_CHECKED"
            binding = composition.protected_binding.metadata()
            result = "PASS" if (target_ok and state.phase is not PaperPreparationPhase.INCOMPATIBLE) else "BLOCKED"
            _emit({"alembic_revision": state.alembic_revision if target_ok else "UNVERIFIED",
                    "binding_ready": True, "control_state": composition.target.control_state,
                    "dry_run": True, "execute_composition_ready": True,
                    "identity_ready": True, "result": result, "role_state": role_state,
                    "runtime_binding_ready": binding.binding_valid,
                    "target": "production", "target_verified": target_ok,
                    "preparation_phase": state.phase.value,
                    "schema_ready": state.schema_ready,
                    "baseline_ready": state.baseline_ready,
                    "runtime_role_ready": state.runtime_role_ready,
                    "runtime_grants_ready": state.runtime_grants_ready,
                    "readonly_paper_grants_ready": state.readonly_paper_grants_ready,
                    "readonly_baseline_grants_ready": state.readonly_baseline_grants_ready,
                    "runtime_configuration_ready": state.runtime_configuration_ready,
                    "readonly_reporting_deployed": state.readonly_reporting_deployed,
                    "preparation_complete": state.preparation_complete,
                    "privilege_drift": state.privilege_drift,
                    # Fixed count-only readback; no identifiers or row contents cross the boundary.
                    **invariance})
            if not target_ok:
                return EXIT_TARGET_MISMATCH
            return EXIT_PRIVILEGE_DRIFT if state.privilege_drift else EXIT_SUCCESS
        actions = _actions(args.actions)
        if args.ack != ACKNOWLEDGEMENT:
            _emit({"result": "BLOCKED", "reason": "EXECUTION_NOT_AUTHORIZED"}, stderr=True)
            return EXIT_VALIDATION_BLOCKED
        result = _execute(composition, actions,
                          orchestrate=args.orchestrate_schema_and_baseline,
                          balance=args.initial_balance_usdt)
        _emit({"actions": [item.value for item in result.executed_actions],
               "binding_ready": result.binding_valid, "dry_run": False,
               "identity_ready": True, "mutations": result.production_mutations,
               "result": "PASS" if result.finding is PaperPreparationFinding.READY else "BLOCKED",
               "role_name": result.role_name, "target": "production"})
        if result.finding is PaperPreparationFinding.TARGET_ENVIRONMENT_MISMATCH:
            return EXIT_TARGET_MISMATCH
        if result.finding is PaperPreparationFinding.EXISTING_ROLE_PRIVILEGE_DRIFT:
            return EXIT_PRIVILEGE_DRIFT
        if result.finding is PaperPreparationFinding.RUNTIME_CREDENTIAL_BINDING_MISSING:
            return EXIT_BINDING_UNAVAILABLE
        return EXIT_SUCCESS if result.finding is PaperPreparationFinding.READY else EXIT_VALIDATION_BLOCKED
    except PaperProductionIdentityError:
        _emit({"result": "BLOCKED", "reason": "IDENTITY_UNAVAILABLE"}, stderr=True)
        return EXIT_IDENTITY_UNAVAILABLE
    except PaperPreparationAdapterError as error:
        reason = str(error)
        _emit({"result": "BLOCKED", "reason": reason}, stderr=True)
        if reason in {"TARGET_MISMATCH", "PRODUCTION_TARGET_MISMATCH", "SCHEMA_REVISION_UNAVAILABLE"}:
            return EXIT_TARGET_MISMATCH
        if reason in {"PRODUCTION_TARGET_BINDING_UNAVAILABLE", "PRODUCTION_TARGET_BINDING_INVALID"}:
            return EXIT_BINDING_UNAVAILABLE
        return EXIT_EXECUTION_FAILURE
    except Exception:
        _emit({"result": "BLOCKED", "reason": "EXECUTION_FAILURE"}, stderr=True)
        return EXIT_EXECUTION_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
