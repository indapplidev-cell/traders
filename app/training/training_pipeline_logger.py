from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrainingPipelineLogPaths:
    run_dir: Path
    log_path: Path
    events_path: Path
    json_report_path: Path
    markdown_report_path: Path


class TrainingPipelineLogger:
    """Write human-readable and JSONL logs for training pipeline runs."""

    def __init__(
        self,
        *,
        run_id: str,
        output_dir: Path | str = Path("reports/training_pipeline_runs"),
    ) -> None:
        self._run_id = run_id
        self._output_dir = Path(output_dir)
        self._run_dir = self._output_dir / run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)
        self._log_path = self._run_dir / "training_pipeline.log"
        self._events_path = self._run_dir / "training_pipeline_events.jsonl"
        self._json_report_path = self._run_dir / "training_pipeline_report.json"
        self._markdown_report_path = self._run_dir / "training_pipeline_report.md"

    @property
    def paths(self) -> TrainingPipelineLogPaths:
        return TrainingPipelineLogPaths(
            run_dir=self._run_dir,
            log_path=self._log_path,
            events_path=self._events_path,
            json_report_path=self._json_report_path,
            markdown_report_path=self._markdown_report_path,
        )

    def pipeline_started(self, *, message: str, data: dict[str, Any] | None = None) -> None:
        self._write_event(
            stage="pipeline",
            event="pipeline_started",
            status="running",
            message=message,
            duration_seconds=None,
            data=data or {},
            level="INFO",
        )

    def pipeline_completed(
        self,
        *,
        status: str,
        message: str,
        duration_seconds: float | None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self._write_event(
            stage="pipeline",
            event="pipeline_completed",
            status=status,
            message=message,
            duration_seconds=duration_seconds,
            data=data or {},
            level="INFO",
        )

    def pipeline_failed(
        self,
        *,
        message: str,
        duration_seconds: float | None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self._write_event(
            stage="pipeline",
            event="pipeline_failed",
            status="FAILED",
            message=message,
            duration_seconds=duration_seconds,
            data=data or {},
            level="ERROR",
        )

    def stage_started(
        self,
        *,
        stage: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self._write_event(
            stage=stage,
            event="stage_started",
            status="RUNNING",
            message=message,
            duration_seconds=None,
            data=data or {},
            level="INFO",
        )

    def stage_completed(
        self,
        *,
        stage: str,
        status: str,
        message: str,
        duration_seconds: float | None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self._write_event(
            stage=stage,
            event="stage_completed",
            status=status,
            message=message,
            duration_seconds=duration_seconds,
            data=data or {},
            level="INFO",
        )

    def stage_failed(
        self,
        *,
        stage: str,
        message: str,
        duration_seconds: float | None,
        data: dict[str, Any] | None = None,
    ) -> None:
        self._write_event(
            stage=stage,
            event="stage_failed",
            status="FAILED",
            message=message,
            duration_seconds=duration_seconds,
            data=data or {},
            level="ERROR",
        )

    def _write_event(
        self,
        *,
        stage: str,
        event: str,
        status: str,
        message: str,
        duration_seconds: float | None,
        data: dict[str, Any],
        level: str,
    ) -> None:
        timestamp = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
        event_payload = {
            "timestamp": timestamp,
            "run_id": self._run_id,
            "stage": stage,
            "event": event,
            "status": status,
            "message": message,
            "duration_seconds": duration_seconds,
            "data": data,
        }
        with self._events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event_payload, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

        human_timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        duration_part = (
            f" duration={duration_seconds:.2f}s" if duration_seconds is not None else ""
        )
        details_part = ""
        if data:
            serialized = " ".join(f"{key}={value}" for key, value in data.items())
            details_part = f" {serialized}"
        line = (
            f"[{human_timestamp}] [{level}] [{stage}] run_id={self._run_id} "
            f"status={status} event={event}{duration_part} message={message}{details_part}"
        )
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
