from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config.settings import PROJECT_ROOT


TRADERS_ML_READINESS_AUDIT_NAME = "traders_ml_final_standalone_readiness_audit"
TRADERS_ML_READINESS_AUDIT_VERSION = "ml24"

READY = "READY"
NEEDS_ATTENTION = "NEEDS_ATTENTION"
READY_STANDALONE = "READY_STANDALONE"


@dataclass(frozen=True)
class ReadinessAuditComponent:
    name: str
    status: str
    required_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "required_files": list(self.required_files),
            "missing_files": list(self.missing_files),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class FinalReadinessAuditResult:
    audit_name: str
    audit_version: str
    status: str
    summary: dict[str, Any]
    components: dict[str, ReadinessAuditComponent]
    safety_boundaries: dict[str, bool]
    capabilities: tuple[str, ...]
    known_limits: tuple[str, ...]
    next_steps: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_name": self.audit_name,
            "audit_version": self.audit_version,
            "status": self.status,
            "summary": dict(self.summary),
            "components": {
                key: component.to_dict()
                for key, component in self.components.items()
            },
            "safety_boundaries": dict(self.safety_boundaries),
            "capabilities": list(self.capabilities),
            "known_limits": list(self.known_limits),
            "next_steps": list(self.next_steps),
        }


class FinalReadinessAudit:
    """Build the final standalone readiness audit for traders-ml."""

    COMPONENT_SPECS: dict[str, dict[str, Any]] = {
        "project_identity": {
            "name": "Project identity",
            "required_files": (
                "README.md",
                "pyproject.toml",
            ),
            "notes": (
                "Project identity is defined by README and packaging metadata.",
            ),
        },
        "api_layer": {
            "name": "API layer",
            "required_files": (
                "app/api/main.py",
                "app/api/routes_predict.py",
                "app/api/schemas.py",
                "app/api/gate_policy_response_builder.py",
            ),
            "notes": (
                "FastAPI health, prediction, models, and replay endpoints exist.",
                "The /predict response includes a GatePolicy block.",
            ),
        },
        "prediction_layer": {
            "name": "Prediction layer",
            "required_files": (
                "app/prediction/prediction_service.py",
                "app/prediction/predictor.py",
            ),
            "notes": (
                "Prediction layer serves model inference and payload generation.",
            ),
        },
        "gate_policy_layer": {
            "name": "GatePolicy layer",
            "required_files": (
                "app/gates/gate_policy_service.py",
                "app/gates/gate_policy_reporter.py",
                "app/gates/gate_policy_prediction_runtime_adapter.py",
                "app/gates/gate_policy_prediction_runtime_adapter_contract.py",
                "app/gates/gate_policy_prediction_runtime_adapter_contract_reporter.py",
            ),
            "notes": (
                "GatePolicy logic, adapter contract, and reporters are present.",
            ),
        },
        "runtime_binding_layer": {
            "name": "Runtime binding layer",
            "required_files": (
                "app/gates/gate_policy_prediction_runtime_binding.py",
                "app/gates/gate_policy_prediction_runtime_binding_reporter.py",
                "reports/stage_ml21_prediction_service_gate_policy_runtime_binding_report.md",
            ),
            "notes": (
                "ML21 runtime binding connects prediction payloads to GatePolicy safely.",
            ),
        },
        "replay_evaluation_layer": {
            "name": "Replay and evaluation layer",
            "required_files": (
                "app/evaluation/gate_policy_replay_evaluator.py",
                "app/evaluation/gate_policy_replay_reporter.py",
                "app/replay/replay_service.py",
                "app/replay/historical_replay_engine.py",
                "reports/stage_ml23_gate_policy_replay_evaluation_report.md",
            ),
            "notes": (
                "Replay and evaluation through GatePolicy are implemented.",
            ),
        },
        "cli_layer": {
            "name": "CLI layer",
            "required_files": (
                "app/cli/commands.py",
            ),
            "notes": (
                "Typer CLI exposes diagnostics, training, prediction, GatePolicy, replay, and audit commands.",
            ),
        },
        "reports_layer": {
            "name": "Reports layer",
            "required_files": (
                "reports/stage_ml19_prediction_mapping_plan_report.md",
                "reports/stage_ml20_prediction_runtime_adapter_contract_report.md",
                "reports/stage_ml21_prediction_service_gate_policy_runtime_binding_report.md",
                "reports/stage_ml22_api_gate_policy_response_report.md",
                "reports/stage_ml23_gate_policy_replay_evaluation_report.md",
            ),
            "notes": (
                "Stage reports document ML19 through ML23 readiness layers.",
            ),
        },
        "tests_layer": {
            "name": "Tests layer",
            "required_files": (
                "tests/test_api_predict_gate_policy_block.py",
                "tests/test_gate_policy_replay_evaluator.py",
                "tests/test_gate_policy_replay_reporter.py",
                "tests/test_gate_policy_replay_cli.py",
            ),
            "notes": (
                "API GatePolicy and replay evaluation tests are present.",
            ),
        },
        "safety_boundaries": {
            "name": "Safety boundaries",
            "required_files": (),
            "notes": (
                "traders-ml remains analytical and does not execute trades.",
            ),
        },
        "next_integration_boundaries": {
            "name": "Next integration boundaries",
            "required_files": (),
            "notes": (
                "Future traders-core integration should happen through HTTP only when explicitly requested.",
            ),
        },
    }

    def __init__(self, project_root: Path | None = None) -> None:
        self._project_root = project_root or PROJECT_ROOT

    def run(self) -> FinalReadinessAuditResult:
        components = {
            key: self._build_component(key, spec)
            for key, spec in self.COMPONENT_SPECS.items()
        }

        status = (
            READY_STANDALONE
            if all(component.status == READY for component in components.values())
            else NEEDS_ATTENTION
        )

        safety_boundaries = {
            "opens_trades": False,
            "places_orders": False,
            "sizes_positions": False,
            "uses_exchange_api": False,
            "traders_core_connected": False,
            "live_trading_connected": False,
            "orders_enabled": False,
            "database_writes_for_gate_policy": False,
            "database_migrations_required": False,
            "production_deploy_required": False,
        }

        summary = {
            "standalone_ml_service_ready": status == READY_STANDALONE,
            "api_gate_policy_block_ready": components["api_layer"].status == READY,
            "gate_policy_replay_evaluation_ready": (
                components["replay_evaluation_layer"].status == READY
            ),
            "traders_core_direct_connection": False,
            "live_trading_enabled": False,
            "orders_enabled": False,
        }

        return FinalReadinessAuditResult(
            audit_name=TRADERS_ML_READINESS_AUDIT_NAME,
            audit_version=TRADERS_ML_READINESS_AUDIT_VERSION,
            status=status,
            summary=summary,
            components=components,
            safety_boundaries=safety_boundaries,
            capabilities=(
                "Load and normalize historical candles.",
                "Build features.",
                "Build labels.",
                "Build datasets.",
                "Train and evaluate models.",
                "Generate predictions.",
                "Return prediction API responses.",
                "Attach a GatePolicy block to /predict.",
                "Run replay/evaluation through GatePolicy.",
                "Export diagnostic JSON reports through CLI.",
                "Operate as a standalone ML analytics module.",
            ),
            known_limits=(
                "traders-ml does not execute trades.",
                "traders-ml is not connected directly to traders-core.",
                "traders-ml does not manage balances, orders, or positions.",
                "Live trading is disabled.",
                "Automatic model activation is not part of ML24.",
                "Production and server deploy are outside ML24 scope.",
                "traders-core integration must be a separate HTTP API stage.",
            ),
            next_steps=(
                "Integrate with traders-core through HTTP only when requested.",
                "Run production-like local smoke before external deployment.",
                "Keep ML service analytical; execution remains outside traders-ml.",
            ),
        )

    def _build_component(
        self,
        key: str,
        spec: dict[str, Any],
    ) -> ReadinessAuditComponent:
        required_files = tuple(spec["required_files"])
        missing_files = tuple(
            file_path
            for file_path in required_files
            if not (self._project_root / file_path).exists()
        )
        status = READY if not missing_files else NEEDS_ATTENTION
        return ReadinessAuditComponent(
            name=str(spec["name"]),
            status=status,
            required_files=required_files,
            missing_files=missing_files,
            notes=tuple(spec["notes"]),
        )


def build_final_readiness_audit() -> FinalReadinessAuditResult:
    """Build the final traders-ml standalone readiness audit."""

    return FinalReadinessAudit().run()
