"""Tkinter presentation only; research work is delegated to the controller."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from .cli import DEFAULT_CONFIG, DEFAULT_OUTPUT_ROOT
from .controller import ParameterSweepController
from .texts import RU
from .utils import format_duration
from .modes import RESEARCH_MODE_VALUES, ResearchMode


class ParameterSweepWindow:
    POLL_MS = 200

    def __init__(self, root: tk.Tk, controller: ParameterSweepController) -> None:
        self.root = root
        self.controller = controller
        self.show_all = False
        root.title(RU["title"])
        root.geometry("900x760")
        root.minsize(720, 600)
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        self._render()
        root.after(self.POLL_MS, self._poll)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.body = ttk.Frame(canvas)
        self.body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.body, anchor="nw", tags="body")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure("body", width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(self.body, text=RU["title"], font=("Segoe UI", 17, "bold")).pack(anchor="w", pady=(0, 10))
        self.context = ttk.Label(self.body, justify="left")
        self.context.pack(anchor="w", fill="x")
        self.status = ttk.Label(self.body, font=("Segoe UI", 11, "bold"), wraplength=820)
        self.status.pack(anchor="w", fill="x", pady=12)
        self.plan = ttk.Label(self.body, justify="left")
        self.plan.pack(anchor="w")
        ttk.Label(
            self.body, text=RU["research_parameters"],
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(12, 4))
        self.search_parameters = tk.Text(
            self.body, height=10, wrap="word", state="disabled",
            font=("Segoe UI", 9),
        )
        self.search_parameters.pack(fill="x")
        self.progress = ttk.Progressbar(self.body, maximum=100)
        self.progress.pack(fill="x", pady=(12, 3))
        self.progress_text = ttk.Label(self.body)
        self.progress_text.pack(anchor="w")

        ttk.Label(
            self.body, text=RU["current_combination"],
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(12, 4))
        self.current_summary = ttk.Label(self.body, justify="left")
        self.current_summary.pack(anchor="w", pady=(0, 4))
        self.parameters = tk.Text(self.body, height=8, wrap="none", state="disabled", font=("Consolas", 9))
        self.parameters.pack(fill="x")
        self.toggle_button = ttk.Button(self.body, text=RU["show_all"], command=self._toggle_parameters)
        self.toggle_button.pack(anchor="w", pady=4)

        self.result = ttk.Label(self.body, justify="left")
        self.result.pack(anchor="w", pady=8)
        self.terminal_explanation = ttk.Label(self.body, justify="left", wraplength=820)
        self.terminal_explanation.pack(anchor="w", pady=4)
        self.counters = ttk.Label(self.body, justify="left")
        self.counters.pack(anchor="w", pady=4)
        self.timing = ttk.Label(self.body, justify="left")
        self.timing.pack(anchor="w", pady=4)
        self.integrity = ttk.Label(self.body, justify="left")
        self.integrity.pack(anchor="w", pady=8)
        self.replay_diagnostics = ttk.Label(self.body, justify="left", wraplength=820)
        self.replay_diagnostics.pack(anchor="w", pady=8)
        self.directory = ttk.Label(self.body, justify="left", wraplength=820)
        self.directory.pack(anchor="w", pady=4)

        actions = ttk.Frame(self.body)
        actions.pack(fill="x", pady=12)
        ttk.Label(actions, text="Символ:").pack(side="left", padx=(0, 4))
        self.symbol_var = tk.StringVar(value=self.controller.state.symbol or "")
        self.symbol_selector = ttk.Combobox(
            actions, textvariable=self.symbol_var, state="readonly", width=12,
            values=self.controller.available_symbols,
        )
        self.symbol_selector.pack(side="left", padx=(0, 8))
        self.mode_var = tk.StringVar(value=ResearchMode.ALL.value)
        self.mode_selector = ttk.Combobox(
            actions, textvariable=self.mode_var, state="readonly", width=28,
            values=RESEARCH_MODE_VALUES,
        )
        self.mode_selector.pack(side="left", padx=(0, 6))
        self.start_button = ttk.Button(actions, text=RU["start"], command=self._start)
        self.start_button.pack(side="left", padx=(0, 6))
        self.stop_button = ttk.Button(actions, text=RU["stop"], command=self.controller.request_stop_after_current)
        self.stop_button.pack(side="left", padx=6)
        self.resume_button = ttk.Button(actions, text=RU["resume"], command=self._resume)
        self.resume_button.pack(side="left", padx=6)
        self.open_button = ttk.Button(actions, text=RU["open"], command=self._open)
        self.open_button.pack(side="left", padx=6)
        ttk.Button(actions, text=RU["close"], command=self._on_close).pack(side="right")

    def _start(self) -> None:
        try:
            self.controller.start_new_run(
                mode=self.mode_var.get(), symbol=self.symbol_var.get(),
            )
        except (RuntimeError, ValueError) as error:
            messagebox.showerror(RU["title"], str(error), parent=self.root)

    def _resume(self) -> None:
        if self.controller.state.run_id != "—":
            self.controller.resume_run(
                self.controller.state.run_id, symbol=self.symbol_var.get(),
            )

    def _open(self) -> None:
        try:
            self.controller.open_reports_directory()
        except OSError as error:
            messagebox.showerror(RU["title"], str(error), parent=self.root)

    def _toggle_parameters(self) -> None:
        if self.controller.state.current_config is None:
            return
        self.show_all = not self.show_all
        self.toggle_button.configure(text=RU["show_changed"] if self.show_all else RU["show_all"])
        self._render()

    def _poll(self) -> None:
        self.controller.drain_events()
        self._render()
        if self.controller._close_after_stop and not self.controller.state.active:
            self.root.destroy()
            return
        self.root.after(self.POLL_MS, self._poll)

    def _render(self) -> None:
        state = self.controller.state
        self.context.configure(text=(
            "Profile: trade-5m-v2\nTimeframe: 5m\n"
            f"Symbol: {state.symbol or self.symbol_var.get() or '—'}\n"
            f"Глубина истории: {state.history_target_days} дней\n"
            f"Фактически загружено: {state.history_actual_days if state.history_actual_days is not None else '—'} дней\n"
            "Режим: Только чтение\n"
            f"Режим исследования: {state.research_mode}\n"
            "Источник данных: Production PAPER\nLIVE: Отключён\n"
            f"RUN ID: {state.run_id}"
        ))
        self.status.configure(text=state.status_text)
        planned_label = (
            "Будет исследовано"
            if state.terminal_state is None and state.active else "Запланировано"
        )
        self.plan.configure(text=(
            f"Фаза исследования: {state.research_phase}\n"
            f"HOLDOUT: {state.holdout_status}\n"
            f"Финалисты зафиксированы: {'ДА' if state.finalists_frozen else 'НЕТ'} · "
            f"Количество: {state.finalist_count}\n"
            f"Holdout открыт/оценён: {'ДА' if state.holdout_opened else 'НЕТ'} / "
            f"{'ДА' if state.holdout_evaluated else 'НЕТ'}\n"
            f"Количество измерений: {len(state.search_dimensions)}\n"
            f"Исходных комбинаций: {state.raw_space:,}\n"
            f"{planned_label}: {state.planned:,}\n"
            f"Фактически обработано: {state.completed:,}\n"
            f"Стратегия: {state.strategy}"
        ).replace(",", " "))
        self.search_parameters.configure(state="normal")
        self.search_parameters.delete("1.0", "end")
        self.search_parameters.insert("1.0", state.format_search_parameters())
        self.search_parameters.configure(state="disabled")
        self.progress.configure(value=state.progress_percent)
        stopped = " · Остановлено" if state.terminal_state in {"FAILED", "CANCELLED"} else ""
        self.progress_text.configure(text=(
            f"{state.progress_percent:.1f}% · Обработано {state.completed} из {state.planned}{stopped}"
        ))
        self.current_summary.configure(text=(
            RU["not_started"]
            if state.current_config is None
            else f"Комбинация {state.current_index} из {state.planned}"
        ))
        self.parameters.configure(state="normal")
        self.parameters.delete("1.0", "end")
        self.parameters.insert(
            "1.0", state.format_current_parameters(show_all=self.show_all),
        )
        self.parameters.configure(state="disabled")
        result = state.current_result
        validation = state.canonical_validation
        result_status = result.get("result_status", "—")
        translated_status = {
            "ACCEPTED": "Принята", "REJECTED": "Отклонена",
            "EARLY_REJECTED": "Недостаточно данных",
        }.get(result_status, result_status)
        if state.current_config is None:
            self.result.configure(text="Результат текущей комбинации: отсутствует")
        else:
            self.result.configure(text=(
                f"Сделок: {validation.get('validation_trade_count', '—')}\n"
                f"Покрытие символов: {validation.get('symbol_coverage', '—')} / "
                f"{validation.get('symbol_coverage_expected', 1)}\n"
                f"Независимых периодов: {validation.get('independent_period_count', '—')}\n"
                f"Статус: {translated_status}"
            ))
        if state.failed_before_first_config:
            self.terminal_explanation.configure(text=(
                f"{RU['failed_before_first']}\n"
                "Последняя обработанная комбинация: отсутствует\n"
                f"{RU['new_observations_required']}"
            ))
        elif state.terminal_state and state.completed:
            self.terminal_explanation.configure(
                text=f"Последняя обработанная комбинация: {state.completed}",
            )
        else:
            self.terminal_explanation.configure(text="")
        self.counters.configure(text=(
            f"Выполнено: {state.completed}   Осталось: {max(0, state.planned-state.completed)}\n"
            f"Принято: {state.accepted}   Отклонено: {state.rejected}   "
            f"Недостаточно данных: {state.insufficient}   Ошибки: {state.errors}\n"
            f"Этап: {state.current_stage}   Семейство: {state.current_parameter_family}\n"
            f"Negative expectancy: {state.negative_expectancy}   Promising: {state.promising}   "
            f"Validation candidates: {state.validation_candidates}\n"
            f"Артефакты: {state.artifact_bytes / 1048576:.2f} MiB / "
            f"soft {state.artifact_soft_budget_bytes / 1048576:.0f} MiB / "
            f"hard {state.artifact_hard_budget_bytes / 1048576:.0f} MiB"
        ))
        elapsed = None
        if state.started_at:
            elapsed = state.duration_seconds if state.duration_seconds is not None else (
                datetime.now(timezone.utc) - datetime.fromisoformat(state.started_at)
            ).total_seconds()
        self.timing.configure(text=(
            f"Начало: {state.started_at or '—'}\nПрошло: {format_duration(elapsed)}\n"
            f"Ориентировочно осталось: {format_duration(state.eta_seconds) if state.eta_seconds is not None else '—'}"
        ))
        self.integrity.configure(text=(
            f"Целостность отчётов: {state.integrity_status}\n" + "\n".join(state.integrity_files[-10:])
        ))
        diagnostics = state.replay_diagnostics
        if diagnostics:
            self.replay_diagnostics.configure(text=(
                f"{RU['replay_diagnostics']}\n"
                f"Закрытых PAPER-сделок: {diagnostics.get('dataset_rows', 0)}\n"
                "Повторная оценка по закрытым сделкам (OUTCOME_REPLAY): "
                f"{diagnostics.get('outcome_replay_rows', 0)}\n"
                "Повторная оценка тайм-стопа (TIME_STOP_REPLAY): "
                f"{diagnostics.get('time_stop_replay_rows', 0)}\n"
                "Исторические строки рынка: "
                f"{diagnostics.get('historical_market_rows', 0)}\n"
                "Вселенная opportunities: "
                f"{diagnostics.get('opportunity_universe_size', 0)}\n"
                "Закрытые контрольные сделки: "
                f"{diagnostics.get('persisted_closed_trades', 0)}\n"
                "Реконструированные opportunities: "
                f"{diagnostics.get('reconstructed_opportunities', 0)}\n"
                "Полный причинный replay (FULL_CAUSAL_REPLAY): "
                f"{diagnostics.get('full_replay_rows', 0)}\n"
                f"Post-instrumentation observations: {diagnostics.get('post_instrumentation_rows', 0)}\n"
                f"Без market timeline: {diagnostics.get('missing_market_timeline_rows', 0)}\n"
                f"Без cost timeline: {diagnostics.get('missing_cost_timeline_rows', 0)}\n"
                f"Причина остановки: {state.error_message_ru or '—'}"
            ))
        else:
            self.replay_diagnostics.configure(
                text=f"{RU['replay_diagnostics']}: данные ещё не рассчитаны",
            )
        self.directory.configure(text=f"Каталог результатов: {state.output_directory}")
        self.toggle_button.configure(
            text=RU["show_changed"] if self.show_all else RU["show_all"],
            state="normal" if state.current_config is not None else "disabled",
        )
        valid_symbol = self.symbol_var.get() in self.controller.available_symbols
        self.start_button.configure(
            state="disabled" if state.active or not valid_symbol else "normal",
        )
        self.stop_button.configure(state="normal" if state.active else "disabled")
        self.resume_button.configure(state="normal" if state.resume_available and not state.active else "disabled")
        self.open_button.configure(state="normal" if state.output_directory != "—" and Path(state.output_directory).is_dir() else "disabled")

    def _on_close(self) -> None:
        if self.controller.state.active:
            if not messagebox.askyesno(RU["title"], RU["close_active"], parent=self.root):
                return
            self.controller.close_ui()
            return
        self.root.destroy()


def main(
    config_path: Path = DEFAULT_CONFIG,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> None:
    root = tk.Tk()
    controller = ParameterSweepController(config_path, output_root)
    ParameterSweepWindow(root, controller)
    root.mainloop()
