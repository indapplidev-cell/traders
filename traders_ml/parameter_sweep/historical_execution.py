"""Research-only chronological positions using the shared PAPER calculations."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.engine_paper.controlled_quantity_validity import calculate_quantity_sizing
from app.engine_paper.exit_evaluator import evaluate_paper_exit_window, PAPER_EXIT_EVALUATION_POLICY_ID
from app.engine_paper.fill_simulator import PaperFillCandle, adverse_fill_price, quote_fee_amount, resolve_trade_action
from app.engine_paper.fill_roles import PaperFillRole
from app.engine_paper.portfolio_gate import evaluate_paper_portfolio_gate
from app.engine_position.paper_accounting import gross_realized_pnl, net_realized_pnl, risk_multiple
from app.engine_safety.paper_domain import PaperSide
from app.operator_control.production_executor import _foundation_policy


def decimal(value):
    return Decimal(str(value))


def fill_candle(row):
    return PaperFillCandle(symbol=row.symbol, timeframe="1m", open_time_ms=row.open_time_ms,
        close_boundary_ms=row.close_time_ms+1, open_price=decimal(row.open), high_price=decimal(row.high),
        low_price=decimal(row.low), close_price=decimal(row.close), is_closed=True,
        observed_closed_until_ms=row.close_time_ms+1)


@dataclass
class HistoricalPosition:
    identity: str
    symbol: str
    side: PaperSide
    quantity: Decimal
    entry: Decimal
    entry_fee: Decimal
    stop: Decimal
    target: Decimal
    entry_boundary: int
    cursor: int
    initial_risk: Decimal
    exit_fee_bps: Decimal
    exit_slippage_bps: Decimal
    exit_cause: str | None = None
    pending_exit_boundary: int | None = None
    trace: list = field(default_factory=list)
    expectancy_money: Decimal | None = None
    expectancy_R: Decimal | None = None


class HistoricalExecution:
    """No DB session or order service; only immutable calculation contracts."""
    def __init__(self, capital, runtime):
        self.balance = decimal(capital)
        if not self.balance.is_finite() or self.balance<=0:
            raise ValueError("POSITIVE_FINITE_INITIAL_CAPITAL_REQUIRED")
        self.runtime = runtime
        self.positions = {}
        self.closed = []
        self.policy = _foundation_policy()

    @property
    def available_capital(self):
        return self.balance - sum((p.entry*p.quantity for p in self.positions.values()), Decimal(0))

    def portfolio_gate(self, result):
        # The shared gate consumes one SELECT result. Supply the isolated book,
        # never a production connection, while retaining its exact calculations.
        rows = [(SimpleNamespace(symbol=p.symbol, side=p.side.value, remaining_quantity=p.quantity,
                average_entry_price=p.entry, stop_price=p.stop), result.trade_profile_id)
                for p in self.positions.values()]
        session = SimpleNamespace(execute=lambda statement: tuple(rows))
        return evaluate_paper_portfolio_gate(session, result=result,
            candidate_direction=result.paper_payload["paper_direction"], account_equity=self.balance,
            evaluation_time=datetime.fromtimestamp(result.closed_until_ms/1000, timezone.utc))

    def open(self, *, identity, symbol, side, reference, stop, target, candle,
             entry_fee_bps, exit_fee_bps, entry_slippage_bps, exit_slippage_bps):
        if symbol in self.positions:
            raise ValueError("DUPLICATE_OPEN_SYMBOL")
        side = PaperSide(side)
        sizing = calculate_quantity_sizing(symbol=symbol, equity=self.available_capital,
            entry=decimal(reference), stop=decimal(stop), risk_per_trade_bps=decimal(self.runtime.risk_per_trade_bps))
        price = adverse_fill_price(decimal(candle.open), decimal(entry_slippage_bps),
            self.policy.price_quantum, resolve_trade_action(side, PaperFillRole.ENTRY))
        quantity = sizing.normalized_quantity
        fee = quote_fee_amount(price, quantity, decimal(entry_fee_bps), self.policy.fee_quantum)
        if price*quantity+fee > self.available_capital:
            raise ValueError("INSUFFICIENT_CAPITAL_AFTER_ENTRY_COSTS")
        if not (decimal(stop) < price < decimal(target) if side == PaperSide.LONG else decimal(target) < price < decimal(stop)):
            raise ValueError("FILL_OUTSIDE_STOP_TARGET")
        p = HistoricalPosition(identity, symbol, side, quantity, price, fee, decimal(stop), decimal(target),
            candle.open_time_ms, candle.close_time_ms+1, abs(price-decimal(stop))*quantity,
            decimal(exit_fee_bps), decimal(exit_slippage_bps))
        p.trace.append({"event": "ENTRY", "source_open_ms": candle.open_time_ms,
                        "observed_closed_ms": candle.close_time_ms+1, "sizing": sizing.to_dict()})
        self.positions[symbol] = p
        self.balance -= fee
        return p

    def advance(self, symbol, candle):
        p = self.positions.get(symbol)
        if p is None:
            return
        if candle.open_time_ms != p.cursor:
            raise ValueError("POSITION_MARKET_DATA_GAP")
        if p.pending_exit_boundary is not None:
            price = adverse_fill_price(decimal(candle.open), p.exit_slippage_bps,
                self.policy.price_quantum, resolve_trade_action(p.side, PaperFillRole.CLOSE))
            fee = quote_fee_amount(price, p.quantity, p.exit_fee_bps, self.policy.fee_quantum)
            gross = gross_realized_pnl(p.side, p.entry, price, p.quantity)
            net = net_realized_pnl(gross, p.entry_fee, fee)
            self.balance += gross-fee
            self.closed.append({"identity": p.identity, "symbol": symbol, "side": p.side.value,
                "quantity": str(p.quantity), "entry_price": str(p.entry), "exit_price": str(price),
                "entry_boundary": p.entry_boundary, "exit_boundary": candle.open_time_ms,
                "exit_observed_closed_ms": candle.close_time_ms+1, "exit_cause": p.exit_cause,
                "gross_pnl": str(gross), "entry_fee": str(p.entry_fee), "exit_fee": str(fee),
                "net_pnl": str(net), "realized_R": str(risk_multiple(net,p.initial_risk)),
                "expectancy_money": str(p.expectancy_money) if p.expectancy_money is not None else None,
                "expectancy_R": str(p.expectancy_R) if p.expectancy_R is not None else None,
                "trace": p.trace + [{"event": "EXIT_FILL", "source_open_ms": candle.open_time_ms}],
                "cost_accounting": "ADVERSE_PRICE_IMPACT_INCLUDED_IN_FILL_FEES_DEDUCTED_ONCE"})
            del self.positions[symbol]
            return
        result = evaluate_paper_exit_window(position_id=p.identity, cursor_id=p.identity+":cursor",
            expected_position_version=0, expected_cursor_version=0, cursor_closed_until_ms=p.cursor,
            candles=(fill_candle(candle),), market_snapshot_closed_until_ms=candle.close_time_ms+1,
            safety_directive=None, source_command_id=p.identity+":command", entry_fill_id=p.identity+":fill",
            symbol=symbol, side=p.side, remaining_quantity=p.quantity, stop_price=p.stop,
            target_price=p.target, evaluation_policy_id=PAPER_EXIT_EVALUATION_POLICY_ID,
            correlation_id=p.identity, causation_id=p.identity)
        if not result.successful:
            raise ValueError(result.reason_code)
        p.cursor = candle.close_time_ms+1
        if result.trigger:
            p.pending_exit_boundary = result.trigger.trigger_source_closed_until_ms
            p.exit_cause = result.trigger.cause.value
            p.trace.append({"event": "EXIT_TRIGGER", "boundary": p.pending_exit_boundary,
                "stop_hit": result.trigger.stop_hit, "target_hit": result.trigger.target_hit})
        # The production evaluator has no live time-stop action. SHADOW stale
        # position diagnostics cannot close a research position either.

    def summary(self):
        return {"balance": str(self.balance), "closed_trades": self.closed,
                "open_positions": list(self.positions),
                "open_position_entry_fees":str(sum((p.entry_fee for p in self.positions.values()),Decimal(0))),
                "net_pnl": str(sum((decimal(t["net_pnl"]) for t in self.closed), Decimal(0))),
                "terminal": "INCOMPLETE_EXIT_TAIL" if self.positions else "COMPLETE"}
