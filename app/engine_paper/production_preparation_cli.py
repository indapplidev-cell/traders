"""Approved preparation-only CLI; no trading or secret arguments exist."""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Mapping, Sequence

from app.engine_paper.production_preparation import (
    ALL_PREPARATION_ACTIONS,
    EXPECTED_FINAL_ALEMBIC,
    EXPECTED_START_ALEMBIC,
    PaperPreparationAction,
    PaperPreparationFinding,
    PaperProductionExecutionAuthorization,
    PaperProductionIdentityError,
    PaperProductionPreparationMutationBudget,
    PaperProductionTargetGuard,
)
from app.engine_paper.production_preparation_backend import (
    PaperPreparationAdapterError,
    PaperProductionIdentityConfigurationAdapter,
    compose_production_preparation,
    validate_production_preparation_config,
)


EXIT_SUCCESS = 0
EXIT_VALIDATION_BLOCKED = 2
EXIT_TARGET_MISMATCH = 3
EXIT_PRIVILEGE_DRIFT = 4
EXIT_BINDING_UNAVAILABLE = 5
EXIT_IDENTITY_UNAVAILABLE = 6
EXIT_EXECUTION_FAILURE = 7
ACKNOWLEDGEMENT = "I_ACKNOWLEDGE_PRODUCTION_PREPARATION_MUTATIONS"


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
    parser.add_argument("--config", type=Path, required=True,
                        help="non-secret preparation composition JSON")
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
        authorization = PaperProductionExecutionAuthorization(ACKNOWLEDGEMENT, actions)
        return composition.executor.execute(composition.identity, composition.target, budget, authorization)
    if balance != "100.00":
        raise PaperPreparationAdapterError("EXPLICIT_100_USDT_BASELINE_REQUIRED")
    current_revision = composition.backend.current_revision()
    if current_revision not in {EXPECTED_START_ALEMBIC, EXPECTED_FINAL_ALEMBIC}:
        raise PaperPreparationAdapterError("TARGET_MISMATCH")
    current_target = PaperProductionTargetGuard(
        database_target_id=composition.target.database_target_id,
        expected_start_alembic=current_revision,
    )
    if not composition.backend.validate_target(current_target):
        raise PaperPreparationAdapterError("TARGET_MISMATCH")
    migration_changed = _migrate(composition)
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
    baseline_changed = _baseline(composition, balance)
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
        config = _load_config(args.config)
        if args.mode == "plan":
            validate_production_preparation_config(config)
            identity = PaperProductionIdentityConfigurationAdapter(Path(str(config["identity_config"]))).load()
            del identity
            _emit({"action": "PLAN", "backend": "PostgresPaperProductionPreparationBackend",
                   "binding_adapter": "ProtectedPaperRuntimeBindingAdapter", "dry_run": True,
                   "identity_adapter": "PaperProductionIdentityConfigurationAdapter",
                   "mutations": 0, "result": "PASS", "target": "production"})
            return EXIT_SUCCESS
        composition = compose_production_preparation(config)
        if args.mode == "status":
            target_ok = composition.backend.validate_target(composition.target)
            role_state = composition.backend.inspect_runtime_role() if target_ok else "NOT_CHECKED"
            binding = composition.protected_binding.metadata()
            result = "PASS" if target_ok and role_state != "BROADER_THAN_CONTRACT" else "BLOCKED"
            _emit({"binding_ready": binding.binding_valid, "dry_run": True,
                   "identity_ready": True, "result": result, "role_state": role_state,
                   "target": "production", "target_verified": target_ok})
            if not target_ok:
                return EXIT_TARGET_MISMATCH
            return EXIT_PRIVILEGE_DRIFT if role_state == "BROADER_THAN_CONTRACT" else EXIT_SUCCESS
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
        return EXIT_TARGET_MISMATCH if reason == "TARGET_MISMATCH" else EXIT_EXECUTION_FAILURE
    except Exception:
        _emit({"result": "BLOCKED", "reason": "EXECUTION_FAILURE"}, stderr=True)
        return EXIT_EXECUTION_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
