"""Research-only chronological portfolio lifecycle for native v3 decisions.

The caller supplies native candidate decisions and frozen, closed 1m candles.
No production persistence or exchange services are used here.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from collections.abc import Callable, Iterable, Mapping
from contextlib import ExitStack
from dataclasses import dataclass
from decimal import Decimal
from heapq import merge
from pathlib import Path
from typing import Any

from app.config.trade_parameters import AnalyticalExitParameters, ScalpingV2Parameters
from app.engine_analysis import AnalysisWindowConfig
from app.engine_paper.analytical_exit import (
    AnalyticalExitDecision,
    ClosedAnalysisCandle,
    analyze_position_exit,
)

from .full_pipeline_ragged import HistoricalCostModelV1
from .full_pipeline_v3 import HistoricalCostLedgerV3, _sha256


@dataclass(frozen=True, slots=True)
class ReplayPolicyV3:
    max_open_positions: int
    max_new_commands_per_cycle: int
    risk_per_trade_bps: float
    total_open_risk_limit_bps: float
    entry_ttl_ms: int
    hard_timeout_ms: int

    @classmethod
    def from_parameters(cls, parameters: ScalpingV2Parameters) -> ReplayPolicyV3:
        return cls(
            max_open_positions=parameters.risk.max_open_positions,
            max_new_commands_per_cycle=parameters.risk.max_new_commands_per_cycle,
            risk_per_trade_bps=parameters.risk.risk_per_trade_bps,
            total_open_risk_limit_bps=parameters.risk.total_open_risk_limit_bps,
            entry_ttl_ms=parameters.lifecycle.entry_fill_window_seconds * 1000,
            hard_timeout_ms=parameters.exit_policy.stale_position.hard_timeout_seconds * 1000,
        )


@dataclass(slots=True)
class _Pending:
    symbol: str
    opportunity_id: str
    signal_ms: int
    expires_ms: int
    entry: float
    stop: float
    target: float
    score: float
    regime: str | None


@dataclass(slots=True)
class _Position:
    pending: _Pending
    filled_ms: int
    notional: float
    locked: float
    last_close: float
    last_candle_ms: int


class FullPipelineReplayEngineV3:
    """Apply shared position/capital limits to a global 5m/1m event clock."""

    def __init__(self, *, policy: ReplayPolicyV3, cost_model: HistoricalCostModelV1,
                 initial_equity: float, role_end_ms: int,
                 analytical_exit: Callable[[str, Mapping[str, Any], Mapping[str, Any]], str | None]
                 | None = None) -> None:
        if initial_equity <= 0 or policy.max_open_positions < 1 or role_end_ms <= 0:
            raise ValueError("INVALID_V3_REPLAY_POLICY")
        self.policy = policy
        self.cost_model = cost_model
        self.role_end_ms = role_end_ms
        self.analytical_exit = analytical_exit
        self.balance = initial_equity
        self.available = initial_equity
        self.pending: dict[str, _Pending] = {}
        self.positions: dict[str, _Position] = {}
        self.seen_opportunities: set[str] = set()
        self.trades: list[dict[str, Any]] = []
        self.traces: list[dict[str, Any]] = []
        self.last_event_ms = -1

    def _record(self, *, boundary_ms: int, symbol: str, stage: str,
                reason: str, opportunity_id: str | None = None) -> None:
        self.traces.append({"boundary_ms": boundary_ms, "symbol": symbol,
                            "stage": stage, "reason": reason,
                            "opportunity_id": opportunity_id})

    def on_boundary(self, boundary_ms: int,
                    decisions: Iterable[Mapping[str, Any]]) -> None:
        if boundary_ms < self.last_event_ms or boundary_ms >= self.role_end_ms:
            raise ValueError("V3_BOUNDARY_OUTSIDE_CHRONOLOGY_OR_ROLE")
        self.last_event_ms = boundary_ms
        for symbol, plan in list(self.pending.items()):
            if plan.expires_ms < boundary_ms:
                self.pending.pop(symbol)
                self._record(boundary_ms=boundary_ms, symbol=symbol,
                             stage="FILL", reason="ENTRY_TTL_EXPIRED",
                             opportunity_id=plan.opportunity_id)
        eligible: list[_Pending] = []
        for row in decisions:
            symbol = str(row["symbol"])
            paper = row.get("paper") or {}
            statuses = row.get("statuses") or {}
            if statuses.get("paper_status") != "PAPER_PLAN_READY":
                self._record(boundary_ms=boundary_ms, symbol=symbol,
                             stage="NATIVE_PIPELINE",
                             reason=str(row.get("first_rejection") or statuses.get("paper_status")))
                continue
            context = paper.get("paper_context") or {}
            diagnostic = context.get("scalping_geometry_diagnostics") or {}
            opportunity = str(diagnostic.get("opportunity_id") or paper.get("source_setup_id") or "")
            entry = paper.get("hypothetical_entry_reference")
            stop = paper.get("hypothetical_stop_level")
            target = paper.get("hypothetical_target_level")
            if not opportunity or any(value is None for value in (entry, stop, target)):
                self._record(boundary_ms=boundary_ms, symbol=symbol,
                             stage="PLAN", reason="INCOMPLETE_NATIVE_PLAN")
                continue
            entry, stop, target = float(entry), float(stop), float(target)
            if not 0 < stop < entry < target:
                self._record(boundary_ms=boundary_ms, symbol=symbol,
                             stage="PLAN", reason="INVALID_LONG_GEOMETRY")
                continue
            if opportunity in self.seen_opportunities:
                self._record(boundary_ms=boundary_ms, symbol=symbol,
                             stage="OPPORTUNITY", reason="DUPLICATE_WITHOUT_RESET",
                             opportunity_id=opportunity)
                continue
            eligible.append(_Pending(symbol, opportunity, boundary_ms,
                            min(boundary_ms + self.policy.entry_ttl_ms, self.role_end_ms),
                            entry, stop, target, float(paper.get("source_risk_score") or 0),
                            str(context.get("empirical_regime_normalized") or "") or None))
        eligible.sort(key=lambda item: (-item.score, item.symbol, item.opportunity_id))
        for index, candidate in enumerate(eligible):
            reason = None
            if index >= self.policy.max_new_commands_per_cycle:
                reason = "SELECTOR_LIMIT"
            elif candidate.symbol in self.pending or candidate.symbol in self.positions:
                reason = "SYMBOL_ALREADY_ACTIVE"
            elif len(self.pending) + len(self.positions) >= self.policy.max_open_positions:
                reason = "PORTFOLIO_SLOTS_FULL"
            if reason:
                self._record(boundary_ms=boundary_ms, symbol=candidate.symbol,
                             stage="PORTFOLIO", reason=reason,
                             opportunity_id=candidate.opportunity_id)
                continue
            self.pending[candidate.symbol] = candidate
            self.seen_opportunities.add(candidate.opportunity_id)
            self._record(boundary_ms=boundary_ms, symbol=candidate.symbol,
                         stage="APPROVAL", reason="PENDING_NEXT_1M_CANDLE",
                         opportunity_id=candidate.opportunity_id)

    def on_1m_candle(self, symbol: str, candle: Mapping[str, Any]) -> None:
        close_ms = int(candle["close_time_ms"])
        event_ms = close_ms + 1
        if event_ms < self.last_event_ms or event_ms > self.role_end_ms:
            raise ValueError("V3_CANDLE_OUTSIDE_CHRONOLOGY_OR_ROLE")
        self.last_event_ms = event_ms
        high, low, close = (float(candle[key]) for key in ("high", "low", "close"))
        pending = self.pending.get(symbol)
        if pending and event_ms > pending.expires_ms:
            self.pending.pop(symbol)
            self._record(boundary_ms=event_ms, symbol=symbol,
                         stage="FILL", reason="ENTRY_TTL_EXPIRED",
                         opportunity_id=pending.opportunity_id)
            pending = None
        if (pending and event_ms > pending.signal_ms and event_ms < self.role_end_ms
                and low <= pending.entry <= high):
            risk_bps = self.policy.risk_per_trade_bps
            current_risk = len(self.positions) * risk_bps
            stop_bps = (pending.entry - pending.stop) / pending.entry * 10_000
            bucket, _ = self.cost_model.resolve(symbol, pending.regime)
            cost_reserve_fraction = (
                bucket.entry_fee_bps + bucket.exit_fee_bps + bucket.spread_bps
                + bucket.entry_slippage_bps + bucket.exit_slippage_bps
                + bucket.depth_impact_bps
                + bucket.reserve_bps
            ) / 10_000
            notional = min(self.available / (1 + cost_reserve_fraction),
                           self.balance * risk_bps / max(stop_bps, 1e-9))
            locked = notional * (1 + cost_reserve_fraction)
            if current_risk + risk_bps <= self.policy.total_open_risk_limit_bps and notional > 0:
                self.pending.pop(symbol)
                self.available -= locked
                self.positions[symbol] = _Position(pending, event_ms, notional,
                                                   locked, close, event_ms)
                self._record(boundary_ms=event_ms, symbol=symbol, stage="FILL",
                             reason="FILLED_AFTER_SIGNAL", opportunity_id=pending.opportunity_id)
            else:
                self._record(boundary_ms=event_ms, symbol=symbol, stage="RISK",
                             reason="CAPITAL_OR_OPEN_RISK_LIMIT", opportunity_id=pending.opportunity_id)
        position = self.positions.get(symbol)
        if position is None or event_ms < position.filled_ms:
            return
        position.last_close = close
        position.last_candle_ms = event_ms
        plan = position.pending
        # When entry and both exits are touched in one later candle, stop wins.
        if low <= plan.stop:
            self._close(symbol, event_ms, plan.stop, "STOP")
        elif high >= plan.target:
            self._close(symbol, event_ms, plan.target, "TARGET")
        elif self.analytical_exit is not None and (
            reason := self.analytical_exit(symbol, {
                "opportunity_id": plan.opportunity_id,
                "entry_price": plan.entry, "stop_price": plan.stop,
                "target_price": plan.target, "filled_ms": position.filled_ms,
                "notional": position.notional, "close": close,
                "regime": plan.regime,
            }, candle)
        ):
            self._close(symbol, event_ms, close, reason)
        elif event_ms - position.filled_ms >= self.policy.hard_timeout_ms:
            self._close(symbol, event_ms, close, "TIME_STOP_HARD")

    def _close(self, symbol: str, exit_ms: int, exit_price: float, reason: str) -> None:
        position = self.positions.pop(symbol)
        plan = position.pending
        bucket, bucket_key = self.cost_model.resolve(symbol, plan.regime)
        gross = position.notional * (exit_price - plan.entry) / plan.entry
        ledger = HistoricalCostLedgerV3.from_bps(
            boundary_ms=exit_ms, provenance="MODELLED_CONSERVATIVE", evidence_ms=None,
            notional=position.notional, gross_pnl=gross,
            entry_fee_bps=bucket.entry_fee_bps, exit_fee_bps=bucket.exit_fee_bps,
            spread_bps=bucket.spread_bps,
            entry_slippage_bps=bucket.entry_slippage_bps,
            exit_slippage_bps=bucket.exit_slippage_bps,
            depth_impact_bps=bucket.depth_impact_bps, reserve_bps=bucket.reserve_bps,
        )
        self.available += position.locked + ledger.net_pnl
        self.balance += ledger.net_pnl
        self.trades.append({"symbol": symbol, "opportunity_id": plan.opportunity_id,
                            "signal_ms": plan.signal_ms, "filled_ms": position.filled_ms,
                            "closed_ms": exit_ms, "entry_price": plan.entry,
                            "exit_price": exit_price, "reason": reason,
                            "cost_bucket": bucket_key, "ledger": ledger.model_dump(mode="json")})
        self._record(boundary_ms=exit_ms, symbol=symbol, stage="EXIT", reason=reason,
                     opportunity_id=plan.opportunity_id)

    def finish_role(self) -> dict[str, Any]:
        for symbol in sorted(self.pending):
            plan = self.pending[symbol]
            self._record(boundary_ms=self.role_end_ms, symbol=symbol,
                         stage="ROLE_END", reason="PENDING_CANCELLED",
                         opportunity_id=plan.opportunity_id)
        self.pending.clear()
        for symbol in sorted(self.positions):
            position = self.positions[symbol]
            if position.last_candle_ms <= position.filled_ms:
                raise ValueError("V3_ROLE_END_HAS_NO_LATER_CLOSED_CANDLE")
            self._close(symbol, self.role_end_ms, position.last_close, "ROLE_END")
        return {"trades": self.trades, "traces": self.traces,
                "balance": self.balance, "net_pnl": sum(trade["ledger"]["net_pnl"]
                                                    for trade in self.trades)}


def _events_from_handle(handle: Any, *, symbol: str, kind: str,
                        start_ms: int, end_ms: int) -> Iterable[tuple[int, int, str, dict[str, Any]]]:
    previous = -1
    for line in handle:
        row = json.loads(line)
        if kind.startswith("CANDLE_"):
            timeframe = kind.removeprefix("CANDLE_")
            if row["timeframe"] != timeframe:
                if timeframe == "1m" or row["timeframe"] in {"15m", "1h"}:
                    return  # Frozen archive is grouped 1m, 5m, 15m, 1h.
                continue
            event_ms = int(row["close_time_ms"]) + 1
            priority = 0 if timeframe == "5m" else 1
            if event_ms > end_ms:
                return
        else:
            event_ms = int(row["boundary_ms"])
            priority = 2
            if event_ms >= end_ms:
                return
        if event_ms < previous:
            raise ValueError("V3_EVENT_SOURCE_NOT_MONOTONIC")
        previous = event_ms
        if event_ms >= start_ms:
            yield event_ms, priority, symbol, row


def _analysis_candle(symbol: str, row: Mapping[str, Any]) -> ClosedAnalysisCandle:
    return ClosedAnalysisCandle(
        symbol=symbol, timeframe=str(row["timeframe"]),
        open_time_ms=int(row["open_time_ms"]),
        close_boundary_ms=int(row["close_time_ms"]) + 1,
        open_price=Decimal(str(row["open"])),
        high_price=Decimal(str(row["high"])),
        low_price=Decimal(str(row["low"])),
        close_price=Decimal(str(row["close"])),
        volume=Decimal(str(row["volume"])),
        quote_volume=(Decimal(str(row["quote_volume"]))
                      if row.get("quote_volume") is not None else None),
        trades_count=(int(row["trades_count"])
                      if row.get("trades_count") is not None else None),
        source="v3-frozen-research", is_closed=True,
    )


def replay_signal_shards_v3(
    shards: Mapping[str, tuple[Path, Path]], *, dataset_hash: str,
    policy: ReplayPolicyV3, cost_model: HistoricalCostModelV1,
    initial_equity: float, role_start_ms: int, role_end_ms: int,
    holdout_start_ms: int,
    analytical_exit: Callable[[str, Mapping[str, Any], Mapping[str, Any]], str | None]
    | None = None,
    analytical_policy: AnalyticalExitParameters | None = None,
) -> dict[str, Any]:
    """Merge certified per-symbol native signals and frozen 1m candles."""
    if role_start_ms >= role_end_ms or role_end_ms > holdout_start_ms or not shards:
        raise ValueError("V3_INVALID_REPLAY_ROLE_OR_SHARDS")
    context_size = AnalysisWindowConfig().context_candles + 4
    candle_context: dict[str, dict[str, deque[ClosedAnalysisCandle]]] = defaultdict(
        lambda: {"1m": deque(maxlen=context_size), "5m": deque(maxlen=context_size)})
    prior_scores: dict[str, list[float]] = defaultdict(list)

    def native_exit(symbol: str, position: Mapping[str, Any], candle: Mapping[str, Any]) -> str | None:
        boundary_ms = int(candle["close_time_ms"]) + 1
        if boundary_ms <= int(position["filled_ms"]):
            return None
        entry = Decimal(str(position["entry_price"]))
        close = Decimal(str(position["close"]))
        gross = Decimal(str(position["notional"])) * (close - entry) / entry
        bucket, _ = cost_model.resolve(symbol, position.get("regime"))
        cost_bps = (bucket.entry_fee_bps + bucket.exit_fee_bps + bucket.spread_bps
                    + bucket.entry_slippage_bps + bucket.exit_slippage_bps
                    + bucket.depth_impact_bps
                    + bucket.reserve_bps)
        net = gross - Decimal(str(position["notional"] * cost_bps / 10_000))
        identity = str(position["opportunity_id"])
        evidence = analyze_position_exit(
            position_id=identity, symbol=symbol, side="LONG",
            entry_price=entry, stop_price=Decimal(str(position["stop_price"])),
            target_price=Decimal(str(position["target_price"])),
            opened_at_ms=int(position["filled_ms"]),
            candles_1m=candle_context[symbol]["1m"],
            candles_5m=candle_context[symbol]["5m"],
            boundary_ms=boundary_ms,
            prior_exit_scores=tuple(prior_scores[identity]),
            gross_pnl=gross, net_pnl=net,
            net_pnl_bps=float(net / Decimal(str(position["notional"])) * 10_000),
            policy=analytical_policy,
        )
        if evidence.decision not in {AnalyticalExitDecision.DATA_UNAVAILABLE,
                                     AnalyticalExitDecision.ERROR}:
            prior_scores[identity].append(evidence.exit_score)
        if evidence.decision in {AnalyticalExitDecision.ANALYTICAL_EXIT,
                                 AnalyticalExitDecision.STRONG_REVERSAL_EXIT,
                                 AnalyticalExitDecision.PROFIT_PROTECTION_EXIT}:
            return str(evidence.decision.value)
        return None

    exit_evaluator = analytical_exit if analytical_exit is not None else native_exit
    engine = FullPipelineReplayEngineV3(
        policy=policy, cost_model=cost_model, initial_equity=initial_equity,
        role_end_ms=role_end_ms, analytical_exit=exit_evaluator,
    )
    with ExitStack() as stack:
        streams = []
        for symbol, (signal_path, candle_path) in sorted(shards.items()):
            signal_receipt = json.loads(signal_path.with_suffix(".json").read_text(encoding="utf-8"))
            candle_receipt = json.loads(candle_path.with_name("CANDLES.json").read_text(encoding="utf-8"))
            if (signal_receipt.get("dataset_hash") != dataset_hash
                    or candle_receipt.get("dataset_hash") != dataset_hash
                    or signal_receipt.get("symbol") != symbol
                    or signal_receipt.get("sha256") != _sha256(signal_path)
                    or candle_receipt.get("sha256") != _sha256(candle_path)
                    or candle_receipt.get("allowed_end_ms", 0) > holdout_start_ms
                    or signal_receipt.get("holdout_evaluated", False)):
                raise ValueError("V3_REPLAY_SOURCE_IDENTITY_OR_ROLE_MISMATCH")
            for path, kind in ((signal_path, "SIGNAL"), (candle_path, "CANDLE_1m"),
                               (candle_path, "CANDLE_5m")):
                handle = stack.enter_context(path.open(encoding="utf-8"))
                streams.append(_events_from_handle(handle, symbol=symbol, kind=kind,
                                                   start_ms=(role_start_ms if kind == "SIGNAL"
                                                             else max(0, role_start_ms
                                                                      - context_size * 300_000)),
                                                   end_ms=role_end_ms))
        boundary = None
        decisions: list[dict[str, Any]] = []
        for event_ms, priority, symbol, row in merge(*streams):
            if boundary is not None and event_ms != boundary:
                engine.on_boundary(boundary, decisions)
                decisions = []
                boundary = None
            if priority in (0, 1):
                candle_context[symbol][row["timeframe"]].append(_analysis_candle(symbol, row))
            if priority == 1:
                engine.on_1m_candle(symbol, row)
            elif priority == 2:
                boundary = event_ms
                decisions.append(row)
        if boundary is not None:
            engine.on_boundary(boundary, decisions)
    result = engine.finish_role()
    result["status"] = "REPLAY_NOT_VERIFIED"
    result["eligible_for_training"] = False
    result["analytical_exit_integrated"] = True
    result["holdout_evaluated"] = False
    return result
