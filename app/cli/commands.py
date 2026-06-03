"""CLI commands for the traders server runtime."""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from typing import Any

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
from app.runtime.paper_runner import PaperRunner, RunnerStartResult
from app.execution.paper_runner_service import PaperRunnerService, RunnerIterationResult
from app.analytics.paper_portfolio_analytics import PaperPortfolioAnalyticsService, PortfolioAnalyticsReport
from app.analytics.strategy_performance import (
    SessionComparison,
    SessionPerformanceReport,
    SessionPerformanceSummary,
    StrategyPerformanceService,
)
from app.execution.paper_step_service import PaperStepService
from app.execution.position_manager import PositionManager
from app.history.historical_loader import HistoricalLoadResult, HistoricalLoader
from app.market.analysis_service import MarketAnalysisService
from app.market.candle_service import CandleService
from app.market.indicator_service import IndicatorCalculationError
from app.runtime.strategy_runtime import RuntimeTickResult, StrategyRuntime
from app.strategy.strategy_registry import list_strategies as list_registered_strategies


def _supports_unicode_stream(stream: Any) -> bool:
    """Return True when the target stream can encode the Unicode UI glyphs we use."""

    encoding = getattr(stream, "encoding", None)
    if not encoding:
        return True

    try:
        probe = chr(0x2502) + chr(0x2807)
        probe.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


def _make_console() -> Console:
    """Create a console with ASCII-safe fallback for Windows cp1251 terminals."""

    unicode_output = _supports_unicode_stream(sys.stdout)
    return Console(
        safe_box=not unicode_output,
        emoji=unicode_output,
        highlight=False,
    )


console = _make_console()
app = typer.Typer(help="CLI for the traders server runtime.")
analysis_service = MarketAnalysisService()
_strategy_runtime: StrategyRuntime | None = None
_paper_runner: PaperRunner | None = None


def get_strategy_runtime() -> StrategyRuntime:
    """Лениво создаёт runtime, чтобы import CLI не требовал runtime env."""

    global _strategy_runtime
    if _strategy_runtime is None:
        _strategy_runtime = StrategyRuntime()
    return _strategy_runtime


def get_paper_runner() -> PaperRunner:
    """Лениво создаёт bounded PaperRunner поверх StrategyRuntime."""

    global _paper_runner
    if _paper_runner is None:
        _paper_runner = PaperRunner(runtime=get_strategy_runtime())
    return _paper_runner


def _safe_output_text(value: object, stream: Any | None = None) -> str:
    """Convert text to ASCII escapes when the terminal encoding is too narrow."""

    text_value = str(value)
    output_stream = stream or console.file
    if _supports_unicode_stream(output_stream):
        return text_value
    return text_value.encode("ascii", errors="backslashreplace").decode("ascii")


def _build_progress() -> Progress:
    """Create a progress renderer without Unicode-only widgets on narrow terminals."""

    if _supports_unicode_stream(console.file):
        return Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TextColumn("{task.completed} chunks"),
            TimeElapsedColumn(),
            console=console,
        )

    return Progress(
        TextColumn("{task.description}"),
        TextColumn("{task.completed} chunks"),
        TimeElapsedColumn(),
        console=console,
    )


def _print_error(exc: object, prefix: str = "ERROR") -> None:
    """Print a plain-text-safe error message."""

    console.print(f"{prefix}: {_safe_output_text(exc)}")


def _format_decimal(value: Decimal) -> str:
    """Format Decimal values for compact terminal output."""

    normalized = value.quantize(Decimal("0.00000001")).normalize()
    return format(normalized, "f")


def _render_paper_step_result(symbol: str, interval: str, result: object) -> None:
    """Render a paper-step or runner iteration result."""

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
    """Render a backtest summary."""

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
    """Render a historical-load summary."""

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


