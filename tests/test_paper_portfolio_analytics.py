from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.analytics.paper_portfolio_analytics import PaperPortfolioAnalyticsService
from app.db.models import Candle, PaperAccount, PaperPosition


def test_portfolio_analytics_empty_db_returns_unavailable(sqlite_session) -> None:
    report = PaperPortfolioAnalyticsService().analyze_symbol("BTCUSDT")

    assert report.data_quality == "UNAVAILABLE"
    assert report.available_cash is None
    assert report.unavailable_reason is not None


def test_portfolio_analytics_no_open_position_returns_complete(sqlite_session) -> None:
    now = datetime.now(UTC)
    account = PaperAccount(currency="USDT", balance=Decimal("1000"), created_at=now, updated_at=now)
    sqlite_session.add(account)
    sqlite_session.commit()

    report = PaperPortfolioAnalyticsService().analyze_symbol("BTCUSDT")

    assert report.available_cash == Decimal("1000")
    assert report.locked_cash == Decimal("0")
    assert report.open_position_qty == Decimal("0")
    assert report.open_position_avg_price is None
    assert report.unrealized_pnl == Decimal("0")
    assert report.data_quality == "COMPLETE"


def test_portfolio_analytics_partial_without_mark_price(sqlite_session) -> None:
    now = datetime.now(UTC)
    account = PaperAccount(currency="USDT", balance=Decimal("900"), created_at=now, updated_at=now)
    position = PaperPosition(
        symbol="BTCUSDT",
        side="LONG",
        status="OPEN",
        entry_price=Decimal("100"),
        quantity=Decimal("1"),
        stop_loss=None,
        take_profit=None,
        opened_at=now,
        closed_at=None,
        close_price=None,
        realized_pnl=None,
        created_at=now,
        updated_at=now,
    )
    sqlite_session.add_all([account, position])
    sqlite_session.commit()

    report = PaperPortfolioAnalyticsService().analyze_symbol("BTCUSDT")

    assert report.available_cash == Decimal("900")
    assert report.locked_cash == Decimal("100")
    assert report.open_position_qty == Decimal("1")
    assert report.open_position_avg_price == Decimal("100")
    assert report.latest_mark_price is None
    assert report.unrealized_pnl is None
    assert report.data_quality == "PARTIAL"
    assert report.unavailable_reason is not None


def test_portfolio_analytics_unrealized_pnl_formula(sqlite_session) -> None:
    now = datetime.now(UTC)
    account = PaperAccount(currency="USDT", balance=Decimal("900"), created_at=now, updated_at=now)
    position = PaperPosition(
        symbol="BTCUSDT",
        side="LONG",
        status="OPEN",
        entry_price=Decimal("100"),
        quantity=Decimal("1"),
        stop_loss=None,
        take_profit=None,
        opened_at=now,
        closed_at=None,
        close_price=None,
        realized_pnl=None,
        created_at=now,
        updated_at=now,
    )
    candle = Candle(
        symbol="BTCUSDT",
        interval="15m",
        open_time=now,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("99"),
        close=Decimal("110"),
        volume=Decimal("1"),
        close_time=now,
    )
    sqlite_session.add_all([account, position, candle])
    sqlite_session.commit()

    report = PaperPortfolioAnalyticsService().analyze_symbol("BTCUSDT")

    assert report.unrealized_pnl == Decimal("10.00000000")
    assert report.estimated_position_value == Decimal("110.00000000")
    assert report.estimated_equity == Decimal("1010.00000000")
    assert report.total_pnl == Decimal("10.00000000")
    assert report.return_pct == Decimal("0.01000000")
    assert report.data_quality == "COMPLETE"


def test_portfolio_analytics_realized_pnl_is_filtered_by_symbol(sqlite_session) -> None:
    now = datetime.now(UTC)
    account = PaperAccount(currency="USDT", balance=Decimal("1000"), created_at=now, updated_at=now)

    btc_closed_position = PaperPosition(
        symbol="BTCUSDT",
        side="LONG",
        status="CLOSED",
        entry_price=Decimal("100"),
        quantity=Decimal("1"),
        stop_loss=None,
        take_profit=None,
        opened_at=now,
        closed_at=now,
        close_price=Decimal("110"),
        realized_pnl=Decimal("10"),
        created_at=now,
        updated_at=now,
    )

    eth_closed_position = PaperPosition(
        symbol="ETHUSDT",
        side="LONG",
        status="CLOSED",
        entry_price=Decimal("100"),
        quantity=Decimal("1"),
        stop_loss=None,
        take_profit=None,
        opened_at=now,
        closed_at=now,
        close_price=Decimal("130"),
        realized_pnl=Decimal("30"),
        created_at=now,
        updated_at=now,
    )

    sqlite_session.add_all([account, btc_closed_position, eth_closed_position])
    sqlite_session.commit()

    report = PaperPortfolioAnalyticsService().analyze_symbol("BTCUSDT")

    assert report.realized_pnl == Decimal("10")
    assert report.total_pnl == Decimal("10.00000000")
