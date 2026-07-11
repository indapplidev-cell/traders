from __future__ import annotations

from collections.abc import Callable, Sequence

from app.market_reader.multi_symbol_preview import DEFAULT_MULTI_SYMBOLS, parse_symbols
from app.market_reader.timeline_preview import TimelinePreviewConfig, build_window_labels


InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]


def prompt_timeline_config(
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> TimelinePreviewConfig | None:
    symbols = prompt_timeline_symbols(input_func=input_func, output_func=output_func)
    interval = prompt_timeline_interval(input_func=input_func, output_func=output_func)
    window_size = prompt_timeline_window_size(input_func=input_func, output_func=output_func)
    window_count = prompt_timeline_window_count(input_func=input_func, output_func=output_func)

    config = TimelinePreviewConfig(
        symbols=symbols,
        interval=interval,
        window_size=window_size,
        window_count=window_count,
        min_candles=50,
    )

    if not prompt_timeline_confirm_run(config, input_func=input_func, output_func=output_func):
        output_func("Cancelled.")
        return None

    return config


def prompt_timeline_symbols(
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> tuple[str, ...]:
    choices = {
        "": DEFAULT_MULTI_SYMBOLS,
        "1": DEFAULT_MULTI_SYMBOLS,
        "2": ("BTCUSDT", "ETHUSDT"),
        "3": ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"),
        "4": ("BTCUSDT",),
        "5": ("ETHUSDT",),
        "6": ("SOLUSDT",),
    }
    while True:
        answer = _ask(
            input_func,
            output_func,
            "\n".join(
                [
                    "BOOK-L1 Market Regime Timeline",
                    "",
                    "Choose symbol set:",
                    "",
                    "1) BTCUSDT, ETHUSDT, SOLUSDT  [default]",
                    "2) BTCUSDT, ETHUSDT",
                    "3) BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT",
                    "4) BTCUSDT only",
                    "5) ETHUSDT only",
                    "6) SOLUSDT only",
                    "7) Enter list manually",
                    "",
                    "Enter option number and press Enter.",
                    "Enter without input = option 1:",
                    "> ",
                ]
            ),
        )
        if answer in choices:
            return choices[answer]
        if answer == "7":
            return _prompt_manual_symbols(input_func=input_func, output_func=output_func)
        output_func("Invalid input. Try again.")


def prompt_timeline_interval(
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> str:
    choices = {
        "": "15m",
        "1": "15m",
        "2": "1m",
        "3": "5m",
        "4": "30m",
        "5": "1h",
        "6": "4h",
        "7": "1d",
    }
    while True:
        answer = _ask(
            input_func,
            output_func,
            "\n".join(
                [
                    "Choose candle interval:",
                    "",
                    "1) 15m  [default]",
                    "2) 1m",
                    "3) 5m",
                    "4) 30m",
                    "5) 1h",
                    "6) 4h",
                    "7) 1d",
                    "8) Enter manually",
                    "",
                    "Enter option number and press Enter.",
                    "Enter without input = option 1:",
                    "> ",
                ]
            ),
        )
        if answer in choices:
            return choices[answer]
        if answer == "8":
            interval = _ask(input_func, output_func, "Enter candle interval:\n> ").strip()
            if interval:
                return interval
            output_func("Interval must not be empty. Try again.")
            continue
        output_func("Invalid input. Try again.")


def prompt_timeline_window_size(
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> int:
    choices = {
        "": 300,
        "1": 300,
        "2": 100,
        "3": 500,
    }
    while True:
        answer = _ask(
            input_func,
            output_func,
            "\n".join(
                [
                    "Choose one window size:",
                    "",
                    "1) 300 candles  [default]",
                    "2) 100 candles",
                    "3) 500 candles",
                    "4) Enter manually",
                    "",
                    "Enter option number and press Enter.",
                    "Enter without input = option 1:",
                    "> ",
                ]
            ),
        )
        if answer in choices:
            return choices[answer]
        if answer == "4":
            manual = _ask(input_func, output_func, "Enter one window size:\n> ").strip()
            try:
                window_size = int(manual)
            except ValueError:
                output_func("Window size must be a number. Try again.")
                continue
            if window_size >= 50:
                return window_size
            output_func("Window size must be at least 50. Try again.")
            continue
        output_func("Invalid input. Try again.")


def prompt_timeline_window_count(
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> int:
    choices = {
        "": 4,
        "1": 4,
        "2": 3,
        "3": 5,
        "4": 6,
    }
    while True:
        answer = _ask(
            input_func,
            output_func,
            "\n".join(
                [
                    "Choose timeline window count:",
                    "",
                    "1) 4 windows: W-3, W-2, W-1, Current  [default]",
                    "2) 3 windows: W-2, W-1, Current",
                    "3) 5 windows: W-4, W-3, W-2, W-1, Current",
                    "4) 6 windows",
                    "5) Enter manually from 2 to 6",
                    "",
                    "Enter option number and press Enter.",
                    "Enter without input = option 1:",
                    "> ",
                ]
            ),
        )
        if answer in choices:
            return choices[answer]
        if answer == "5":
            manual = _ask(input_func, output_func, "Enter timeline window count from 2 to 6:\n> ").strip()
            try:
                window_count = int(manual)
            except ValueError:
                output_func("Window count must be a number. Try again.")
                continue
            if 2 <= window_count <= 6:
                return window_count
            output_func("Window count must be from 2 to 6. Try again.")
            continue
        output_func("Invalid input. Try again.")


def prompt_timeline_confirm_run(
    config: TimelinePreviewConfig,
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> bool:
    while True:
        answer = _ask(
            input_func,
            output_func,
            "\n".join(
                [
                    "Run parameters:",
                    "",
                    f"Symbols: {', '.join(config.symbols)}",
                    f"Interval: {config.interval}",
                    f"Window size: {config.window_size} candles",
                    f"Window count: {config.window_count}",
                    f"Window labels: {', '.join(build_window_labels(config.window_count))}",
                    f"Required candles per symbol: {config.required_candles}",
                    f"Min candles per window: {config.min_candles}",
                    "",
                    "Run analysis?",
                    "",
                    "1) Yes  [default]",
                    "2) No, cancel",
                    "",
                    "Enter without input = option 1:",
                    "> ",
                ]
            ),
        )
        if answer in {"", "1"}:
            return True
        if answer == "2":
            return False
        output_func("Invalid input. Try again.")


def prompt_timeline_details_choice(
    symbols: Sequence[str],
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> tuple[str, ...]:
    while True:
        answer = _ask(
            input_func,
            output_func,
            "\n".join(
                [
                    "Show details by symbol?",
                    "",
                    "1) No  [default]",
                    "2) Yes",
                    "",
                    "Enter without input = option 1:",
                    "> ",
                ]
            ),
        )
        if answer in {"", "1"}:
            return ()
        if answer == "2":
            return _prompt_details_symbol(symbols, input_func=input_func, output_func=output_func)
        output_func("Invalid input. Try again.")


def prompt_timeline_export_choice(
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> str:
    choices = {
        "": "none",
        "1": "none",
        "2": "all",
        "3": "json",
        "4": "md",
    }
    while True:
        answer = _ask(
            input_func,
            output_func,
            "\n".join(
                [
                    "Save result to files?",
                    "",
                    "1) No  [default]",
                    "2) Yes, JSON + Markdown",
                    "3) JSON only",
                    "4) Markdown only",
                    "",
                    "Enter option number and press Enter.",
                    "Enter without input = option 1:",
                    "> ",
                ]
            ),
        )
        if answer in choices:
            return choices[answer]
        output_func("Invalid input. Try again.")


def _prompt_manual_symbols(
    *,
    input_func: InputFunc,
    output_func: OutputFunc,
) -> tuple[str, ...]:
    while True:
        answer = _ask(
            input_func,
            output_func,
            "\n".join(
                [
                    "Enter symbols separated by comma, for example:",
                    "BTCUSDT,ETHUSDT,SOLUSDT",
                    "> ",
                ]
            ),
        )
        try:
            symbols = parse_symbols(answer)
        except ValueError:
            symbols = ()
        if symbols:
            return symbols
        output_func("Symbol list must not be empty. Try again.")


def _prompt_details_symbol(
    symbols: Sequence[str],
    *,
    input_func: InputFunc,
    output_func: OutputFunc,
) -> tuple[str, ...]:
    while True:
        lines = ["Choose symbol for details:", ""]
        for index, symbol in enumerate(symbols, start=1):
            lines.append(f"{index}) {symbol}")
        lines.append(f"{len(symbols) + 1}) All")
        lines.extend(["", "Enter option number:", "> "])

        answer = _ask(input_func, output_func, "\n".join(lines))
        try:
            choice = int(answer)
        except ValueError:
            output_func("Invalid input. Try again.")
            continue

        if 1 <= choice <= len(symbols):
            return (symbols[choice - 1],)
        if choice == len(symbols) + 1:
            return tuple(symbols)
        output_func("Invalid input. Try again.")


def _ask(input_func: InputFunc, output_func: OutputFunc, prompt: str) -> str:
    output_func(prompt)
    return input_func("").strip()
