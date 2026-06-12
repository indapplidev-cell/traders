from __future__ import annotations

import json
from pathlib import Path
from typing import Any

class TrainingPipelineReporter:
    """Serialize and export training pipeline results."""

    def result_to_dict(self, result) -> dict[str, Any]:
        return result.to_dict()

    def result_to_json(
        self,
        result,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.result_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def compact_summary_to_dict(self, result) -> dict[str, Any]:
        stage_count = len(result.stage_results)
        completed_stage_count = sum(
            int(item.status == "COMPLETED") for item in result.stage_results
        )
        failed_stage_count = sum(
            int(item.status == "FAILED") for item in result.stage_results
        )
        skipped_stage_count = sum(
            int(item.status in {"SKIPPED", "SKIPPED_NOT_AVAILABLE"})
            for item in result.stage_results
        )
        return {
            "status": result.status,
            "run_id": result.run_id,
            "symbol": result.symbol,
            "interval": result.interval,
            "start_date": result.start_date,
            "end_date": result.end_date,
            "dry_run": result.dry_run,
            "sample_mode": result.sample_mode,
            "stage_count": stage_count,
            "completed_stage_count": completed_stage_count,
            "failed_stage_count": failed_stage_count,
            "skipped_stage_count": skipped_stage_count,
            "quality_status": result.quality_summary.get("quality_status"),
            "approved_for_traders_core_integration": result.safety.get(
                "approved_for_traders_core_integration",
                False,
            ),
            "approved_for_live_trading": result.safety.get(
                "approved_for_live_trading",
                False,
            ),
            "approved_for_auto_activation": result.safety.get(
                "approved_for_auto_activation",
                False,
            ),
            "output_dir": result.output_dir,
            "log_path": result.log_path,
            "events_path": result.events_path,
            "json_report_path": result.json_report_path,
            "markdown_report_path": result.markdown_report_path,
        }

    def compact_summary_to_json(
        self,
        result,
        *,
        indent: int | None = 2,
    ) -> str:
        return json.dumps(
            self.compact_summary_to_dict(result),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def write_json_report(self, result) -> Path:
        path = Path(result.json_report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.result_to_json(result), encoding="utf-8")
        return path

    def write_markdown_report(self, result) -> Path:
        path = Path(result.markdown_report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._markdown_report(result), encoding="utf-8")
        return path

    def _markdown_report(self, result) -> str:
        lines = [
            f"# Training Pipeline Report - {result.run_id}",
            "",
            "## Run",
            "",
            f"- run_id: `{result.run_id}`",
            f"- status: `{result.status}`",
            f"- symbol: `{result.symbol}`",
            f"- interval: `{result.interval}`",
            f"- start_date: `{result.start_date}`",
            f"- end_date: `{result.end_date}`",
            f"- dry_run: `{str(result.dry_run).lower()}`",
            f"- sample_mode: `{str(result.sample_mode).lower()}`",
            "",
            "## Logs",
            "",
            f"- training_pipeline.log: `{result.log_path}`",
            f"- training_pipeline_events.jsonl: `{result.events_path}`",
            f"- training_pipeline_report.json: `{result.json_report_path}`",
            f"- training_pipeline_report.md: `{result.markdown_report_path}`",
            "",
            "## Stages",
            "",
            "| Stage | Status | Duration | Message |",
            "| --- | --- | --- | --- |",
        ]
        for stage in result.stage_results:
            lines.append(
                f"| `{stage.stage}` | `{stage.status}` | `{stage.duration_seconds:.2f}s` | {stage.message} |"
            )

        lines.extend(
            [
                "",
                "## Quality Summary",
                "",
                f"- quality_status: `{result.quality_summary.get('quality_status')}`",
                f"- approved_for_traders_core_integration: `{result.safety.get('approved_for_traders_core_integration')}`",
                f"- approved_for_live_trading: `{result.safety.get('approved_for_live_trading')}`",
                f"- approved_for_auto_activation: `{result.safety.get('approved_for_auto_activation')}`",
                "",
                "## Model Summary",
                "",
                f"- model_version: `{result.model_summary.get('model_version')}`",
                f"- model_accuracy: `{result.quality_summary.get('model_accuracy')}`",
                f"- collapse_detected: `{result.quality_summary.get('collapse_detected')}`",
                "",
                "## Baseline Summary",
                "",
                f"- baseline_accuracy: `{result.quality_summary.get('baseline_accuracy')}`",
                "",
                "## GatePolicy Replay Summary",
                "",
                f"- gate_policy_replay_status: `{result.gate_policy_replay_summary.get('gate_policy_replay_status')}`",
                f"- total_records: `{result.gate_policy_replay_summary.get('total_records')}`",
                "",
                "## Gap Quality",
                "",
                f"- gap_severity: `{result.gap_quality_summary.get('gap_severity')}`",
                f"- dataset_safe_for_training: `{result.gap_quality_summary.get('dataset_safe_for_training')}`",
                f"- gap_count: `{result.gap_quality_summary.get('gap_count')}`",
                "",
                "## Anti-Collapse",
                "",
                f"- collapse_detected: `{result.anti_collapse_summary.get('collapse_detected')}`",
                f"- collapse_type: `{result.anti_collapse_summary.get('collapse_type')}`",
                "",
                "## Candidate Selection",
                "",
                f"- candidate_status: `{result.candidate_selection_summary.get('candidate_status')}`",
                f"- candidate_decision: `{result.candidate_selection_summary.get('candidate_decision')}`",
                f"- failed_gates: `{result.candidate_selection_summary.get('failed_gates')}`",
                "",
                "## Label Config",
                "",
                f"- label_version: `{result.label_config_summary.get('label_version')}`",
                f"- horizon_candles: `{result.label_config_summary.get('horizon_candles')}`",
                "",
                "## Quality Gates",
                "",
                f"- passed_gates: `{result.quality_gates_summary.get('passed_gates')}`",
                f"- failed_gates: `{result.quality_gates_summary.get('failed_gates')}`",
                "",
                "## Safety",
                "",
                "- no live trading",
                "- no orders",
                "- no traders-core integration",
                "- no auto activation",
                "",
                "## Next Recommendations",
                "",
            ]
        )
        for item in result.next_recommendations:
            lines.append(f"- {item}")
        lines.append("")
        return "\n".join(lines)
