from __future__ import annotations

from collections.abc import Callable, Sequence

from app.market_reader.multi_symbol_preview import (
    DEFAULT_MULTI_SYMBOLS,
    MultiSymbolPreviewConfig,
    parse_symbols,
)


InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]


def prompt_multi_symbol_config(
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> MultiSymbolPreviewConfig | None:
    symbols = prompt_symbol_set(input_func=input_func, output_func=output_func)
    reference_mode, reference_date = prompt_reference_date(input_func=input_func, output_func=output_func)
    limit = prompt_limit(input_func=input_func, output_func=output_func)
    interval = prompt_interval(input_func=input_func, output_func=output_func)

    config = MultiSymbolPreviewConfig(
        symbols=symbols,
        interval=interval,
        limit=limit,
        min_candles=50,
        reference_mode=reference_mode,
        reference_date=reference_date,
    )

    if not prompt_confirm_run(config, input_func=input_func, output_func=output_func):
        output_func("Cancelled.")
        return None

    return config


def prompt_symbol_set(
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
                    "BOOK-L1 Multi-Symbol Market Reader",
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
            return prompt_manual_symbols(input_func=input_func, output_func=output_func)
        output_func("Неверный ввод. Попробуй еще раз.")


def prompt_manual_symbols(
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


def prompt_reference_date(
    *,
    input_func: InputFunc = input,
    output_func: OutputFunc = print,
) -> tuple[str, str | None]:
    while True:
        answer = _ask(
            input_func,
            output_func,
            "\n".join(
                [
                    "Выбери дату отсчёта:",
                    "",
                    "1) Последняя доступная свеча в БД  [default]",
                    "2) Ввести дату вручную",
                    "",
                    "Ответь номером пункта и нажми Enter.",
                    "Enter без ввода = пункт 1:",
                    "> ",
                ]
            ),
        )
        if answer in {"", "1"}:
            return "latest", None
        if answer == "2":
            reference_date = _ask(
                input_func,
                output_func,
                "\n".join(
                    [
                        "Введи дату отсчёта в формате YYYY-MM-DD или YYYY-MM-DD HH:MM:",
                        "> ",
                    ]
                ),
            ).strip()
            if reference_date:
                return "manual", reference_date
            output_func("Дата не должна быть пустой. Попробуй еще раз.")
            continue
        output_func("Неверный ввод. Попробуй еще раз.")


def prompt_limit(
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
                    "Выбери временной диапазон анализа:",
                    "",
                    "1) Последние 300 свечей  [default]",
                    "2) Последние 100 свечей",
                    "3) Последние 500 свечей",
                    "4) Ввести limit вручную",
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
            manual = _ask(input_func, output_func, "Введи limit:\n> ").strip()
            try:
                limit = int(manual)
            except ValueError:
                output_func("Limit должен быть числом. Попробуй еще раз.")
                continue
            if limit >= 50:
                return limit
            output_func("Limit должен быть не меньше 50. Попробуй еще раз.")
            continue
        output_func("Неверный ввод. Попробуй еще раз.")


def prompt_interval(
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


def prompt_confirm_run(
    config: MultiSymbolPreviewConfig,
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
                    f"Reference date: {_format_reference_date(config)}",
                    f"Range: last {config.limit} candles",
                    f"Min candles: {config.min_candles}",
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


def prompt_details_choice(
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


def _format_reference_date(config: MultiSymbolPreviewConfig) -> str:
    if config.reference_mode == "manual":
        return config.reference_date or "manual"
    return "latest available candle"
