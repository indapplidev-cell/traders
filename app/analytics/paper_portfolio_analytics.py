from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select, func

from app.db.models import Candle, PaperAccount, PaperPosition
from app.db.session import session_scope


@dataclass(slots=True)
class PortfolioAnalyticsReport:
    symbol: str
    quote_asset: str
    available_cash: Decimal | None
    locked_cash: Decimal | None
    open_position_qty: Decimal | None
    open_position_avg_price: Decimal | None
    latest_mark_price: Decimal | None
    estimated_position_value: Decimal | None
    estimated_equity: Decimal | None
    realized_pnl: Decimal | None
    unrealized_pnl: Decimal | None
    total_pnl: Decimal | None
    return_pct: Decimal | None
    data_quality: str
    unavailable_reason: str | None


class PaperPortfolioAnalyticsService:
    """Сервис аналитики paper-портфеля по локальным данным."""

    def analyze_symbol(self, symbol: str) -> PortfolioAnalyticsReport:
        normalized_symbol = symbol.upper()

        with session_scope() as session:
            account = session.execute(
                select(PaperAccount).where(PaperAccount.currency == "USDT")
            ).scalar_one_or_none()
            positions = list(
                session.execute(
                    select(PaperPosition).where(
                        PaperPosition.symbol == normalized_symbol,
                        PaperPosition.status == "OPEN",
                    )
                )
                .scalars()
                .all()
            )
            latest_candle = session.execute(
                select(Candle)
                .where(Candle.symbol == normalized_symbol)
                .order_by(Candle.close_time.desc())
                .limit(1)
            ).scalar_one_or_none()
            realized_pnl = Decimal(
                str(
                    session.execute(
                        select(func.coalesce(func.sum(PaperPosition.realized_pnl), 0)).where(
                            PaperPosition.symbol == normalized_symbol,
                            PaperPosition.status == "CLOSED",
                        )
                    ).scalar_one()
                )
            )

        if account is None:
            return PortfolioAnalyticsReport(
                symbol=normalized_symbol,
                quote_asset="USDT",
                available_cash=None,
                locked_cash=None,
                open_position_qty=None,
                open_position_avg_price=None,
                latest_mark_price=None,
                estimated_position_value=None,
                estimated_equity=None,
                realized_pnl=None,
                unrealized_pnl=None,
                total_pnl=None,
                return_pct=None,
                data_quality="UNAVAILABLE",
                unavailable_reason="Paper account data not found.",
            )

        available_cash = Decimal(str(account.balance))
        open_position_qty = sum((position.quantity for position in positions), Decimal("0"))
        locked_cash = sum(
            (
                (position.entry_price * position.quantity).quantize(Decimal("0.00000001"))
                for position in positions
            ),
            Decimal("0.00000000"),
        )
        open_position_avg_price = None
        if open_position_qty and open_position_qty > 0:
            total_cost = sum(position.entry_price * position.quantity for position in positions)
            open_position_avg_price = (total_cost / open_position_qty).quantize(Decimal("0.00000001"))

        latest_mark_price = Decimal(str(latest_candle.close)) if latest_candle is not None else None
        estimated_position_value = None
        if open_position_qty is not None and open_position_qty > 0:
            if latest_mark_price is not None:
                estimated_position_value = (open_position_qty * latest_mark_price).quantize(Decimal("0.00000001"))
        else:
            estimated_position_value = Decimal("0")

        unrealized_pnl = None
        if open_position_qty is not None and open_position_qty > 0:
            if latest_mark_price is not None and open_position_avg_price is not None:
                unrealized_pnl = (open_position_qty * (latest_mark_price - open_position_avg_price)).quantize(
                    Decimal("0.00000001")
                )
        else:
            unrealized_pnl = Decimal("0")

        estimated_equity = None
        if estimated_position_value is not None:
            estimated_equity = (available_cash + estimated_position_value).quantize(Decimal("0.00000001"))

        total_pnl = None
        if realized_pnl is not None and unrealized_pnl is not None:
            total_pnl = (realized_pnl + unrealized_pnl).quantize(Decimal("0.00000001"))

        starting_balance = available_cash + locked_cash - realized_pnl
        return_pct = None
        if total_pnl is not None and starting_balance and starting_balance != 0:
            return_pct = (total_pnl / starting_balance).quantize(Decimal("0.00000001"))

        if open_position_qty and open_position_qty > 0 and latest_mark_price is None:
            data_quality = "PARTIAL"
            unavailable_reason = "No local mark price available for open position valuation."
        else:
            data_quality = "COMPLETE"
            unavailable_reason = None

        if latest_mark_price is None and open_position_qty == 0:
            data_quality = "COMPLETE"
            unavailable_reason = None

        return PortfolioAnalyticsReport(
            symbol=normalized_symbol,
            quote_asset="USDT",
            available_cash=available_cash,
            locked_cash=locked_cash,
            open_position_qty=open_position_qty,
            open_position_avg_price=open_position_avg_price,
            latest_mark_price=latest_mark_price,
            estimated_position_value=estimated_position_value,
            estimated_equity=estimated_equity,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_pnl=total_pnl,
            return_pct=return_pct,
            data_quality=data_quality,
            unavailable_reason=unavailable_reason,
        )
