from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MultiSymbolFeatureRegimeReporter:
    """Serialize multi-symbol feature/regime analysis results."""

    def result_to_dict(self, result: object) -> dict[str, Any]:
        if isinstance(result, dict):
            return dict(result)
        to_dict = getattr(result, "to_dict", None)
        if callable(to_dict):
            return dict(to_dict())
        raise TypeError("result must be a dict or provide to_dict()")

    def result_to_json(self, result: object, *, indent: int | None = 2) -> str:
        return json.dumps(
            self.result_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def compact_summary_to_dict(
        self,
        result: object,
        *,
        json_path: str | None = None,
        markdown_path: str | None = None,
    ) -> dict[str, Any]:
        payload = self.result_to_dict(result)
        return {
            "status": "ok",
            "symbols": payload.get("symbols"),
            "experiment_count": payload.get("experiment_count"),
            "candidate_count": payload.get("candidate_count"),
            "evaluated_candidate_count": payload.get("evaluated_candidate_count"),
            "failed_candidate_count": payload.get("failed_candidate_count"),
            "accepted_candidate_count": payload.get("accepted_candidate_count"),
            "rejected_candidate_count": payload.get("rejected_candidate_count"),
            "best_symbol": payload.get("best_symbol"),
            "best_candidate_config_id": payload.get("best_candidate_config_id"),
            "best_candidate_score": payload.get("best_candidate_score"),
            "all_feature_version_fv2": payload.get("all_feature_version_fv2"),
            "all_gap_training_safe": payload.get("all_gap_training_safe"),
            "all_real_feature_diagnostics_used": payload.get("all_real_feature_diagnostics_used"),
            "any_accepted_candidate": payload.get("any_accepted_candidate"),
            "top_failed_gate": payload.get("top_failed_gate"),
            "symbols_missing_real_diagnostics": payload.get("symbols_missing_real_diagnostics"),
            "symbols_missing_regime_features": payload.get("symbols_missing_regime_features"),
            "analysis_json_path": json_path,
            "analysis_markdown_path": markdown_path,
            "approved_for_live_trading": False,
            "approved_for_auto_activation": False,
            "orders_enabled": False,
            "traders_core_connected": False,
        }

    def compact_summary_to_json(
        self,
        result: object,
        *,
        json_path: str | None = None,
        markdown_path: str | None = None,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.compact_summary_to_dict(
                result,
                json_path=json_path,
                markdown_path=markdown_path,
            ),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def write_analysis_json(self, result: object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.result_to_json(result), encoding="utf-8")
        return path

    def write_analysis_markdown(self, result: object, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._markdown(self.result_to_dict(result)), encoding="utf-8")
        return path

    def _markdown(self, payload: dict[str, Any]) -> str:
        lines = [
            "# ML35 Multi-Symbol Feature/Regime Analysis",
            "",
            "## Summary",
            "",
            f"- symbols: `{payload.get('symbols')}`",
            f"- experiment_count: `{payload.get('experiment_count')}`",
            f"- candidate_count: `{payload.get('candidate_count')}`",
            f"- evaluated_candidate_count: `{payload.get('evaluated_candidate_count')}`",
            f"- failed_candidate_count: `{payload.get('failed_candidate_count')}`",
            f"- accepted_candidate_count: `{payload.get('accepted_candidate_count')}`",
            f"- rejected_candidate_count: `{payload.get('rejected_candidate_count')}`",
            f"- best symbol: `{payload.get('best_symbol')}`",
            f"- best candidate config: `{payload.get('best_candidate_config_id')}`",
            f"- best candidate score: `{payload.get('best_candidate_score')}`",
            f"- top failed gate: `{payload.get('top_failed_gate')}`",
            "",
            "## Symbol Comparison Table",
            "",
            "| Symbol | Score | Baseline Edge | Profit Factor | Walk-Forward PF | Real Diagnostics | Regime Features | Failed Gates |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for item in payload.get("symbol_results", []):
            lines.append(
                "| `{symbol}` | `{score}` | `{edge}` | `{profit_factor}` | `{walk_forward_pf}` | `{real_diag}` | `{regime_features}` | `{failed_gates}` |".format(
                    symbol=item.get("symbol"),
                    score=item.get("best_candidate_score"),
                    edge=item.get("baseline_edge"),
                    profit_factor=item.get("profit_factor"),
                    walk_forward_pf=item.get("walk_forward_profit_factor"),
                    real_diag=item.get("real_feature_diagnostics_used"),
                    regime_features=item.get("regime_features_attached"),
                    failed_gates=",".join(item.get("failed_gates", [])),
                )
            )
        if not payload.get("symbol_results"):
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |")

        lines.extend(
            [
                "",
                "## Best Symbol",
                "",
                f"- best symbol: `{payload.get('best_symbol')}`",
                f"- best score: `{payload.get('best_candidate_score')}`",
                "",
                "## Gate Failures By Symbol",
                "",
            ]
        )
        for item in payload.get("symbol_results", []):
            lines.append(f"- {item.get('symbol')}: `{item.get('failed_gates')}`")

        lines.extend(
            [
                "",
                "## Feature Version Check",
                "",
                f"- all_feature_version_fv2: `{payload.get('all_feature_version_fv2')}`",
                f"- feature_versions_by_symbol: `{dict(payload.get('feature_version_summary', {})).get('feature_versions_by_symbol')}`",
                "",
                "## Gap Training Safety Check",
                "",
                f"- all_gap_training_safe: `{payload.get('all_gap_training_safe')}`",
                f"- gap_severity_by_symbol: `{dict(payload.get('gap_training_safety_summary', {})).get('gap_severity_by_symbol')}`",
                f"- effective_gap_count_by_symbol: `{dict(payload.get('gap_training_safety_summary', {})).get('effective_gap_count_by_symbol')}`",
                "",
                "## Real Feature Diagnostics Check",
                "",
                f"- all_real_feature_diagnostics_used: `{payload.get('all_real_feature_diagnostics_used')}`",
                f"- symbols_missing_real_diagnostics: `{payload.get('symbols_missing_real_diagnostics')}`",
                "",
                "## Regime Integration Status",
                "",
                f"- symbols_missing_regime_features: `{payload.get('symbols_missing_regime_features')}`",
                f"- regime_training_applied_by_symbol: `{dict(payload.get('regime_integration_summary', {})).get('regime_training_applied_by_symbol')}`",
                f"- regime_specific_training_applied_any: `{dict(payload.get('regime_integration_summary', {})).get('regime_specific_training_applied_any')}`",
                "",
                "## Walk-Forward/Profit-Aware Summary",
                "",
                f"- walk_forward_summary: `{payload.get('walk_forward_summary')}`",
                f"- profit_aware_summary: `{payload.get('profit_aware_summary')}`",
                "",
                "## Collapse Summary",
                "",
                f"- collapse_summary: `{payload.get('collapse_summary')}`",
                f"- collapse_diagnostics_v2_by_symbol: `{ {item.get('symbol'): item.get('collapse_diagnostics_v2') for item in payload.get('symbol_results', [])} }`",
                "",
                "## Recommendations",
                "",
            ]
        )
        for recommendation in payload.get("recommendations", []):
            lines.append(f"- {recommendation}")

        lines.extend(
            [
                "",
                "## Safety",
                "",
                "- approved_for_live_trading: `False`",
                "- approved_for_auto_activation: `False`",
                "- orders_enabled: `False`",
                "- traders_core_connected: `False`",
                "",
            ]
        )
        return "\n".join(lines)