def _render_runtime_result(result: RuntimeTickResult, title: str) -> None:
    """Render one runtime tick result."""

    table = Table(title=title)
    table.add_column("field")
    table.add_column("value")
    table.add_row("strategy", result.strategy_decision.strategy_name)
    table.add_row("version", result.strategy_decision.strategy_version)
    table.add_row("symbol", result.strategy_decision.symbol)
    table.add_row("interval", result.strategy_decision.interval)
    table.add_row("strategy action", result.strategy_decision.action)
    table.add_row("final action", result.final_action)
    table.add_row("confidence", f"{result.strategy_decision.confidence:.2f}")
    table.add_row("risk approved", str(result.risk_approved))
    table.add_row("risk reason", result.risk_reason)
    table.add_row("execution action", result.execution_action)
    table.add_row("execution message", result.execution_message)
    table.add_row("candles used", str(result.candles_used))
    table.add_row("market regime", str(result.market_regime))
    if result.decision_id is not None:
        table.add_row("journal id", str(result.decision_id))
    console.print(table)


def _render_runner_start_result(result: RunnerStartResult) -> None:
    """Render bounded runner start result."""

    table = Table(title="Runner session result")
    table.add_column("field")
    table.add_column("value")
    table.add_row("session id", str(result.session_id))
    table.add_row("status", result.status)
    table.add_row("strategy", result.strategy_name)
    table.add_row("version", result.strategy_version)
    table.add_row("symbol", result.symbol)
    table.add_row("interval", result.interval)
    table.add_row("ticks requested", str(result.ticks_requested))
    table.add_row("ticks completed", str(result.ticks_completed))
    table.add_row("last error", result.last_error or "-")
    console.print(table)


def _render_runner_history(items: list[object]) -> None:
    """Render recent runner sessions."""

    table = Table(title="Runner history")
    table.add_column("id")
    table.add_column("status")
    table.add_column("strategy_name")
    table.add_column("strategy_version")
    table.add_column("symbol")
    table.add_column("interval")
    table.add_column("ticks_requested")
    table.add_column("ticks_completed")
    table.add_column("started_at")
    table.add_column("stopped_at")
    table.add_column("last_error")
    for item in items:
        table.add_row(
            str(item.id),
            item.status,
            item.strategy_name,
            item.strategy_version,
            item.symbol,
            item.interval,
            str(item.ticks_requested),
            str(item.ticks_completed),
            item.started_at.isoformat() if item.started_at else "-",
            item.stopped_at.isoformat() if item.stopped_at else "-",
            item.last_error or "-",
        )
    console.print(table)


def _render_runner_ticks(items: list[object], session_id: int) -> None:
    """Render runtime tick audit rows for one session."""

    table = Table(title=f"Runner ticks session {session_id}")
    table.add_column("tick_number")
    table.add_column("strategy_action")
    table.add_column("final_action")
    table.add_column("risk_approved")
    table.add_column("risk_reason")
    table.add_column("execution_action")
    table.add_column("journal_id")
    table.add_column("market_regime")
    table.add_column("candles_used")
    table.add_column("error")
    for item in items:
        table.add_row(
            str(item.tick_number),
            item.strategy_action,
            item.final_action,
            str(item.risk_approved),
            item.risk_reason or "-",
            item.execution_action,
            str(item.journal_id) if item.journal_id is not None else "-",
            item.market_regime or "-",
            str(item.candles_used) if item.candles_used is not None else "-",
            item.error or "-",
        )
    console.print(table)


