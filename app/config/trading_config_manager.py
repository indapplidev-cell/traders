"""Canonical hot-reload owner for the mutable trading-parameter YAML."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, RLock, Thread
import time
from typing import Any

from app.config.trade_parameters import (
    CONFIG_PATH,
    ResolvedParameterSet,
    TradeParameters,
    load_trade_parameters,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class TradingConfigSnapshot:
    generation: int
    loaded_at: str
    activated_at: str | None
    activation_boundary_ms: int
    source_path: str
    config: TradeParameters
    resolved: ResolvedParameterSet


class TradingConfigManager:
    """Validate candidates off-loop and atomically swap at a 5m boundary.

    A manager owns one immutable active reference and at most one pending
    candidate.  Invalid or partial writes never replace the last-known-good
    reference.  Generation is the source file's mtime in nanoseconds, making
    independently running consumers of the same bind mount converge on the
    same monotonically increasing identity.
    """

    def __init__(
        self, path: Path = CONFIG_PATH, *, clock=time.time, monotonic=time.monotonic,
    ) -> None:
        self.path = Path(path)
        self._clock = clock
        self._monotonic = monotonic
        self._lock = RLock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._last_observed_signature: tuple[int, int] | None = None
        self._candidate_signature: tuple[int, int] | None = None
        self._candidate_first_seen = 0.0
        self._last_attempted_signature: tuple[int, int] | None = None
        self._last_detected_at: str | None = None
        self._last_validated_at: str | None = None
        self._last_error: str | None = None
        self._reload_status = "STARTING"
        self._pending: TradingConfigSnapshot | None = None
        self._active = self._load_initial()
        self._history: list[TradingConfigSnapshot] = []

    def _signature(self) -> tuple[int, int]:
        stat = self.path.stat()
        return stat.st_mtime_ns, stat.st_size

    def _load_initial(self) -> TradingConfigSnapshot:
        config = load_trade_parameters(self.path)
        signature = self._signature()
        now = _utc_now()
        generation = signature[0]
        resolved = replace(
            config.resolve_scalping_v2_parameter_set(),
            config_generation=generation,
            loaded_at=now,
            activated_at=now,
            source_path=str(self.path),
        )
        snapshot = TradingConfigSnapshot(
            generation=generation,
            loaded_at=now,
            activated_at=now,
            activation_boundary_ms=0,
            source_path=str(self.path),
            config=config,
            resolved=resolved,
        )
        self._last_observed_signature = signature
        self._last_attempted_signature = signature
        self._last_detected_at = now
        self._last_validated_at = now
        self._reload_status = "ACTIVE"
        return snapshot

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = Thread(
                target=self._watch_loop,
                name="trading-config-reloader",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=self._active.config.reload.poll_interval_seconds * 2 + 1)

    def _watch_loop(self) -> None:
        while not self._stop.wait(self._active.config.reload.poll_interval_seconds):
            self.poll_once()
            self.activate_due()

    def poll_once(self) -> bool:
        """Observe/stabilize one file state; return true when a candidate is ready."""
        now_monotonic = self._monotonic()
        try:
            signature = self._signature()
        except OSError as exc:
            with self._lock:
                self._last_detected_at = _utc_now()
                self._reload_status = "RELOAD_FAILED"
                self._last_error = f"CONFIG_SOURCE_UNAVAILABLE: {exc}"
                self._candidate_signature = None
            return False

        with self._lock:
            if signature == self._last_attempted_signature:
                return False
            if signature != self._candidate_signature:
                self._candidate_signature = signature
                self._candidate_first_seen = now_monotonic
                self._last_detected_at = _utc_now()
                self._reload_status = "CHANGE_DETECTED"
                self._last_error = None
                return False
            policy = self._active.config.reload
            stable_for = now_monotonic - self._candidate_first_seen
            if stable_for < policy.debounce_seconds + policy.stability_seconds:
                return False
            self._last_attempted_signature = signature

        try:
            config = load_trade_parameters(self.path)
            if self._signature() != signature:
                with self._lock:
                    self._candidate_signature = None
                    self._last_attempted_signature = None
                return False
            resolved = config.resolve_scalping_v2_parameter_set()
            # Validate the resolved candidate against the same runtime contract
            # used by the consumers before staging it.  YAML parsing alone is
            # insufficient: a candidate can be structurally valid but violate
            # profile invariants (for example the Scalping RR floor).
            from app.engine_orchestrator.trade_profile import resolve_trade_profile
            resolve_trade_profile(
                "trade-5m-v2", scalping_parameters=resolved.parameters
            )
        except Exception as exc:
            with self._lock:
                self._reload_status = "RELOAD_FAILED"
                self._last_error = f"{type(exc).__name__}: {exc}"
            return False

        loaded_at = _utc_now()
        period_ms = config.reload.activation_timeframe_seconds * 1000
        detected_ms = int(self._clock() * 1000)
        boundary_ms = ((detected_ms // period_ms) + 1) * period_ms
        with self._lock:
            generation = signature[0]
            if generation <= self._active.generation:
                generation = self._active.generation + 1
            resolved = replace(
                resolved,
                config_generation=generation,
                loaded_at=loaded_at,
                activated_at=None,
                source_path=str(self.path),
            )
            self._pending = TradingConfigSnapshot(
                generation=generation,
                loaded_at=loaded_at,
                activated_at=None,
                activation_boundary_ms=boundary_ms,
                source_path=str(self.path),
                config=config,
                resolved=resolved,
            )
            self._last_validated_at = loaded_at
            self._reload_status = "PENDING_SAFE_BOUNDARY"
            self._last_error = None
        return True

    def activate_due(self, boundary_ms: int | None = None) -> bool:
        """Atomically activate the pending candidate at/after its safe boundary."""
        effective_boundary = int(self._clock() * 1000) if boundary_ms is None else int(boundary_ms)
        with self._lock:
            pending = self._pending
            if pending is None or effective_boundary < pending.activation_boundary_ms:
                return False
            activated_at = _utc_now()
            resolved = replace(pending.resolved, activated_at=activated_at)
            self._history.append(self._active)
            if len(self._history) > 2016:
                self._history.pop(0)
            self._active = replace(
                pending,
                activated_at=activated_at,
                resolved=resolved,
            )
            self._pending = None
            self._last_observed_signature = self._last_attempted_signature
            self._reload_status = "ACTIVE"
            self._last_error = None
            return True

    def snapshot_for_cycle(self, boundary_ms: int) -> TradingConfigSnapshot:
        self.activate_due(boundary_ms)
        with self._lock:
            eligible = [
                snapshot
                for snapshot in (*self._history, self._active)
                if snapshot.activation_boundary_ms <= int(boundary_ms)
            ]
            return max(eligible, key=lambda item: item.activation_boundary_ms)

    def get_active_snapshot(self) -> TradingConfigSnapshot:
        with self._lock:
            return self._active

    def status(self) -> dict[str, Any]:
        with self._lock:
            active, pending = self._active, self._pending
            try:
                modified = datetime.fromtimestamp(
                    self.path.stat().st_mtime, timezone.utc
                ).isoformat()
            except OSError:
                modified = None
            definitions = {
                definition.id: key
                for key, definition in active.config.scalping_v2.parameter_sets.items()
            }
            parameters: dict[str, Any] = {}
            values = active.resolved.parameters.model_dump(mode="json")

            def visit(node: dict[str, Any], prefix: str = "") -> None:
                for key, value in node.items():
                    path = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, dict):
                        visit(value, path)
                        continue
                    owner = active.resolved.provenance.get(path)
                    overridden = owner is not None
                    source_path = f"profiles.trade-5m-v2.{path}"
                    source_file = "config/trading/trade_parameters.yaml"
                    layer = "BASE_PROFILE"
                    if path.startswith("risk."):
                        source_path = f"profiles.trade-5m-v2.{path.removeprefix('risk.')}"
                        source_file = "config/trading/risk_policy.yaml"
                        layer = "RISK_POLICY"
                    if overridden:
                        registry_key = definitions.get(owner, owner)
                        if path.startswith("risk."):
                            source_path = (
                                f"parameter_sets.{registry_key}.overrides."
                                f"{path.removeprefix('risk.')}"
                            )
                            layer = "RISK_PARAMETER_SET_OVERRIDE"
                        else:
                            source_path = (
                                f"scalping_v2.parameter_sets.{registry_key}.overrides.{path}"
                            )
                            layer = "PARAMETER_SET_OVERRIDE"
                    parameters[path] = {
                        "effective_value": value,
                        "source_file": source_file,
                        "source_yaml_path": source_path,
                        "source_layer": layer,
                        "override_status": overridden,
                    }

            visit(values)
            return {
                "config_source_path": active.source_path,
                "config_file_last_modified_at": modified,
                "config_last_detected_at": self._last_detected_at,
                "config_last_validated_at": self._last_validated_at,
                "config_last_activated_at": active.activated_at,
                "config_active_generation": active.generation,
                "config_pending_generation": None if pending is None else pending.generation,
                "config_pending_activation_boundary_ms": (
                    None if pending is None else pending.activation_boundary_ms
                ),
                "config_reload_status": self._reload_status,
                "config_reload_error": self._last_error,
                "active_parameter_set": active.resolved.id,
                "resolved_config_hash": active.resolved.resolved_config_hash,
                "parameters": parameters,
            }


_MANAGER: TradingConfigManager | None = None
_MANAGER_LOCK = RLock()


def get_trading_config_manager(*, start: bool = True) -> TradingConfigManager:
    global _MANAGER
    with _MANAGER_LOCK:
        if _MANAGER is None:
            _MANAGER = TradingConfigManager()
        if start:
            _MANAGER.start()
        return _MANAGER


__all__ = (
    "TradingConfigManager",
    "TradingConfigSnapshot",
    "get_trading_config_manager",
)
