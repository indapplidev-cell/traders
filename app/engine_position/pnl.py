"""Pure Decimal PnL calculations; no implicit quantization is performed."""
from decimal import Decimal
from app.engine_position.enums import PositionSide


def unrealized_pnl(side: PositionSide, entry: Decimal, mark: Decimal, quantity: Decimal) -> Decimal:
    return (mark - entry) * quantity if side is PositionSide.LONG else (entry - mark) * quantity


def realized_pnl(side: PositionSide, entry: Decimal, close: Decimal, quantity: Decimal) -> Decimal:
    return (close - entry) * quantity if side is PositionSide.LONG else (entry - close) * quantity


def net_realized_pnl(gross: Decimal, fees: Decimal) -> Decimal:
    return gross - fees
