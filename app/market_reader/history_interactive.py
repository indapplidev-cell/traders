from __future__ import annotations

from collections.abc import Callable, Sequence

from app.market_reader.history_snapshot import HistorySnapshotConfig
from app.market_reader.multi_symbol_preview import DEFAULT_MULTI_SYMBOLS, parse_symbols


InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]


def prompt_history_config(
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> HistorySnapshotConfig | None:
    symbols = prompt_history_symbols(input_func=input_func, output_func=output_func)
    interval = prompt_history_interval(input_func=input_func, output_func=output_func)
    limit = prompt_history_limit(input_func=input_func, output_func=output_func)

    output_func(f"Для сравнения будет загружено {limit * 2} свечей на каждый symbol.")

    config = HistorySnapshotConfig(
        symbols=symbols,
        interval=interval,
        limit=limit,
        min_candles=50,
    )

    if not prompt_history_confirm_run(config, input_func=input_func, output_func=output_func):
        output_func("Cancelled.")
        return None

    return config


def prompt_history_symbols(
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
                    "BOOK-L1 History Snapshot",
                    "",
                    "Выбери набор symbol:",
                    "",
                    "1) BTCUSDT, ETHUSDT, SOLUSDT  [default]",
                    "2) BTCUSDT, ETHUSDT",
                    "3) BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT",
                    "4) Только BTCUSDT",
                    "5) Только ETHUSDT",
                    "6) Только SOLUSDT",
                    "7) Ввести список вручную",
                    "",
                    "Ответь номером пункта и нажми Enter.",
                    "Enter без ввода = пункт 1:",
                    "> ",
                ]
            ),
        )
        if answer in choices:
            return choices[answer]
        if answer == "7":
            return _prompt_manual_symbols(input_func=input_func, output_func=output_func)
        output_func("Неверный ввод. Попробуй еще раз.")


def prompt_history_interval(
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
                    "Выбери интервал свечей:",
                    "",
                    "1) 15m  [default]",
                    "2) 1m",
                    "3) 5m",
                    "4) 30m",
                    "5) 1h",
                    "6) 4h",
                    "7) 1d",
                    "8) Ввести вручную",
                    "",
                    "Ответь номером пункта и нажми Enter.",
                    "Enter без ввода = пункт 1:",
                    "> ",
                ]
            ),
        )
        if answer in choices:
            return choices[answer]
        if answer == "8":
            interval = _ask(input_func, output_func, "Введи интервал свечей:\n> ").strip()
            if interval:
                return interval
            output_func("Интервал не должен быть пустым. Попробуй еще раз.")
            continue
        output_func("Неверный ввод. Попробуй еще раз.")


def prompt_history_limit(
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
                    "Выбери размер одного окна:",
                    "",
                    "1) 300 свечей  [default]",
                    "2) 100 свечей",
                    "3) 500 свечей",
                    "4) Ввести вручную",
                    "",
                    "Ответь номером пункта и нажми Enter.",
                    "Enter без ввода = пункт 1:",
                    "> ",
                ]
            ),
        )
        if answer in choices:
            return choices[answer]
        if answer == "4":
            manual = _ask(input_func, output_func, "Введи размер одного окна:\n> ").strip()
            try:
                limit = int(manual)
            except ValueError:
                output_func("Размер окна должен быть числом. Попробуй еще раз.")
                continue
            if limit >= 50:
                return limit
            output_func("Размер окна должен быть не меньше 50. Попробуй еще раз.")
            continue
        output_func("Неверный ввод. Попробуй еще раз.")


def prompt_history_confirm_run(
    config: HistorySnapshotConfig,
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
                    "Параметры запуска:",
                    "",
                    f"Symbols: {', '.join(config.symbols)}",
                    f"Interval: {config.interval}",
                    f"Current window: last {config.limit} candles",
                    f"Previous window: previous {config.limit} candles",
                    f"Required candles per symbol: {config.required_candles_per_symbol}",
                    f"Min candles per window: {config.min_candles}",
                    "",
                    "Запустить анализ?",
                    "",
                    "1) Да  [default]",
                    "2) Нет, отменить",
                    "",
                    "Enter без ввода = пункт 1:",
                    "> ",
                ]
            ),
        )
        if answer in {"", "1"}:
            return True
        if answer == "2":
            return False
        output_func("Неверный ввод. Попробуй еще раз.")


def prompt_history_details_choice(
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
                    "Показать подробности по symbol?",
                    "",
                    "1) Нет  [default]",
                    "2) Да",
                    "",
                    "Enter без ввода = пункт 1:",
                    "> ",
                ]
            ),
        )
        if answer in {"", "1"}:
            return ()
        if answer == "2":
            return _prompt_details_symbol(symbols, input_func=input_func, output_func=output_func)
        output_func("Неверный ввод. Попробуй еще раз.")


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
                    "Введи symbol через запятую, например:",
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
        output_func("Список symbol не должен быть пустым. Попробуй еще раз.")


def _prompt_details_symbol(
    symbols: Sequence[str],
    *,
    input_func: InputFunc,
    output_func: OutputFunc,
) -> tuple[str, ...]:
    while True:
        lines = ["Выбери symbol для подробностей:", ""]
        for index, symbol in enumerate(symbols, start=1):
            lines.append(f"{index}) {symbol}")
        lines.append(f"{len(symbols) + 1}) Все")
        lines.extend(["", "Ответь номером пункта:", "> "])

        answer = _ask(input_func, output_func, "\n".join(lines))
        try:
            choice = int(answer)
        except ValueError:
            output_func("Неверный ввод. Попробуй еще раз.")
            continue

        if 1 <= choice <= len(symbols):
            return (symbols[choice - 1],)
        if choice == len(symbols) + 1:
            return tuple(symbols)
        output_func("Неверный ввод. Попробуй еще раз.")


def _ask(input_func: InputFunc, output_func: OutputFunc, prompt: str) -> str:
    output_func(prompt)
    return input_func("").strip()
