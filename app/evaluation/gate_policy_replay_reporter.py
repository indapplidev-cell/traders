from __future__ import annotations

import json
from typing import Any

from app.evaluation.gate_policy_replay_evaluator import (
    GatePolicyReplayEvaluationSummary,
)


class GatePolicyReplayReporter:
    """Serialize GatePolicy replay evaluation summaries."""

    def summary_to_dict(
        self,
        summary: GatePolicyReplayEvaluationSummary,
    ) -> dict[str, Any]:
        return summary.to_dict(include_records=True)

    def compact_summary_to_dict(
        self,
        summary: GatePolicyReplayEvaluationSummary,
    ) -> dict[str, Any]:
        return summary.to_dict(include_records=False)

    def summary_to_json(
        self,
        summary: GatePolicyReplayEvaluationSummary,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.summary_to_dict(summary),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def compact_summary_to_json(
        self,
        summary: GatePolicyReplayEvaluationSummary,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.compact_summary_to_dict(summary),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )
