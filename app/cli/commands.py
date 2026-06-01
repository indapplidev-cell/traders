"""CLI-команды для управления проектом."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from sqlalchemy import text

from app.backtest.backtest_engine import BacktestEngine
from app.backtest.backtest_result import BacktestResult
from app.config.settings import get_settings
from app.db.async_session import async_session_scope
from app.db.session import session_scope
from app.execution.paper_runner_service import PaperRunnerService, RunnerIterationResult
from app.execution.paper_step_service import PaperStepService
from app.execution.position_manager import PositionManager
from app.history.historical_loader import HistoricalLoadResult, HistoricalLoader
from app.market.analysis_service import MarketAnalysisService
from app.market.candle_service import CandleService
from app.market.indicator_service import IndicatorCalculationError


app = typer.Typer(help="CLI для серверного ядра traders.")
console = Console()
analysis_service = MarketAnalysisService()


def _format_decimal(value: Decimal) -> str:
    """Форматирует Decimal для компактного терминального вывода."""

    normalized = value.quantize(Decimal("0.00000001")).normalize()
    return format(normalized, "f")


def _render_paper_step_result(symbol: str, interval: str, result) -> None:
    """Печатает результат paper-step или runner в едином виде."""

    table = Table(title=f"Paper step {symbol} {interval}")
    table.add_column("field")
    table.add_column("value")
    table.add_row("strategy decision", result.strategy_decision.decision.value)
    table.add_row("final decision", result.final_decision.decision.value)
    table.add_row("regime", result.strategy_decision.regime.value)
    table.add_row("price", str(result.strategy_decision.price))
    table.add_row("strategy reason", result.strategy_decision.reason)
    table.add_row("final reason", result.final_decision.reason)
    table.add_row("risk approved", str(result.risk_approved))
    table.add_row("risk reason", result.risk_reason)
    table.add_row("execution action", result.execution_action)
    table.add_row("execution message", result.execution_message)
    console.print(table)


def _render_backtest_result(result: BacktestResult) -> None:
    """Печатает сводку backtest через rich-таблицу."""

    table = Table(title=f"Backtest {result.symbol} {result.interval}")
    table.add_column("metric")
    table.add_column("value")
    table.add_row("symbol", result.symbol)
    table.add_row("interval", result.interval)
    table.add_row("candles used", str(result.candles_used))
    table.add_row("initial balance", _format_decimal(result.initial_balance))
    table.add_row("final balance", _format_decimal(result.final_balance))
    table.add_row("total pnl", _format_decimal(result.total_pnl))
    table.add_row("total pnl %", _format_decimal(result.total_pnl_pct))
    table.add_row("total trades", str(result.total_trades))
    table.add_row("winning trades", str(result.winning_trades))
    table.add_row("losing trades", str(result.losing_trades))
    table.add_row("winrate %", _format_decimal(result.winrate_pct))
    table.add_row("max drawdown %", _format_decimal(result.max_drawdown_pct))
    table.add_row("largest win", _format_decimal(result.largest_win))
    table.add_row("largest loss", _format_decimal(result.largest_loss))
    console.print(table)


def _render_history_result(result: HistoricalLoadResult) -> None:
    """Печатает сводку по завершённой исторической загрузке."""

    table = Table(title=f"History load {result.symbol} {result.interval}")
    table.add_column("metric")
    table.add_column("value")
    table.add_row("days", str(result.days))
    table.add_row("chunks loaded", str(result.chunks_loaded))
    table.add_row("candles saved", str(result.candles_saved))
    table.add_row("started at", result.started_at.isoformat())
    table.add_row("finished at", result.finished_at.isoformat())
    table.add_row("first open time", result.first_open_time.isoformat() if result.first_open_time else "-")
    table.add_row("last open time", result.last_open_time.isoformat() if result.last_open_time else "-")
    console.print(table)


@app.command("health")
def health() -> None:
    """Проверяет, что приложение импортируется и sync-БД доступна."""

    console.print("OK: app loaded")
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        console.print("OK: database connected")
    except Exception as exc:
        console.print(f"ERROR: database unavailable - {exc}")
        raise typer.Exit(code=1) from exc


@app.command("async-health")
def async_health() -> None:
    """Проверяет, что async engine создаётся и async-БД отвечает."""

    async def _check() -> None:
        async with async_session_scope() as session:
            await session.execute(text("SELECT 1"))

    try:
        asyncio.run(_check())
        console.print("OK: async database connected")
    except Exception as exc:
        console.print(f"ERROR: async database unavailable - {exc}")
        raise typer.Exit(code=1) from exc


@app.command("fetch-candles")
def fetch_candles(
    symbol: str = typer.Option(None, help="Торговый символ, например BTCUSDT."),
    interval: str = typer.Option(None, help="Таймфрейм Binance, например 15m."),
    limit: int = typer.Option(None, help="Количество свечей для загрузки."),
) -> None:
    """Загружает свечи с Binance и сохраняет их в БД."""

    settings = get_settings()
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval
    limit = limit or settings.default_candle_limit

    service = CandleService()
    saved_count = asyncio.run(service.fetch_and_store_candles(symbol=symbol, interval=interval, limit=limit))
    console.print(f"Loaded candles: {limit}")
    console.print(f"Saved/updated: {saved_count}")


@app.command("load-history")
def load_history(
    symbol: str = typer.Option(None, help="Торговый символ, например BTCUSDT."),
    interval: str = typer.Option(None, help="Таймфрейм Binance, например 15m."),
    days: int = typer.Option(365, help="За сколько последних дней загрузить историю."),
) -> None:
    """Загружает историю свечей Binance чанками и сохраняет её в БД."""

    settings = get_settings()
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval
    loader = HistoricalLoader()

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed} chunks"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task(f"Loading history {symbol} {interval}", total=None)

        def on_progress(_chunks_loaded: int, _candles_saved: int, _cursor_ms: int) -> None:
            progress.advance(task_id, 1)

        try:
            result = asyncio.run(
                loader.load_history(
                    symbol=symbol,
                    interval=interval,
                    days=days,
                    progress_callback=on_progress,
                )
            )
        except Exception as exc:
            console.print(f"ERROR: {exc}")
            raise typer.Exit(code=1) from exc

    _render_history_result(result)


@app.command("show-candles")
def show_candles(
    symbol: str = typer.Option(None, help="Торговый символ, например BTCUSDT."),
    interval: str = typer.Option(None, help="Таймфрейм Binance, например 15m."),
    limit: int = typer.Option(10, help="Сколько последних свечей показать."),
) -> None:
    """Показывает последние свечи в таблице."""

    settings = get_settings()
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval

    with session_scope() as session:
        candles = analysis_service.load_candles(session=session, symbol=symbol, interval=interval, limit=limit)
    if not candles:
        raise typer.BadParameter("В базе нет свечей для показа. Сначала выполните fetch-candles.")

    table = Table(title=f"Свечи {symbol} {interval}")
    table.add_column("open_time")
    table.add_column("open")
    table.add_column("high")
    table.add_column("low")
    table.add_column("close")
    table.add_column("volume")
    for candle in candles:
        table.add_row(
            candle.open_time.isoformat(),
            str(candle.open),
            str(candle.high),
            str(candle.low),
            str(candle.close),
            str(candle.volume),
        )
    console.print(table)


@app.command("analyze")
def analyze(
    symbol: str = typer.Option(None, help="Торговый символ, например BTCUSDT."),
    interval: str = typer.Option(None, help="Таймфрейм Binance, например 15m."),
) -> None:
    """Считает индикаторы и показывает решение стратегии."""

    settings = get_settings()
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval

    try:
        with session_scope() as session:
            analysis = analysis_service.load_and_analyze(
                session=session,
                symbol=symbol,
                interval=interval,
                limit=settings.default_candle_limit,
            )
        snapshot = analysis.indicator_snapshot
    except IndicatorCalculationError as exc:
        console.print(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        console.print(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Анализ {symbol} {interval}")
    table.add_column("metric")
    table.add_column("value")
    table.add_row("symbol", symbol)
    table.add_row("interval", interval)
    table.add_row("last close", str(snapshot.last_close))
    table.add_row("EMA20", str(snapshot.ema_20))
    table.add_row("EMA50", str(snapshot.ema_50))
    table.add_row("EMA200", str(snapshot.ema_200))
    table.add_row("RSI14", str(snapshot.rsi_14))
    table.add_row("ATR14", str(snapshot.atr_14))
    table.add_row("VolumeSMA20", str(snapshot.volume_sma_20))
    table.add_row("market regime", analysis.market_regime.value)
    table.add_row("decision", analysis.strategy_decision.decision.value)
    table.add_row("reason", analysis.strategy_decision.reason)
    console.print(table)


@app.command("paper-step")
def paper_step(
    symbol: str = typer.Option(None, help="Торговый символ, например BTCUSDT."),
    interval: str = typer.Option(None, help="Таймфрейм Binance, например 15m."),
) -> None:
    """Выполняет один полный цикл paper trading."""

    settings = get_settings()
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval

    service = CandleService()
    asyncio.run(service.fetch_and_store_candles(symbol=symbol, interval=interval, limit=settings.default_candle_limit))

    try:
        with session_scope() as session:
            analysis = analysis_service.load_and_analyze(
                session=session,
                symbol=symbol,
                interval=interval,
                limit=settings.default_candle_limit,
            )
    except IndicatorCalculationError as exc:
        console.print(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        console.print(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc

    with session_scope() as session:
        result = PaperStepService(session).process(
            analysis.strategy_decision,
            indicator_snapshot=analysis.indicator_snapshot,
            latest_candle=analysis.latest_candle,
        )

    _render_paper_step_result(symbol, interval, result)
    if result.has_execution_error:
        raise typer.Exit(code=1)


@app.command("portfolio")
def portfolio() -> None:
    """Показывает состояние paper-портфеля."""

    with session_scope() as session:
        manager = PositionManager(session)
        state = manager.get_portfolio_state()

    summary = Table(title="Paper portfolio")
    summary.add_column("metric")
    summary.add_column("value")
    summary.add_row("USDT balance", str(state.balance_usdt))
    summary.add_row("open positions", str(len(state.open_positions)))
    summary.add_row("realized pnl", str(state.realized_pnl))
    console.print(summary)

    positions_table = Table(title="Open positions")
    positions_table.add_column("symbol")
    positions_table.add_column("side")
    positions_table.add_column("entry_price")
    positions_table.add_column("quantity")
    for position in state.open_positions:
        positions_table.add_row(
            position.symbol,
            position.side,
            str(position.entry_price),
            str(position.quantity),
        )
    console.print(positions_table)


@app.command("backtest")
def backtest(
    symbol: str = typer.Option(None, help="Торговый символ, например BTCUSDT."),
    interval: str = typer.Option(None, help="Таймфрейм Binance, например 15m."),
    limit: int = typer.Option(1000, help="Количество последних свечей для короткого backtest."),
    days: int | None = typer.Option(None, help="Если указан, backtest читает историю из БД за последние N дней."),
) -> None:
    """Запускает исторический backtest по свечам без реальных ордеров."""

    settings = get_settings()
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval

    try:
        engine = BacktestEngine()
        if days is not None:
            with session_scope() as session:
                candles = engine.load_candles_from_db(
                    session=session,
                    symbol=symbol,
                    interval=interval,
                    days=days,
                )
        else:
            asyncio.run(CandleService().fetch_and_store_candles(symbol=symbol, interval=interval, limit=limit))
            with session_scope() as session:
                candles = analysis_service.load_candles(session=session, symbol=symbol, interval=interval, limit=limit)
        result = engine.run(symbol=symbol, interval=interval, candles=candles)
    except IndicatorCalculationError as exc:
        console.print(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        console.print(f"ERROR: {exc}")
        raise typer.Exit(code=1) from exc

    _render_backtest_result(result)


@app.command("paper-runner")
def paper_runner(
    symbol: str = typer.Option(None, help="Торговый символ, например BTCUSDT."),
    interval: str = typer.Option(None, help="Таймфрейм Binance, например 15m."),
) -> None:
    """Запускает безопасный paper-only runner до Ctrl+C."""

    settings = get_settings()
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval

    service = PaperRunnerService()

    def on_iteration(iteration: RunnerIterationResult) -> None:
        console.print(iteration.message)
        if iteration.result is not None:
            _render_paper_step_result(symbol, interval, iteration.result)

    console.print(f"Paper runner started for {symbol} {interval}. Для остановки нажмите Ctrl+C.")
    try:
        asyncio.run(service.run_forever(symbol=symbol, interval=interval, on_iteration=on_iteration))
    except KeyboardInterrupt:
        console.print("Paper runner остановлен пользователем.")


if __name__ == "__main__":
    app()
