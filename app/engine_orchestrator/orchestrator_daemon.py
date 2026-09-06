"""Polling daemon for new and durable waiting 15-minute windows."""

from __future__ import annotations

import json
import logging
import random
import signal
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from threading import Event
from typing import Any, Callable
from uuid import uuid4

from app.engine_orchestrator.freshness_gate import FreshnessClassification
from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_health import OrchestratorHealthReporter
from app.engine_orchestrator.orchestrator_state import OrchestratorState
from app.engine_orchestrator.orchestrator_status import FinalResult, OrchestratorHealthStatus, PipelineStatus
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import ClaimedWindow, aware_utc, utc_from_ms
from app.engine_orchestrator.trade_profile import DEFAULT_TRADE_PROFILE_ID
from app.engine_orchestrator.profile_owner import ProfileOwnershipLostError


LOGGER = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrchestratorDaemon:
    def __init__(self, config: OrchestratorConfig, detector: object, freshness_gate: object,
                 pipeline_runner: object, result_store: object, *,
                 daemon_instance_id: str | None = None,
                 owner_guard: object | None = None,
                 health_reporter: OrchestratorHealthReporter | None = None,
                 cycle_maintenance: Callable[[], object] | None = None,
                 clock: Callable[[], datetime] = utc_now) -> None:
        self.config = config
        self.detector = detector
        self.freshness_gate = freshness_gate
        self.pipeline_runner = pipeline_runner
        self.result_store = result_store
        self.daemon_instance_id = daemon_instance_id or f"orchestrator-{uuid4().hex[:12]}"
        self.owner_guard = owner_guard
        self.health_reporter = health_reporter or OrchestratorHealthReporter(config.health_report_path)
        self.cycle_maintenance = cycle_maintenance
        self.clock = clock
        self.state = OrchestratorState()
        self._stop = Event()
        self._last_health_monotonic = 0.0
        self._hydrate_persisted_health()

    def _now(self) -> datetime:
        return aware_utc(self.clock())

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat().replace("+00:00", "Z") if value else None

    def _event(self, event: str, **values: object) -> None:
        LOGGER.info(json.dumps({
            "event": event,
            "daemon_instance_id": self.daemon_instance_id,
            **values,
        }, sort_keys=True, default=str))

    def _hydrate_persisted_health(self) -> None:
        latest = getattr(self.result_store, "get_latest", None)
        if callable(latest):
            for symbol in self.config.symbols:
                row = (
                    latest(symbol, self.config.primary_timeframe)
                    if self.config.trade_profile_id == DEFAULT_TRADE_PROFILE_ID
                    else latest(symbol, self.config.primary_timeframe,
                                trade_profile_id=self.config.trade_profile_id)
                )
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
            values = (
                totals()
                if self.config.trade_profile_id == DEFAULT_TRADE_PROFILE_ID
                else totals(trade_profile_id=self.config.trade_profile_id)
            )
            self.state.safety_totals.update(values)
        self._refresh_waiting_metrics()

    def _refresh_waiting_metrics(self) -> None:
        metrics = getattr(self.result_store, "waiting_metrics", None)
        if not callable(metrics):
            return
        kwargs = {"now": self._now()}
        if self.config.trade_profile_id != DEFAULT_TRADE_PROFILE_ID:
            kwargs["trade_profile_id"] = self.config.trade_profile_id
        values = metrics(**kwargs)
        for name, value in values.items():
            if isinstance(value, datetime):
                value = self._iso(value)
            setattr(self.state, name, value)

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
        self._refresh_waiting_metrics()
        payload = self.health_reporter.build(
            daemon_instance_id=self.daemon_instance_id, symbols=self.config.symbols,
            primary_timeframe=self.config.primary_timeframe, state=self.state,
            overall_status=status,
        )
        if self.owner_guard is not None:
            payload["profile_owner"] = asdict(self.owner_guard.status())
            payload["profile_owner"]["cursor"] = {
                symbol: value.get("closed_until_ms")
                for symbol, value in self.state.last_processed.items()
            }
            payload["profile_owner"]["last_completed_boundary"] = max(
                (
                    int(value.get("closed_until_ms") or 0)
                    for value in self.state.last_processed.values()
                ),
                default=None,
            )
        self.health_reporter.write(payload)
        self._last_health_monotonic = now

    def _freshness_skip_result(self, claim: ClaimedWindow, reason: str) -> PipelineResult:
        return PipelineResult(
            symbol=claim.symbol, primary_timeframe=claim.primary_timeframe,
            closed_until_ms=claim.closed_until_ms,
            trade_profile_id=claim.trade_profile_id,
            runtime_parameter_set_id=self.config.runtime_parameters.parameter_set_id,
            status=PipelineStatus.SKIPPED_FRESHNESS_NOT_OK.value,
            final_result=FinalResult.NO_ACTION.value, final_reason=reason,
        )

    def _process_claim(self, claim: ClaimedWindow) -> dict[str, Any]:
        now = self._now()
        freshness = self.freshness_gate.check(
            claim.symbol, claim.closed_until_ms,
            deadline_at=claim.freshness_deadline_at, now=now,
        )
        observation = {
            "run_id": claim.run_id, "symbol": claim.symbol,
            "timeframe": claim.primary_timeframe,
            "closed_until_ms": claim.closed_until_ms,
            "freshness_status": freshness.status,
            "freshness_classification": freshness.classification,
            "freshness_reasons": list(freshness.reasons),
        }
        payload = freshness.payload()
        if freshness.classification == FreshnessClassification.WAITING_RETRYABLE.value:
            next_retry = min(
                now + timedelta(seconds=self.config.freshness_retry_interval_seconds),
                claim.freshness_deadline_at,
            )
            changed = self.result_store.mark_waiting(
                claim, daemon_instance_id=self.daemon_instance_id,
                checked_at=now, next_retry_at=next_retry,
                reason_code=freshness.reason_code or "WAITING_FOR_REQUIRED_BOUNDARY",
                waiting_timeframes=freshness.waiting_timeframes, payload=payload,
            )
            if changed:
                event = "FRESHNESS_RETRY_SCHEDULED" if claim.was_waiting else "FRESHNESS_WAIT_STARTED"
                self._event(event, run_id=claim.run_id, symbol=claim.symbol,
                            closed_until_ms=claim.closed_until_ms,
                            next_retry_at=self._iso(next_retry), reason_code=freshness.reason_code)
            observation.update({
                "pipeline_status": PipelineStatus.WAITING_FOR_REQUIRED_BOUNDARY.value,
                "next_retry_at": self._iso(next_retry),
            })
            return observation

        if freshness.classification == FreshnessClassification.TERMINAL_NOT_READY.value:
            deadline_exceeded = freshness.reason_code == "FRESHNESS_DEADLINE_EXCEEDED"
            status = PipelineStatus.SKIPPED_FRESHNESS_NOT_OK.value
            changed = self.result_store.mark_terminal_freshness(
                claim, daemon_instance_id=self.daemon_instance_id, checked_at=now,
                status=status, reason_code=freshness.reason_code or freshness.status,
                waiting_timeframes=freshness.waiting_timeframes, payload=payload,
            )
            result = self._freshness_skip_result(claim, freshness.reason_code or freshness.status)
            if changed:
                self._record(result)
                self._event("FRESHNESS_DEADLINE_EXCEEDED" if deadline_exceeded else "FRESHNESS_TERMINAL_SKIP",
                            run_id=claim.run_id, symbol=claim.symbol,
                            closed_until_ms=claim.closed_until_ms,
                            reason_code=freshness.reason_code)
            observation.update({"pipeline_status": status, "final_result": result.final_result})
            return observation

        if not self.result_store.mark_running(
                claim, daemon_instance_id=self.daemon_instance_id,
                checked_at=now, payload=payload):
            observation["pipeline_status"] = PipelineStatus.SKIPPED_DUPLICATE_WINDOW.value
            return observation
        if claim.was_waiting:
            self._event("FRESHNESS_RECOVERED", run_id=claim.run_id, symbol=claim.symbol,
                        closed_until_ms=claim.closed_until_ms,
                        attempts=claim.freshness_attempt_count + 1)
        result = self.pipeline_runner.run(claim.symbol, claim.closed_until_ms)
        persisted = self.result_store.finish(claim.run_id, result, freshness_status="READY")
        if persisted:
            self._record(result)
        observation.update({"pipeline_status": result.status, "final_result": result.final_result})
        return observation

    def run_cycle(self, *, dry_run: bool = False) -> list[dict[str, Any]]:
        if self.owner_guard is not None:
            self.owner_guard.assert_active()
        if self.cycle_maintenance is not None:
            self.cycle_maintenance()
        observations: list[dict[str, Any]] = []
        if not dry_run:
            due_kwargs = {
                "daemon_instance_id": self.daemon_instance_id,
                "limit": self.config.waiting_batch_size,
                "now": self._now(),
            }
            if self.config.trade_profile_id != DEFAULT_TRADE_PROFILE_ID:
                due_kwargs["trade_profile_id"] = self.config.trade_profile_id
            due = self.result_store.claim_due_waiting(**due_kwargs)
            for claim in due:
                if self._stop.is_set():
                    break
                self._event("FRESHNESS_RETRY_CLAIMED", run_id=claim.run_id,
                            symbol=claim.symbol, closed_until_ms=claim.closed_until_ms)
                observations.append(self._process_claim(claim))

        for symbol in self.config.symbols:
            if self._stop.is_set():
                break
            windows = self.detector.get_unprocessed_closed_windows(symbol)
            self.state.detected_windows += len(windows)
            for window in windows:
                if self._stop.is_set():
                    break
                if dry_run:
                    freshness = self.freshness_gate.check(symbol, window.closed_until_ms)
                    observations.append({
                        "symbol": symbol, "timeframe": window.timeframe,
                        "closed_until_ms": window.closed_until_ms,
                        "freshness_status": freshness.status,
                        "freshness_reasons": list(freshness.reasons), "dry_run": True,
                    })
                    continue
                deadline = utc_from_ms(window.closed_until_ms) + timedelta(
                    seconds=self.config.freshness_grace_seconds)
                # A deployed legacy 15m retry worker predating profile-aware
                # claims may still scan every WAITING row.  Non-default
                # profiles therefore do not publish a retryable authoritative
                # row until freshness is ready.  The closed-window detector
                # will rediscover the unreserved boundary on the next cycle.
                # This keeps 5m ownership exclusive without changing or
                # restarting the production 15m worker.
                if self.config.trade_profile_id != DEFAULT_TRADE_PROFILE_ID:
                    preflight = self.freshness_gate.check(
                        symbol, window.closed_until_ms,
                        deadline_at=deadline, now=self._now(),
                    )
                    if (
                        preflight.classification
                        == FreshnessClassification.WAITING_RETRYABLE.value
                    ):
                        observations.append({
                            "symbol": symbol,
                            "timeframe": window.timeframe,
                            "closed_until_ms": window.closed_until_ms,
                            "freshness_status": preflight.status,
                            "freshness_classification": preflight.classification,
                            "freshness_reasons": list(preflight.reasons),
                            "pipeline_status": "DEFERRED_BEFORE_RESERVATION",
                        })
                        continue
                reserve_kwargs = {
                    "daemon_instance_id": self.daemon_instance_id,
                    "trigger_source": self.config.trigger_source,
                    "freshness_deadline_at": deadline,
                }
                if self.config.trade_profile_id != DEFAULT_TRADE_PROFILE_ID:
                    reserve_kwargs["trade_profile_id"] = self.config.trade_profile_id
                run_id = self.result_store.reserve(
                    symbol, window.timeframe, window.closed_until_ms,
                    **reserve_kwargs,
                )
                if run_id is None:
                    self.state.duplicate_windows += 1
                    observations.append({
                        "symbol": symbol, "timeframe": window.timeframe,
                        "closed_until_ms": window.closed_until_ms,
                        "pipeline_status": PipelineStatus.SKIPPED_DUPLICATE_WINDOW.value,
                    })
                    continue
                observations.append(self._process_claim(self.result_store.get_claim(run_id)))
        self.state.cycles += 1
        self._write_health()
        if self.owner_guard is not None:
            # Health/cursor reads share the pinned owner session.  Re-verify
            # after every cycle so ownership loss is fenced after mutation and
            # the read-only transaction is ended before the polling wait.
            self.owner_guard.assert_active()
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
            except ProfileOwnershipLostError as exc:
                self.state.last_error = f"{type(exc).__name__}: {exc}"
                self.state.error_windows += 1
                self._stop.set()
                self._write_health(force=True, status=OrchestratorHealthStatus.ERROR.value)
                raise
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
