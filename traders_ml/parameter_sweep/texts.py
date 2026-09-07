"""Authoritative Russian UI text catalogue, ready for future locale variants."""

RU = {
    "title": "Исследование параметров Scalping v2",
    "ready": "Статус: Готово к запуску",
    "preparing": "Статус: Подготовка исследования...",
    "preflight": "Проверка базы данных · режима только для чтения · набора данных · конфигурации",
    "planning": "Статус: Построение пространства поиска",
    "research_parameters": "Параметры исследования",
    "current_combination": "Текущая комбинация",
    "not_started": "Комбинация ещё не запущена",
    "running": "Статус: Выполняется исследование параметров",
    "writing": "Статус: Идёт запись результатов в файл...",
    "saved": "Результат комбинации {index} сохранён",
    "finalizing": "Статус: Завершение обработки результатов...",
    "integrity": "Статус: Идёт проверка целостности файлов...",
    "completed": "Обработка {count} комбинаций окончена.",
    "cancel_requested": "Статус: Остановка после завершения текущей комбинации...",
    "cancelled": "Исследование остановлено после сохранения текущей комбинации.",
    "failed": "Исследование остановлено из-за ошибки.",
    "failed_before_first": "Исследование остановлено до запуска первой комбинации.\nНи одна комбинация не была обработана.",
    "replay_diagnostics": "Диагностика replay",
    "new_observations_required": "Для нового запуска требуется накопление дополнительных historical replay observations.",
    "start": "Запустить",
    "stop": "Остановить после текущей комбинации",
    "resume": "Продолжить",
    "new": "Начать новый",
    "open": "Перейти в директорию с отчётами",
    "close": "Закрыть",
    "show_all": "Показать все параметры",
    "show_changed": "Показать изменяемые параметры",
    "close_active": "Исследование ещё выполняется.\n\nОстановить после текущей комбинации и закрыть окно?",
}


REASONS_RU = {
    "CALIBRATION_ALL_ROWS_REJECTED_BY_EXPLICIT_GATES": "Все строки отклонены явными фильтрами",
    "CALIBRATION_INSUFFICIENT_SAMPLE": "Недостаточно данных",
    "ARTIFACT_INTEGRITY_FAILED": "Проверка целостности файлов завершилась ошибкой",
    "NO_REPLAYABLE_ROWS_FOR_REQUIRED_DIMENSIONS": "Недостаточно данных для replay",
}


ERRORS_RU = {
    "INSUFFICIENT_REPLAY_DATA": {
        "title": "Недостаточно данных для replay",
        "message": (
            "Не хватает timestamped historical market/cost observations "
            "для causal time-stop replay."
        ),
    },
    "BASELINE_REPLAY_INVALID": {
        "title": "Недостаточно данных для baseline replay",
        "message": "Закрытые сделки не содержат полный набор outcome-полей.",
    },
}


PARAMETER_LABELS_RU = {
    "soft_timeout_seconds": "Мягкий тайм-аут",
    "hard_timeout_seconds": "Жёсткий тайм-аут",
    "extension_seconds": "Продление тайм-аута",
    "max_extensions": "Максимум продлений",
    "min_target_progress_at_soft_timeout": "Минимальный прогресс к цели",
    "min_mfe_bps_at_soft_timeout": "Минимальный MFE",
    "min_remaining_ev_r_at_soft_timeout": "Минимальный остаточный EV",
    "break_even_activation_target_progress": "Активация безубыточности",
    "net_break_even_protection_enabled": "Защита net break-even",
}


STRATEGIES_RU = {
    "AUTO_BOUNDED": "Автоматический ограниченный поиск",
    "EXHAUSTIVE_LAZY": "Полный ленивый перебор",
}