def _format_optional_decimal(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return _format_decimal(value)


def _format_optional(value: object | None) -> str:
    return "N/A" if value is None else str(value)


def _format_percentage(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def _render_performance_session(report: SessionPerformanceReport, portfolio: PortfolioAnalyticsReport) -> None:
    summary = Table(title=f"Performance session {report.session_id}")
    summary.add_column("metric")
    summary.add_column("value")
    summary.add_row("session id", str(report.session_id))
    summary.add_row("status", report.status)
    summary.add_row("strategy", report.strategy_name)
    summary.add_row("interval", report.interval)
    summary.add_row("symbol", report.symbol)
    summary.add_row("started at", report.started_at.isoformat() if report.started_at else "-")
    summary.add_row("stopped at", report.stopped_at.isoformat() if report.stopped_at else "-")
    summary.add_row("ticks requested", str(report.runtime_quality.ticks_requested))
    summary.add_row("ticks completed", str(report.runtime_quality.ticks_completed))
    summary.add_row("audit ticks", str(report.runtime_quality.audit_ticks_count))
    summary.add_row("error ticks", str(report.runtime_quality.error_ticks_count))
    summary.add_row("success rate", _format_percentage(report.runtime_quality.success_rate))
    summary.add_row(
        "duration seconds",
        str(report.runtime_quality.duration_seconds),
    )
    summary.add_row(
        "average tick duration",
        _format_optional(report.runtime_quality.average_tick_duration_seconds),
    )
    console.print(summary)

    actions_table = Table(title="Strategy and final action counts")
    actions_table.add_column("metric")
    actions_table.add_column("value")
    actions_table.add_row("strategy BUY", str(report.strategy_action_counts.buy))
    actions_table.add_row("strategy SELL", str(report.strategy_action_counts.sell))
    actions_table.add_row("strategy HOLD", str(report.strategy_action_counts.hold))
    actions_table.add_row("final BUY", str(report.final_action_counts.buy))
    actions_table.add_row("final SELL", str(report.final_action_counts.sell))
    actions_table.add_row("final HOLD", str(report.final_action_counts.hold))
    console.print(actions_table)

    risk_table = Table(title="Risk metrics")
    risk_table.add_column("metric")
    risk_table.add_column("value")
    risk_table.add_row("approved", str(report.risk_metrics.approved_count))
    risk_table.add_row("rejected", str(report.risk_metrics.rejected_count))
    risk_table.add_row("approval rate", _format_percentage(report.risk_metrics.approval_rate))
    risk_table.add_row("rejection rate", _format_percentage(report.risk_metrics.rejection_rate))
    console.print(risk_table)

    if report.risk_metrics.rejection_reasons:
        reasons = Table(title="Risk rejection reasons")
        reasons.add_column("reason")
        reasons.add_column("count")
        for reason, count in report.risk_metrics.rejection_reasons.items():
            reasons.add_row(reason, str(count))
        console.print(reasons)

    execution_table = Table(title="Execution metrics")
    execution_table.add_column("metric")
    execution_table.add_column("value")
    execution_table.add_row("executed", str(report.execution_metrics.executed_count))
    execution_table.add_row("skipped", str(report.execution_metrics.skipped_count))
    execution_table.add_row("buy executed", str(report.execution_metrics.buy_executed_count))
    execution_table.add_row("sell executed", str(report.execution_metrics.sell_executed_count))
    execution_table.add_row("hold/noop", str(report.execution_metrics.hold_or_noop_count))
    console.print(execution_table)

    exec_actions = Table(title="Execution actions breakdown")
    exec_actions.add_column("action")
    exec_actions.add_column("count")
    for action, count in report.execution_metrics.execution_actions.items():
        exec_actions.add_row(action, str(count))
    console.print(exec_actions)

    confidence_table = Table(title="Confidence metrics")
    confidence_table.add_column("metric")
    confidence_table.add_column("value")
    confidence_table.add_row("count", str(report.confidence_metrics.count))
    confidence_table.add_row("average", _format_optional_decimal(report.confidence_metrics.average))
    confidence_table.add_row("minimum", _format_optional_decimal(report.confidence_metrics.minimum))
    confidence_table.add_row("maximum", _format_optional_decimal(report.confidence_metrics.maximum))
    console.print(confidence_table)

    regime_table = Table(title="Market regimes")
    regime_table.add_column("regime")
    regime_table.add_column("count")
    for regime, count in report.market_regime_metrics.regimes.items():
        regime_table.add_row(regime, str(count))
    console.print(regime_table)

    candles_table = Table(title="Candles used")
    candles_table.add_column("metric")
    candles_table.add_column("value")
    candles_table.add_row("min", _format_optional(report.candles_used_min))
    candles_table.add_row("max", _format_optional(report.candles_used_max))
    candles_table.add_row("average", _format_optional(report.candles_used_average))
    console.print(candles_table)

    if report.errors:
        errors_table = Table(title="Errors")
        errors_table.add_column("message")
        for error in report.errors:
            errors_table.add_row(error)
        console.print(errors_table)

    portfolio_table = Table(title="Portfolio analytics")
    portfolio_table.add_column("metric")
    portfolio_table.add_column("value")
    portfolio_table.add_row("realized pnl", _format_optional_decimal(portfolio.realized_pnl))
    portfolio_table.add_row("unrealized pnl", _format_optional_decimal(portfolio.unrealized_pnl))
    portfolio_table.add_row("total pnl", _format_optional_decimal(portfolio.total_pnl))
    portfolio_table.add_row("return pct", _format_optional_decimal(portfolio.return_pct))
    portfolio_table.add_row("data quality", portfolio.data_quality)
    portfolio_table.add_row("unavailable reason", portfolio.unavailable_reason or "-")
    console.print(portfolio_table)


def _render_performance_history(items: list[SessionPerformanceSummary]) -> None:
    table = Table(title="Performance history")
    table.add_column("session id")
    table.add_column("status")
    table.add_column("strategy")
    table.add_column("symbol")
    table.add_column("interval")
    table.add_column("ticks completed")
    table.add_column("risk rejection rate")
    table.add_column("skipped executions")
    table.add_column("avg confidence")
    table.add_column("total pnl")
    table.add_column("return pct")
    table.add_column("data quality")
    for item in items:
        table.add_row(
            str(item.session_id),
            item.status,
            item.strategy_name,
            item.symbol,
            item.interval,
            str(item.ticks_completed),
            _format_percentage(item.risk_rejection_rate),
            str(item.execution_skipped_count),
            _format_optional_decimal(item.average_confidence),
            _format_optional_decimal(item.total_pnl),
            _format_optional_decimal(item.return_pct),
            item.data_quality or "N/A",
        )
    console.print(table)


def _render_performance_compare(items: list[SessionComparison]) -> None:
    table = Table(title="Performance compare")
    table.add_column("session id")
    table.add_column("strategy")
    table.add_column("symbol")
    table.add_column("interval")
    table.add_column("ticks completed")
    table.add_column("BUY")
    table.add_column("SELL")
    table.add_column("HOLD")
    table.add_column("risk rejection")
    table.add_column("skipped")
    table.add_column("avg confidence")
    table.add_column("total pnl")
    table.add_column("return pct")
    table.add_column("status")
    table.add_column("data quality")
    for item in items:
        table.add_row(
            str(item.session_id),
            item.strategy_name,
            item.symbol,
            item.interval,
            str(item.ticks_completed),
            str(item.final_buy_count),
            str(item.final_sell_count),
            str(item.final_hold_count),
            _format_percentage(item.risk_rejection_rate),
            str(item.execution_skipped_count),
            _format_optional_decimal(item.average_confidence),
            _format_optional_decimal(item.total_pnl),
            _format_optional_decimal(item.return_pct),
            item.status,
            item.data_quality or "N/A",
        )
    console.print(table)


def _render_portfolio_analytics(report: PortfolioAnalyticsReport) -> None:
    table = Table(title=f"Portfolio analytics {report.symbol}")
    table.add_column("metric")
    table.add_column("value")
    table.add_row("symbol", report.symbol)
    table.add_row("quote asset", report.quote_asset)
    table.add_row("available cash", _format_optional_decimal(report.available_cash))
    table.add_row("locked cash", _format_optional_decimal(report.locked_cash))
    table.add_row("open position qty", _format_optional_decimal(report.open_position_qty))
    table.add_row("open position avg price", _format_optional_decimal(report.open_position_avg_price))
    table.add_row("latest mark price", _format_optional_decimal(report.latest_mark_price))
    table.add_row("estimated position value", _format_optional_decimal(report.estimated_position_value))
    table.add_row("estimated equity", _format_optional_decimal(report.estimated_equity))
    table.add_row("realized pnl", _format_optional_decimal(report.realized_pnl))
    table.add_row("unrealized pnl", _format_optional_decimal(report.unrealized_pnl))
    table.add_row("total pnl", _format_optional_decimal(report.total_pnl))
    table.add_row("return pct", _format_optional_decimal(report.return_pct))
    table.add_row("data quality", report.data_quality)
    table.add_row("unavailable reason", report.unavailable_reason or "-")
    console.print(table)


@app.command("health")
def health() -> None:
    """Verify that the app imports and the sync database is reachable."""

    console.print("OK: app loaded")
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
        console.print("OK: database connected")
    except Exception as exc:
        _print_error(f"database unavailable - {exc}")
        raise typer.Exit(code=1) from exc


@app.command("async-health")
def async_health() -> None:
    """Verify that the async engine is created and the async database responds."""

    async def _check() -> None:
        async with async_session_scope() as session:
            await session.execute(text("SELECT 1"))

    try:
        asyncio.run(_check())
        console.print("OK: async database connected")
    except Exception as exc:
        _print_error(f"async database unavailable - {exc}")
        raise typer.Exit(code=1) from exc


@app.command("strategy-list")
def strategy_list() -> None:
    """Show registered strategies."""

    table = Table(title="Available strategies")
    table.add_column("strategy")
    for name in list_registered_strategies():
        table.add_row(name)
    console.print(table)


@app.command("strategy-run")
def strategy_run(
    strategy: str = typer.Option(None, help="Strategy name."),
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
    interval: str = typer.Option(None, help="Binance interval, for example 15m."),
) -> None:
    """Run exactly one bounded strategy tick."""

    settings = get_settings()
    strategy_name = strategy or settings.strategy_default_name
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval

    try:
        result = get_strategy_runtime().run_tick(strategy_name, symbol, interval)
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    _render_runtime_result(result, f"Strategy run {strategy_name} {symbol} {interval}")


@app.command("strategy-loop")
def strategy_loop(
    strategy: str = typer.Option(None, help="Strategy name."),
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
    interval: str = typer.Option(None, help="Binance interval, for example 15m."),
    ticks: int = typer.Option(None, help="How many bounded ticks to execute."),
    sleep_seconds: float = typer.Option(None, help="Pause between ticks."),
) -> None:
    """Run a bounded strategy loop and stop after N ticks."""

    settings = get_settings()
    strategy_name = strategy or settings.strategy_default_name
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval
    loop_ticks = ticks if ticks is not None else settings.strategy_max_ticks
    loop_sleep = sleep_seconds if sleep_seconds is not None else float(settings.strategy_loop_sleep_seconds)

    try:
        results = get_strategy_runtime().run_loop(
            strategy_name=strategy_name,
            symbol=symbol,
            interval=interval,
            ticks=loop_ticks,
            sleep_seconds=loop_sleep,
        )
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    for index, result in enumerate(results, start=1):
        _render_runtime_result(result, f"Strategy loop tick {index}/{loop_ticks}")


@app.command("runner-start")
def runner_start(
    strategy: str = typer.Option(None, help="Strategy name."),
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
    interval: str = typer.Option(None, help="Binance interval, for example 15m."),
    ticks: int = typer.Option(None, help="How many bounded ticks to execute."),
    sleep_seconds: float = typer.Option(None, help="Pause between ticks."),
) -> None:
    """Run a bounded paper runner session and persist tick audit."""

    settings = get_settings()
    strategy_name = strategy or settings.strategy_default_name
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval
    loop_ticks = ticks if ticks is not None else settings.strategy_max_ticks
    loop_sleep = sleep_seconds if sleep_seconds is not None else float(settings.strategy_loop_sleep_seconds)

    try:
        result = get_paper_runner().start(
            strategy_name=strategy_name,
            symbol=symbol,
            interval=interval,
            ticks=loop_ticks,
            sleep_seconds=loop_sleep,
        )
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    _render_runner_start_result(result)


@app.command("runner-history")
def runner_history(limit: int = typer.Option(10, help="How many recent runner sessions to show.")) -> None:
    """Show recent bounded runner sessions."""

    try:
        items = get_paper_runner().list_sessions(limit=limit)
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    _render_runner_history(items)


@app.command("runner-ticks")
def runner_ticks(session_id: int = typer.Option(..., help="Runner session id.")) -> None:
    """Show runtime tick audit rows for one bounded runner session."""

    try:
        items = get_paper_runner().list_ticks(session_id=session_id)
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    _render_runner_ticks(items, session_id)


@app.command("performance-session")
def performance_session(session_id: int = typer.Option(..., help="Runner session id.")) -> None:
    """Show detailed performance report for one runner session."""

    try:
        report = StrategyPerformanceService().get_session_performance(session_id)
        portfolio = PaperPortfolioAnalyticsService().analyze_symbol(report.symbol)
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    _render_performance_session(report, portfolio)


@app.command("performance-history")
def performance_history(limit: int = typer.Option(10, help="How many recent performance summaries to show.")) -> None:
    """Show recent runner session performance summaries."""

    try:
        items = StrategyPerformanceService().list_session_performance(limit=limit)
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    _render_performance_history(items)


@app.command("performance-compare")
def performance_compare(
    strategy: str | None = typer.Option(None, help="Strategy name to filter."),
    symbol: str | None = typer.Option(None, help="Symbol to filter."),
    limit: int = typer.Option(10, help="How many sessions to compare."),
) -> None:
    """Compare recent runner session performance by strategy and symbol."""

    try:
        items = StrategyPerformanceService().compare_sessions(
            strategy_name=strategy,
            symbol=symbol,
            limit=limit,
        )
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    _render_performance_compare(items)


@app.command("portfolio-analytics")
def portfolio_analytics(
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
) -> None:
    """Show paper portfolio analytics for selected symbol."""

    settings = get_settings()
    normalized_symbol = symbol or settings.default_symbol

    try:
        report = PaperPortfolioAnalyticsService().analyze_symbol(normalized_symbol)
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    _render_portfolio_analytics(report)


@app.command("fetch-candles")
def fetch_candles(
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
    interval: str = typer.Option(None, help="Binance interval, for example 15m."),
    limit: int = typer.Option(None, help="Number of candles to fetch."),
) -> None:
    """Fetch candles from Binance and store them in the database."""

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
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
    interval: str = typer.Option(None, help="Binance interval, for example 15m."),
    days: int = typer.Option(365, help="How many recent days of history to load."),
) -> None:
    """Load historical Binance candles in chunks and store them in the database."""

    settings = get_settings()
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval
    loader = HistoricalLoader()

    with _build_progress() as progress:
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
            _print_error(exc)
            raise typer.Exit(code=1) from exc

    _render_history_result(result)


@app.command("show-candles")
def show_candles(
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
    interval: str = typer.Option(None, help="Binance interval, for example 15m."),
    limit: int = typer.Option(10, help="How many recent candles to display."),
) -> None:
    """Show recent candles from the database."""

    settings = get_settings()
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval

    with session_scope() as session:
        candles = analysis_service.load_candles(session=session, symbol=symbol, interval=interval, limit=limit)
    if not candles:
        raise typer.BadParameter("No candles found in the database. Run fetch-candles first.")

    table = Table(title=f"Candles {symbol} {interval}")
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
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
    interval: str = typer.Option(None, help="Binance interval, for example 15m."),
) -> None:
    """Calculate indicators and print the strategy decision."""

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
        _print_error(exc)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Analysis {symbol} {interval}")
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
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
    interval: str = typer.Option(None, help="Binance interval, for example 15m."),
) -> None:
    """Run one full paper-trading step."""

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
        _print_error(exc)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _print_error(exc)
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
    """Show the current paper portfolio."""

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
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
    interval: str = typer.Option(None, help="Binance interval, for example 15m."),
    limit: int = typer.Option(1000, help="How many recent candles to use for a short backtest."),
    days: int | None = typer.Option(None, help="If set, load candles from the database for the last N days."),
) -> None:
    """Run a historical backtest without real orders."""

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
        _print_error(exc)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _print_error(exc)
        raise typer.Exit(code=1) from exc

    _render_backtest_result(result)


@app.command("paper-runner")
def paper_runner(
    symbol: str = typer.Option(None, help="Trading symbol, for example BTCUSDT."),
    interval: str = typer.Option(None, help="Binance interval, for example 15m."),
) -> None:
    """Start the safe paper-only runner until Ctrl+C."""

    settings = get_settings()
    symbol = symbol or settings.default_symbol
    interval = interval or settings.default_interval

    service = PaperRunnerService()

    def on_iteration(iteration: RunnerIterationResult) -> None:
        console.print(_safe_output_text(iteration.message))
        if iteration.result is not None:
            _render_paper_step_result(symbol, interval, iteration.result)

    console.print(f"Paper runner started for {symbol} {interval}. Press Ctrl+C to stop.")
    try:
        asyncio.run(service.run_forever(symbol=symbol, interval=interval, on_iteration=on_iteration))
    except KeyboardInterrupt:
        console.print("Paper runner stopped by user.")


if __name__ == "__main__":
    app()
