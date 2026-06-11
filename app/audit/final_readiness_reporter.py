from __future__ import annotations

import json
from typing import Any

from app.audit.final_readiness_audit import build_final_readiness_audit


class FinalReadinessReporter:
    """Serialize the final standalone readiness audit."""

    def build_full_report(self) -> dict[str, Any]:
        return build_final_readiness_audit().to_dict()

    def build_compact_summary(self) -> dict[str, Any]:
        report = self.build_full_report()
        components = report["components"]
        ready_component_count = sum(
            int(component["status"] == "READY")
            for component in components.values()
        )
        needs_attention_component_count = sum(
            int(component["status"] != "READY")
            for component in components.values()
        )
        return {
            "audit_name": report["audit_name"],
            "audit_version": report["audit_version"],
            "status": report["status"],
            "ready_component_count": ready_component_count,
            "needs_attention_component_count": needs_attention_component_count,
            "standalone_ml_service_ready": report["summary"][
                "standalone_ml_service_ready"
            ],
            "api_gate_policy_block_ready": report["summary"][
                "api_gate_policy_block_ready"
            ],
            "gate_policy_replay_evaluation_ready": report["summary"][
                "gate_policy_replay_evaluation_ready"
            ],
            "traders_core_connected": report["safety_boundaries"][
                "traders_core_connected"
            ],
            "live_trading_connected": report["safety_boundaries"][
                "live_trading_connected"
            ],
            "orders_enabled": report["safety_boundaries"]["orders_enabled"],
        }

    def full_report_to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            self.build_full_report(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def compact_summary_to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            self.build_compact_summary(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )
