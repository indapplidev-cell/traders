"""Polling daemon for new closed 15-minute PostgreSQL windows."""

from __future__ import annotations

import random
import signal
import time
from dataclasses import asdict
from threading import Event
from typing import Any
from uuid import uuid4

from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_health import OrchestratorHealthReporter
from app.engine_orchestrator.orchestrator_state import OrchestratorState
from app.engine_orchestrator.orchestrator_status import FinalResult, OrchestratorHealthStatus, PipelineStatus
from app.engine_orchestrator.pipeline_result import PipelineResult, SafetyCounters


class OrchestratorDaemon:
    def __init__(self, config: OrchestratorConfig, detector: object, freshness_gate: object,
                 pipeline_runner: object, result_store: object, *,
                 daemon_instance_id: str | None = None,
                 health_reporter: OrchestratorHealthReporter | None = None) -> None:
        self.config = config
        self.detector = detector
        self.freshness_gate = freshness_gate
        self.pipeline_runner = pipeline_runner
        self.result_store = result_store
        self.daemon_instance_id = daemon_instance_id or f"orchestrator-{uuid4().hex[:12]}"
        self.health_reporter = health_reporter or OrchestratorHealthReporter(config.health_report_path)
        self.state = OrchestratorState()
        self._stop = Event()
        self._last_health_monotonic = 0.0
        self._hydrate_persisted_health()

    def _hydrate_persisted_health(self) -> None:
        latest = getattr(self.result_store, "get_latest", None)
        if callable(latest):
            for symbol in self.config.symbols:
                row = latest(symbol, self.config.primary_timeframe)
                if row is not None:
                    self.state.last_processed[symbol] = {
                        "symbol": symbol, "closed_until_ms": row.closed_until_ms,
                        "pipeline_status": row.status, "final_result": row.final_result,
                        "analysis_status": row.analysis_status, "setup_status": row.setup_status,
                        "strategy_status": row.strategy_status, "risk_status": row.risk_status,
                        "paper_status": row.paper_status,
                    }
        totals = getattr(self.result_store, "safety_totals", None)
        if callable(totals):
            self.state.safety_totals.update(totals())

    def request_stop(self, *_: object) -> None:
        self._stop.set()

    def install_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self.request_stop)
        signal.signal(signal.SIGTERM, self.request_stop)

    def _record(self, result: PipelineResult) -> None:
        if result.status == PipelineStatus.COMPLETED.value:
            self.state.completed_windows += 1
        elif result.status in {PipelineStatus.ERROR.value, PipelineStatus.MODULE_ERROR.value}:
            self.state.error_windows += 1
        else:
            self.state.skipped_windows += 1
        counters = asdict(result.safety_counters)
        for name, value in counters.items():
            self.state.safety_totals[name] = self.state.safety_totals.get(name, 0) + int(value)
        self.state.last_processed[result.symbol] = {
            "symbol": result.symbol, "closed_until_ms": result.closed_until_ms,
            "pipeline_status": result.status, "final_result": result.final_result,
            "analysis_status": result.analysis_status, "setup_status": result.setup_status,
            "strategy_status": result.strategy_status, "risk_status": result.risk_status,
            "paper_status": result.paper_status,
        }

    def _write_health(self, *, force: bool = False, status: str | None = None) -> None:
        now = time.monotonic()
        if not force and now - self._last_health_monotonic < self.config.health_report_interval_seconds:
            return
        payload = self.health_reporter.build(
            daemon_instance_id=self.daemon_instance_id, symbols=self.config.symbols,
            primary_timeframe=self.config.primary_timeframe, state=self.state,
            overall_status=status,
        )
        self.health_reporter.write(payload)
        self._last_health_monotonic = now

    def run_cycle(self, *, dry_run: bool = False) -> list[dict[str, Any]]:
        observations: list[dict[str, Any]] = []
        for symbol in self.config.symbols:
            if self._stop.is_set():
                break
            windows = self.detector.get_unprocessed_closed_windows(symbol)
            self.state.detected_windows += len(windows)
            for window in windows:
                if self._stop.is_set():
                    break
                freshness = self.freshness_gate.check(symbol, window.closed_until_ms)
                observation = {
                    "symbol": symbol, "timeframe": window.timeframe,
                    "closed_until_ms": window.closed_until_ms,
                    "freshness_status": freshness.status,
                    "freshness_reasons": list(freshness.reasons),
                }
                if dry_run:
                    observation["dry_run"] = True
                    observations.append(observation)
                    continue
                run_id = self.result_store.reserve(
                    symbol, window.timeframe, window.closed_until_ms,
                    daemon_instance_id=self.daemon_instance_id,
                    trigger_source=self.config.trigger_source,
                )
                if run_id is None:
                    self.state.duplicate_windows += 1
                    observation["pipeline_status"] = PipelineStatus.SKIPPED_DUPLICATE_WINDOW.value
                    observations.append(observation)
                    continue
                if not freshness.allowed:
                    result = PipelineResult(
                        symbol=symbol, primary_timeframe=window.timeframe,
                        closed_until_ms=window.closed_until_ms,
                        status=PipelineStatus.SKIPPED_FRESHNESS_NOT_OK.value,
                        final_result=FinalResult.NO_ACTION.value,
                        final_reason=";".join(freshness.reasons),
                        market_data_payload={"freshness": freshness.timeframe_statuses},
                    )
                else:
                    result = self.pipeline_runner.run(symbol, window.closed_until_ms)
                self.result_store.finish(run_id, result, freshness_status=freshness.status)
                self._record(result)
                observation.update({"pipeline_status": result.status, "final_result": result.final_result})
                observations.append(observation)
        self.state.cycles += 1
        self._write_health()
        return observations

    def run(self, *, continuous: bool, dry_run: bool = False,
            stop_after_cycles: int | None = None) -> list[dict[str, Any]]:
        if stop_after_cycles is not None and stop_after_cycles <= 0:
            raise ValueError("stop_after_cycles must be positive")
        all_observations: list[dict[str, Any]] = []
        backoff = self.config.initial_backoff_seconds
        while not self._stop.is_set():
            try:
                all_observations.extend(self.run_cycle(dry_run=dry_run))
                self.state.last_error = None
                backoff = self.config.initial_backoff_seconds
            except Exception as exc:
                self.state.last_error = f"{type(exc).__name__}: {exc}"
                self.state.error_windows += 1
                self._write_health(force=True, status=OrchestratorHealthStatus.ERROR.value)
                if not continuous:
                    raise
                self._stop.wait(backoff * random.uniform(0.8, 1.2))
                backoff = min(self.config.max_backoff_seconds, backoff * 2)
            if not continuous or (stop_after_cycles is not None and self.state.cycles >= stop_after_cycles):
                break
            self._stop.wait(self.config.poll_interval_seconds)
        final_status = OrchestratorHealthStatus.STOPPED.value if self._stop.is_set() else None
        self._write_health(force=True, status=final_status)
        return all_observations
