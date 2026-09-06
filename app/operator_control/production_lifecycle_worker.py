"""Bounded production PAPER lifecycle continuation for the first canary.

The worker consumes only persisted closed 1m candles and advances at most one
atomic lifecycle stage per poll.  It has no exchange-order authority and is
hard-bound to the already armed one-command/one-position first canary.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256

from app.engine_execution.paper_idempotency import (
    simulated_close_fill_id,
    simulated_fill_id,
)
from app.engine_paper.controlled_worker import (
    PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION,
    PaperControlledLifecycleWorker,
    PaperLifecycleCycleRequest,
    PaperLifecycleCycleScope,
    PaperLifecycleState,
    SqlAlchemyPaperLifecycleGraphLoader,
    classify_paper_lifecycle_state,
)
from app.engine_paper.exit_evaluation_service import PaperExitEvaluationRequest
from app.engine_paper.continuous_authority import PaperContinuousAuthorityStore
from app.engine_paper.exit_evaluator import (
    PAPER_EXIT_EVALUATION_POLICY_ID,
    PaperSafetyExitDirective,
)
from app.engine_paper.fill_causal_boundary import PAPER_FILL_CAUSAL_BOUNDARY_VERSION
from app.engine_paper.fill_simulator import PaperFillCandle, PaperFillRole
from app.engine_paper.first_canary_correlation import SqlAlchemyPaperFirstCanaryStore
from app.engine_paper.order_execution_service import (
    PaperCloseExecutionRequest,
    PaperEntryExecutionRequest,
)
from app.engine_paper.scalping_paper_runner import read_binance_commission_snapshot
from app.engine_safety.paper_domain import PaperPositionState
from app.engine_paper.production_market_data import (
    PaperProductionMarketDataInputAdapter,
    PaperProductionMarketDataRequest,
    PaperProductionMarketDataScope,
    PaperProductionMarketDataReadiness,
)
from app.engine_safety.paper_domain import ExecutionMode
from app.engine_safety.paper_production_control import (
    MutationPrerequisites,
    MutationStage,
    PaperProductionMutationSafetyGate,
    PaperProductionMutationTarget,
    PaperProductionSafetyControl,
    PersistentState,
    ReasonCode,
    SafetyControlError,
)

from .continuation_worker import PostgresCanaryContinuationLock
from .production_executor import (
    ExistingCanaryRuntimeReadiness,
    SCALPING_V2_REFINEMENT_SIMULATION_POLICY_ID,
    _foundation_policy,
)
from .schemas import PaperOperatorRecoveryCloseDecision


# Uvicorn owns the production stderr handler; using its error logger keeps the
# structured canary trail in ``docker logs`` without adding a second handler.
LOGGER = logging.getLogger("uvicorn.error")
DEFAULT_POLL_SECONDS = 10.0
MIN_POLL_SECONDS = 5.0
MAX_POLL_SECONDS = 60.0
MAX_CANDLES = 512


def lifecycle_poll_seconds() -> float:
    raw = os.environ.get("TRADERS_FIRST_CANARY_LIFECYCLE_POLL_SECONDS")
    if raw is None:
        return DEFAULT_POLL_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_POLL_SECONDS
    return value if MIN_POLL_SECONDS <= value <= MAX_POLL_SECONDS else DEFAULT_POLL_SECONDS


def _id(canary_id: str, role: str, *, continuous: bool = False) -> str:
    digest = sha256(f"{canary_id}|{role}".encode("ascii")).hexdigest()
    authority = "continuous" if continuous else "first-canary"
    return f"paper:{authority}:{role}:{digest}"


def _at(boundary_ms: int) -> datetime:
    return datetime.fromtimestamp(boundary_ms / 1000, tz=timezone.utc)


def _fill_candle(value) -> PaperFillCandle:
    return PaperFillCandle(
        symbol=value.symbol,
        timeframe=value.timeframe,
        open_time_ms=value.open_time_ms,
        close_boundary_ms=value.close_time_ms + 1,
        open_price=value.open,
        high_price=value.high,
        low_price=value.low,
        close_price=value.close,
        is_closed=value.is_closed,
        observed_closed_until_ms=value.close_time_ms + 1,
    )


def _entry_fill_window_missed(entry_order, selected_candle: PaperFillCandle) -> bool:
    """Reject a fill whose deterministic event time predates order creation."""

    return entry_order.updated_at > _at(selected_candle.close_boundary_ms)


def _safe_event(event: str, **fields: object) -> None:
    LOGGER.info(json.dumps({"event": event, **fields}, sort_keys=True, default=str))


class ProductionPaperFirstCanaryLifecycleWorker:
    """Poll and advance one existing first-canary lifecycle, one stage at a time."""

    def __init__(
        self,
        *,
        control: PaperProductionSafetyControl,
        canary_store: SqlAlchemyPaperFirstCanaryStore,
        graph_loader: SqlAlchemyPaperLifecycleGraphLoader,
        lifecycle_worker: PaperControlledLifecycleWorker,
        market_data: PaperProductionMarketDataInputAdapter,
        mutation_safety_gate: PaperProductionMutationSafetyGate,
        runtime_readiness,
        lock: PostgresCanaryContinuationLock,
        readonly_base_url: str,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        continuous_store: PaperContinuousAuthorityStore | None = None,
        opportunity_registry: object | None = None,
        outcome_diagnostics: object | None = None,
        stale_position_shadow: object | None = None,
    ) -> None:
        if not MIN_POLL_SECONDS <= poll_seconds <= MAX_POLL_SECONDS:
            raise ValueError("FIRST_CANARY_LIFECYCLE_POLL_INTERVAL_INVALID")
        self._control = control
        self._canary_store = canary_store
        self._graph_loader = graph_loader
        self._worker = lifecycle_worker
        self._market_data = market_data
        self._mutation_safety_gate = mutation_safety_gate
        self._runtime_readiness = runtime_readiness
        self._lock = lock
        self._readonly_base_url = readonly_base_url.rstrip("/")
        self.poll_seconds = float(poll_seconds)
        self._continuous_store = continuous_store
        self._opportunity_registry = opportunity_registry
        self._outcome_diagnostics = outcome_diagnostics
        self._stale_position_shadow = stale_position_shadow
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ticks = 0
        self._last_result = "NOT_STARTED"

    @property
    def active(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def ticks(self) -> int:
        return self._ticks

    @property
    def last_result(self) -> str:
        return self._last_result

    def start(self) -> None:
        if self.active:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="paper-first-canary-lifecycle", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=min(self.poll_seconds + 1.0, 15.0))
        self._thread = None

    def _snapshot(self, symbol: str, canary_id: str, *, continuous: bool = False):
        result = self._market_data.read(PaperProductionMarketDataRequest(
            scope=PaperProductionMarketDataScope(
                symbols=(symbol,), timeframes=("1m",), candles_per_timeframe=MAX_CANDLES
            ),
            request_id=_id(canary_id, "lifecycle-market-snapshot", continuous=continuous),
        ))
        if result.readiness is not PaperProductionMarketDataReadiness.READY or result.data is None:
            return None, result.outcome.value
        snapshot = result.data.snapshots[0]
        candles = dict(snapshot.candles)["1m"]
        return tuple(_fill_candle(value) for value in candles), "READY"

    def _finalize(self, canary, state) -> str:
        """Reconcile a close; only the historical first canary auto-disables."""

        disabled = state
        continuous = getattr(canary, "authority_mode", "FIRST_CANARY_HISTORICAL") == "CONTINUOUS"
        if not continuous and state.state is PersistentState.ARMED:
            disabled = self._control.transition(
                PersistentState.DISABLED,
                expected_generation=state.generation,
                reason=ReasonCode.PREPARATION_CANARY,
                acknowledge=True,
            )
        elif not continuous and state.state is not PersistentState.DISABLED:
            return "SAFE_FAILURE:FINALIZATION_CONTROL_NOT_DISABLED"
        elif continuous and state.state is not PersistentState.CONTINUOUS_ARMED:
            return "SAFE_FAILURE:CONTINUOUS_CONTROL_NOT_ARMED"
        report_available = False
        paper_status = "UNHEALTHY"
        accounting_status = "UNHEALTHY"
        report = None
        try:
            position_id = urllib.parse.quote(canary.position_id or "", safe=":._-")
            with urllib.request.urlopen(
                f"{self._readonly_base_url}/api/v1/paper/trades/{position_id}/report",
                timeout=5,
            ) as response:
                report_document = json.loads(response.read())
            with urllib.request.urlopen(
                f"{self._readonly_base_url}/api/v1/paper/reconciliation", timeout=5
            ) as response:
                reconciliation_document = json.loads(response.read())
            report = report_document.get("data")
            reconciliation = reconciliation_document.get("data") or {}
            report_available = isinstance(report, dict)
            paper_status = str(
                (reconciliation.get("paper_reconciliation") or {}).get("status", "UNHEALTHY")
            )
            accounting_status = str(
                (reconciliation.get("accounting_reconciliation") or {}).get("status", "UNHEALTHY")
            )
        except Exception as error:
            _safe_event("paper_canary_finalization_read_fault", error_type=type(error).__name__)
        healthy = report_available and paper_status == "HEALTHY" and accounting_status == "HEALTHY"
        if continuous:
            if self._continuous_store is None:
                return "SAFE_FAILURE:CONTINUOUS_CONTROL_NOT_CONFIGURED"
            try:
                self._continuous_store.record_close(
                    position_id=canary.position_id or "",
                    realized_pnl=Decimal(str((report or {}).get("net_pnl", "0"))),
                    reconciliation_healthy=healthy,
                )
            except Exception as error:
                _safe_event("paper_continuous_close_reconciliation_fault", error_type=type(error).__name__)
                return "SAFE_FAILURE:CONTINUOUS_CLOSE_RECONCILIATION_FAILED"
        final = self._canary_store.refresh_terminal(
            canary.canary_id,
            control_state=disabled.state.value,
            control_generation=disabled.generation,
            report_available=report_available,
            paper_reconciliation_status=paper_status,
            accounting_reconciliation_status=accounting_status,
            checked_at=datetime.now(timezone.utc),
        )
        _safe_event(
            "paper_execution_cycle_finalized", canary_id=canary.canary_id,
            authority_mode=getattr(canary, "authority_mode", "FIRST_CANARY_HISTORICAL"),
            command_id=canary.command_id, position_id=canary.position_id,
            control_generation=disabled.generation, canary_state=final.state.value,
            report_available=report_available, paper_reconciliation_status=paper_status,
            accounting_reconciliation_status=accounting_status,
            total_fees=None if not isinstance(report, dict) else report.get("total_fees"),
            net_pnl=None if not isinstance(report, dict) else report.get("net_pnl"),
            roi_percent=None if not isinstance(report, dict) else report.get("roi_percent"),
        )
        return f"FINALIZED:{final.state.value}"

    @staticmethod
    def _orders(graph):
        return {node.role: node.order for node in graph.orders}

    def _entry_cycle(self, canary_id: str, graph, candles, *, continuous: bool = False):
        command = graph.command
        entry = self._orders(graph)["ENTRY"]
        refinement_authoritative = (
            command.simulation_policy_id == SCALPING_V2_REFINEMENT_SIMULATION_POLICY_ID
        )
        eligible = tuple(
            value for value in candles
            if value.open_time_ms >= command.closed_until_ms
            and (
                not refinement_authoritative
                or _at(value.close_boundary_ms) >= entry.updated_at
            )
        )
        if not eligible:
            return None, "WAITING_FOR_ENTRY_CANDLE"
        selected = eligible[0]
        if _entry_fill_window_missed(entry, selected) and not refinement_authoritative:
            authority = "CONTINUOUS" if continuous else "FIRST_CANARY"
            reason = f"{authority}_ENTRY_FILL_WINDOW_MISSED"
            self._canary_store.fail_safe(canary_id, reason)
            _safe_event(
                "paper_entry_fill_window_missed",
                canary_id=canary_id,
                command_id=command.command_id,
                order_id=entry.order_id,
                order_updated_at=entry.updated_at.isoformat(),
                selected_candle_close_boundary_ms=selected.close_boundary_ms,
                reason=reason,
            )
            return None, f"SAFE_FAILURE:{reason}"
        policy = _foundation_policy(command.simulation_policy_id)
        fill_id = simulated_fill_id(
            contract_version=policy.contract_version,
            order_id=entry.order_id,
            fill_role=PaperFillRole.ENTRY.value,
            source_open_time_ms=selected.open_time_ms,
            source_close_boundary_ms=selected.close_boundary_ms,
            simulation_policy_id=policy.simulation_policy_id,
            slippage_policy_id=policy.slippage_policy_id,
            fee_policy_id=policy.fee_policy_id,
            latency_policy_id=policy.latency_policy_id,
        )
        correlation = graph.journal[0].correlation_id
        request = PaperEntryExecutionRequest(
            command_id=command.command_id, order_id=entry.order_id,
            expected_order_version=entry.version, fill_role=PaperFillRole.ENTRY,
            candidate_candles=(selected,),
            market_snapshot_closed_until_ms=selected.close_boundary_ms,
            simulation_policy=policy, price_quantum=policy.price_quantum,
            fee_quantum=policy.fee_quantum, quote_asset="USDT", fill_id=fill_id,
            order_event_id=_id(canary_id, "entry-filled-event", continuous=continuous),
            position_event_id=_id(canary_id, "position-opened-event", continuous=continuous),
            journal_entry_ids=(
                _id(canary_id, "entry-filled-journal", continuous=continuous),
                _id(canary_id, "position-opened-journal", continuous=continuous),
            ),
            correlation_id=correlation, causation_id=command.command_id,
            operation_at=_at(selected.close_boundary_ms),
            position_id=_id(canary_id, "position", continuous=continuous),
        )
        return self._cycle(canary_id, graph, continuous=continuous, entry_execution_request=request), "READY"

    def _exit_cycle(
        self,
        canary_id: str,
        graph,
        candles,
        *,
        continuous: bool = False,
        safety_directive: PaperSafetyExitDirective | None = None,
    ):
        command, position, cursor = graph.command, graph.positions[0], graph.cursors[0]
        eligible = tuple(value for value in candles if value.open_time_ms >= cursor.last_evaluated_closed_until_ms)
        if not eligible:
            return None, "WAITING_FOR_EXIT_CANDLE"
        correlation = graph.journal[0].correlation_id
        close_order_id = _id(canary_id, "close-order", continuous=continuous)
        request = PaperExitEvaluationRequest(
            position_id=position.position_id, expected_position_version=position.version,
            cursor_id=cursor.cursor_id, expected_cursor_version=cursor.version,
            expected_cursor_from_closed_until_ms=cursor.last_evaluated_closed_until_ms,
            source_command_id=command.command_id, entry_order_id=position.entry_order_id,
            entry_fill_id=position.entry_fill_id, candles=eligible,
            market_snapshot_closed_until_ms=eligible[-1].close_boundary_ms,
            safety_directive=safety_directive, evaluation_policy_id=PAPER_EXIT_EVALUATION_POLICY_ID,
            execution_mode=ExecutionMode.PAPER, explicit_paper_authorization=True,
            exit_decision_id=_id(canary_id, "exit-decision", continuous=continuous), close_order_id=close_order_id,
            exit_event_id=_id(canary_id, "exit-event", continuous=continuous),
            close_order_created_event_id=_id(canary_id, "close-created-event", continuous=continuous),
            close_order_validated_event_id=_id(canary_id, "close-validated-event", continuous=continuous),
            close_order_opened_event_id=_id(canary_id, "close-opened-event", continuous=continuous),
            journal_entry_ids=(
                _id(canary_id, "close-created-event", continuous=continuous),
                _id(canary_id, "close-validated-event", continuous=continuous),
                _id(canary_id, "close-opened-event", continuous=continuous),
                _id(canary_id, "exit-event", continuous=continuous),
            ),
            close_execution_fill_id=_id(canary_id, "close-fill-reservation", continuous=continuous),
            close_execution_order_event_id=_id(canary_id, "close-filled-event", continuous=continuous),
            close_execution_position_event_id=_id(canary_id, "position-closed-event", continuous=continuous),
            close_execution_journal_entry_ids=(
                _id(canary_id, "close-filled-journal", continuous=continuous),
                _id(canary_id, "position-closed-journal", continuous=continuous),
            ),
            price_quantum=_foundation_policy(command.simulation_policy_id).price_quantum,
            fee_quantum=_foundation_policy(command.simulation_policy_id).fee_quantum,
            quote_asset="USDT",
            # The close order is caused by the first evaluated boundary, not by
            # the later observation watermark.  Dating it at the watermark can
            # make a valid next-candle fill appear to precede its order when a
            # restart processes several accumulated candles at once.
            created_at=_at(eligible[0].close_boundary_ms), correlation_id=correlation,
            causation_id=position.position_id,
        )
        return self._cycle(canary_id, graph, continuous=continuous, exit_evaluation_request=request), "READY"

    def _close_cycle(self, canary_id: str, graph, candles, *, continuous: bool = False):
        command, position, decision = graph.command, graph.positions[0], graph.exit_decisions[0]
        close_order = self._orders(graph)["EXIT"]
        close_order_ready_ms = int(close_order.updated_at.timestamp() * 1000)
        eligible = tuple(
            value for value in candles
            if value.open_time_ms >= max(decision.source_closed_until_ms, close_order_ready_ms)
        )
        if not eligible:
            return None, "WAITING_FOR_CLOSE_CANDLE"
        selected = eligible[0]
        policy = _foundation_policy(command.simulation_policy_id)
        fill_id = simulated_close_fill_id(
            fill_contract_version=PAPER_FILL_CAUSAL_BOUNDARY_VERSION,
            order_id=close_order.order_id, exit_decision_id=decision.exit_decision_id,
            exit_source_closed_until_ms=decision.source_closed_until_ms,
            source_open_time_ms=selected.open_time_ms,
            source_close_boundary_ms=selected.close_boundary_ms,
            simulation_policy_id=policy.simulation_policy_id,
            slippage_policy_id=policy.slippage_policy_id,
            fee_policy_id=policy.fee_policy_id,
            latency_policy_id=policy.latency_policy_id,
        )
        correlation = graph.journal[0].correlation_id
        request = PaperCloseExecutionRequest(
            command_id=command.command_id, order_id=close_order.order_id,
            expected_order_version=close_order.version, position_id=position.position_id,
            expected_position_version=position.version,
            exit_decision_id=decision.exit_decision_id, fill_role=PaperFillRole.CLOSE,
            candidate_candles=(selected,),
            market_snapshot_closed_until_ms=selected.close_boundary_ms,
            simulation_policy=policy, price_quantum=policy.price_quantum,
            fee_quantum=policy.fee_quantum, quote_asset="USDT", fill_id=fill_id,
            order_event_id=_id(canary_id, "close-filled-event", continuous=continuous),
            position_event_id=_id(canary_id, "position-closed-event", continuous=continuous),
            journal_entry_ids=(
                _id(canary_id, "close-filled-journal", continuous=continuous),
                _id(canary_id, "position-closed-journal", continuous=continuous),
            ),
            correlation_id=correlation, causation_id=decision.exit_decision_id,
            operation_at=_at(selected.close_boundary_ms),
        )
        return self._cycle(canary_id, graph, continuous=continuous, close_execution_request=request), "READY"

    @staticmethod
    def _cycle(canary_id: str, graph, *, continuous: bool = False, **stage_request) -> PaperLifecycleCycleRequest:
        return PaperLifecycleCycleRequest(
            cycle_id=_id(canary_id, "lifecycle-cycle", continuous=continuous),
            contract_version=PAPER_LIFECYCLE_CYCLE_CONTRACT_VERSION,
            execution_mode=ExecutionMode.PAPER, explicit_paper_authorization=True,
            scope=PaperLifecycleCycleScope.ADVANCE_ONE_LIFECYCLE_STEP, max_stages=1,
            created_at=datetime.now(timezone.utc),
            correlation_id=graph.journal[0].correlation_id,
            command_id=graph.command.command_id,
            **stage_request,
        )

    def recovery_close_paper_position(
        self, request_id: str, position_id: str
    ) -> PaperOperatorRecoveryCloseDecision:
        """Close one exact OPEN PAPER position at current causal observations.

        This is an authenticated operator entry point into the same atomic
        evaluation and close-execution services used by mandatory exits. It
        never mutates position rows directly and never backdates the fill.
        """

        canary = self._canary_store.current()
        if canary is None or canary.command_id is None:
            raise ValueError("POSITION_NOT_FOUND")
        if canary.position_id != position_id:
            raise ValueError("POSITION_NOT_FOUND")
        with self._lock.acquire(canary.canary_id) as claimed:
            if not claimed:
                raise ValueError("RECOVERY_CLOSE_BUSY")
            canary = self._canary_store.get(canary.canary_id)
            if canary is None or canary.position_id != position_id:
                raise ValueError("POSITION_NOT_FOUND")
            state = self._control.read_authoritative()
            if (
                state.state is not PersistentState.CONTINUOUS_ARMED
                or canary.authority_mode != "CONTINUOUS"
                or state.generation != canary.current_control_generation
            ):
                raise ValueError("RECOVERY_CLOSE_CONTROL_NOT_ARMED")
            graph = self._graph_loader.load(canary.command_id)
            lifecycle = classify_paper_lifecycle_state(graph)
            if lifecycle is PaperLifecycleState.POSITION_CLOSED:
                position = graph.positions[0]
                return PaperOperatorRecoveryCloseDecision(
                    request_id=request_id,
                    accepted=True,
                    executed=False,
                    position_id=position_id,
                    state_before="CLOSED",
                    state_after="CLOSED",
                    close_reason="OPERATOR_RECOVERY_CLOSE",
                    exit_fill_id=position.exit_fill_id,
                    exit_price=(
                        None if position.average_exit_price is None
                        else format(position.average_exit_price, "f")
                    ),
                    exit_fee=format(position.exit_fees, "f"),
                )
            if lifecycle is not PaperLifecycleState.POSITION_OPEN_CURSOR_READY:
                raise ValueError("RECOVERY_CLOSE_POSITION_NOT_OPEN")
            readiness: ExistingCanaryRuntimeReadiness = self._runtime_readiness()
            if not all((
                readiness.market_data_ready,
                readiness.backup_pitr_pass,
                readiness.live_disabled,
            )):
                raise ValueError("RECOVERY_CLOSE_SAFETY_READINESS_DENIED")
            commission_load = read_binance_commission_snapshot(graph.command.symbol)
            commission = commission_load.snapshot
            policy = _foundation_policy(graph.command.simulation_policy_id)
            if (
                commission is None
                or Decimal(str(commission.exit_commission_bps)) != policy.fee_bps
            ):
                raise ValueError("RECOVERY_CLOSE_CURRENT_COMMISSION_NOT_READY")
            candles, market = self._snapshot(
                graph.command.symbol, canary.canary_id, continuous=True
            )
            if candles is None:
                raise ValueError(f"RECOVERY_CLOSE_MARKET_DATA_{market}")
            cursor = graph.cursors[0]
            eligible = tuple(
                candle for candle in candles
                if candle.open_time_ms >= cursor.last_evaluated_closed_until_ms
            )
            if len(eligible) < 2:
                raise ValueError("RECOVERY_CLOSE_CURRENT_CANDLE_PAIR_NOT_READY")
            trigger_candle = eligible[-2]
            now = datetime.now(timezone.utc)
            directive = PaperSafetyExitDirective(
                directive_id=_id(canary.canary_id, "operator-recovery-directive", continuous=True),
                version=1,
                position_id=position_id,
                symbol=graph.command.symbol,
                side=graph.positions[0].side,
                effective_closed_until_ms=trigger_candle.close_boundary_ms,
                issued_at=now,
                valid_until_ms=int((now + timedelta(minutes=5)).timestamp() * 1000),
                final_safety_authorization=True,
                reason="RECOVERY_CLOSE_AFTER_MISSED_STOP",
                correlation_id=graph.journal[0].correlation_id,
                causation_id=request_id,
                mode=ExecutionMode.PAPER,
                recovery_close=True,
            )
            cycle, code = self._exit_cycle(
                canary.canary_id,
                graph,
                candles,
                continuous=True,
                safety_directive=directive,
            )
            if cycle is None:
                raise ValueError(f"RECOVERY_CLOSE_{code}")
            target = PaperProductionMutationTarget(
                environment=canary.environment,
                mode=canary.mode,
                symbol=graph.command.symbol,
                candidate_identity=graph.command.risk_decision_id,
                current_generation=state.generation,
                new_commands_before=canary.command_count,
                open_positions_before=canary.position_count,
            )
            prerequisites = MutationPrerequisites(
                market_data_ready=True,
                approval_candidate_eligible=True,
                backup_pitr_pass=True,
                paper_target_authorized=True,
                live_disabled=True,
            )
            with self._mutation_safety_gate.authorize_mutation(
                MutationStage.EXIT_EVALUATION_MUTATION, target, prerequisites
            ):
                prepared = self._worker.run_cycle(cycle)
            if prepared.final_lifecycle_state is not PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN:
                raise ValueError(f"RECOVERY_CLOSE_PREPARE_{prepared.reason_code}")
            graph = self._graph_loader.load(canary.command_id)
            close_cycle, code = self._close_cycle(
                canary.canary_id, graph, candles, continuous=True
            )
            if close_cycle is None:
                raise ValueError(f"RECOVERY_CLOSE_{code}")
            with self._mutation_safety_gate.authorize_mutation(
                MutationStage.CLOSE_EXECUTION, target, prerequisites
            ):
                closed = self._worker.run_cycle(close_cycle)
            if closed.final_lifecycle_state is not PaperLifecycleState.POSITION_CLOSED:
                raise ValueError(f"RECOVERY_CLOSE_EXECUTION_{closed.reason_code}")
            graph = self._graph_loader.load(canary.command_id)
            position = graph.positions[0]
            if position.state is not PaperPositionState.CLOSED:
                raise ValueError("RECOVERY_CLOSE_NOT_CLOSED")
            if self._outcome_diagnostics is not None:
                self._outcome_diagnostics.process(position.position_id)
            self._finalize(canary, state)
            _safe_event(
                "paper_operator_recovery_close",
                request_id=request_id,
                position_id=position_id,
                reason="OPERATOR_RECOVERY_CLOSE",
                exit_fill_id=position.exit_fill_id,
                source_closed_until_ms=eligible[-1].close_boundary_ms,
                real_binance_order_calls=0,
            )
            return PaperOperatorRecoveryCloseDecision(
                request_id=request_id,
                accepted=True,
                executed=True,
                position_id=position_id,
                state_before="OPEN",
                state_after="CLOSED",
                close_reason="OPERATOR_RECOVERY_CLOSE",
                exit_fill_id=position.exit_fill_id,
                exit_price=format(position.average_exit_price, "f"),
                exit_fee=format(position.exit_fees, "f"),
                source_closed_until_ms=eligible[-1].close_boundary_ms,
            )

    def run_once(self) -> str:
        canary = self._canary_store.current()
        if canary is None or canary.command_id is None:
            return "NO_COMMAND_READY"
        with self._lock.acquire(canary.canary_id) as claimed:
            if not claimed:
                return "CLAIMED_BY_ANOTHER_WORKER"
            canary = self._canary_store.get(canary.canary_id)
            if canary is None or canary.command_id is None:
                return "NO_COMMAND_READY"
            state = self._control.read_authoritative()
            armed_lineage = (
                state.state is PersistentState.ARMED
                and state.generation == canary.arming_generation
                and state.transition_id == canary.arming_transition_id
            )
            continuous_lineage = (
                state.state is PersistentState.CONTINUOUS_ARMED
                and canary.authority_mode == "CONTINUOUS"
                and state.generation == canary.current_control_generation
            )
            disabled_finalization = (
                state.state is PersistentState.DISABLED
                and canary.state.value in {"POSITION_CLOSED", "RECONCILIATION_PENDING"}
            )
            if (
                not (armed_lineage or continuous_lineage or disabled_finalization)
                or canary.command_count != 1
                or canary.max_new_commands != 1
                or canary.max_open_positions != 1
            ):
                return "CONTROL_PREEMPTED"
            graph = self._graph_loader.load(canary.command_id)
            lifecycle = classify_paper_lifecycle_state(graph)
            if lifecycle is PaperLifecycleState.INCONSISTENT:
                authority = (
                    "CONTINUOUS"
                    if canary.authority_mode == "CONTINUOUS"
                    else "FIRST_CANARY"
                )
                reason = f"{authority}_LIFECYCLE_INCONSISTENT"
                self._canary_store.fail_safe(canary.canary_id, reason)
                return f"SAFE_FAILURE:{reason}"
            if lifecycle is PaperLifecycleState.POSITION_CLOSED:
                if self._outcome_diagnostics is not None and graph.positions:
                    self._outcome_diagnostics.process(graph.positions[0].position_id)
                return self._finalize(canary, state)
            readiness: ExistingCanaryRuntimeReadiness = self._runtime_readiness()
            if not all((readiness.market_data_ready, readiness.approval_source_ready,
                        readiness.backup_pitr_pass, readiness.live_disabled)):
                return "SAFE_FAILURE:INDEPENDENT_READINESS_GATE_DENIED"
            continuous = canary.authority_mode == "CONTINUOUS"
            candles, market = self._snapshot(
                graph.command.symbol, canary.canary_id, continuous=continuous
            )
            if candles is None:
                return f"WAITING_FOR_MARKET_DATA:{market}"
            if lifecycle is PaperLifecycleState.ENTRY_ORDER_OPEN:
                cycle, readiness_code = self._entry_cycle(
                    canary.canary_id, graph, candles, continuous=continuous
                )
                stage = MutationStage.ENTRY_EXECUTION
            elif lifecycle is PaperLifecycleState.POSITION_OPEN_CURSOR_READY:
                if self._stale_position_shadow is not None:
                    try:
                        shadow = self._stale_position_shadow.evaluate_and_persist(
                            graph.positions[0], candles
                        )
                        _safe_event(
                            "stale_position_shadow_evaluated",
                            position_id=graph.positions[0].position_id,
                            mode="SHADOW",
                            decision=None if shadow is None else shadow.shadow_decision,
                            reason=None if shadow is None else shadow.shadow_exit_reason,
                            holding_seconds=None if shadow is None else shadow.holding_seconds,
                            production_exit_mutation=False,
                        )
                    except Exception as error:
                        _safe_event(
                            "stale_position_shadow_fault",
                            position_id=graph.positions[0].position_id,
                            error_type=type(error).__name__,
                            production_exit_mutation=False,
                        )
                cycle, readiness_code = self._exit_cycle(
                    canary.canary_id, graph, candles, continuous=continuous
                )
                stage = MutationStage.EXIT_EVALUATION_MUTATION
            elif lifecycle is PaperLifecycleState.POSITION_CLOSING_CLOSE_ORDER_OPEN:
                cycle, readiness_code = self._close_cycle(
                    canary.canary_id, graph, candles, continuous=continuous
                )
                stage = MutationStage.CLOSE_EXECUTION
            else:
                return f"SAFE_FAILURE:UNSUPPORTED_{lifecycle.value}"
            if cycle is None:
                return readiness_code
            target = PaperProductionMutationTarget(
                environment=canary.environment, mode=canary.mode,
                symbol=graph.command.symbol, candidate_identity=graph.command.risk_decision_id,
                current_generation=state.generation, new_commands_before=canary.command_count,
                open_positions_before=canary.position_count,
            )
            prerequisites = MutationPrerequisites(
                market_data_ready=True, approval_candidate_eligible=True,
                backup_pitr_pass=True, paper_target_authorized=True, live_disabled=True,
            )
            try:
                with self._mutation_safety_gate.authorize_mutation(stage, target, prerequisites):
                    result = self._worker.run_cycle(cycle)
            except SafetyControlError as error:
                return f"SAFE_FAILURE:{str(error)[:96]}"
            _safe_event(
                "paper_canary_lifecycle_stage", canary_id=canary.canary_id,
                command_id=canary.command_id, stage=stage.value,
                outcome=result.outcome.value, reason=result.reason_code,
                state_before=result.initial_lifecycle_state.value,
                state_after=result.final_lifecycle_state.value,
                mutation_committed=result.stages_completed == 1,
                position_id=result.position_id,
                child_outcome=(
                    result.stage_trace[-1].child_outcome_code
                    if result.stage_trace else None
                ),
                child_reason=(
                    result.stage_trace[-1].child_reason_code
                    if result.stage_trace else None
                ),
            )
            if (
                canary.authority_mode == "CONTINUOUS"
                and result.position_id is not None
                and self._continuous_store is not None
            ):
                self._continuous_store.record_position(position_id=result.position_id)
            if result.position_id is not None and self._opportunity_registry is not None:
                self._opportunity_registry.bind_position_for_command(
                    canary.command_id, result.position_id
                )
            if (
                result.position_id is not None
                and result.final_lifecycle_state is PaperLifecycleState.POSITION_CLOSED
                and self._outcome_diagnostics is not None
            ):
                self._outcome_diagnostics.process(result.position_id)
            child_reason = result.stage_trace[-1].child_reason_code if result.stage_trace else result.reason_code
            suffix = "" if result.stages_completed == 1 else f":{child_reason}"
            return f"{result.outcome.value}:{result.final_lifecycle_state.value}{suffix}"

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._last_result = self.run_once()
            except Exception as error:
                self._last_result = f"SAFE_FAILURE:{type(error).__name__}"
                _safe_event("paper_canary_lifecycle_fault", error_type=type(error).__name__)
            finally:
                self._ticks += 1
            self._stop.wait(self.poll_seconds)


__all__ = (
    "ProductionPaperFirstCanaryLifecycleWorker",
    "lifecycle_poll_seconds",
)
