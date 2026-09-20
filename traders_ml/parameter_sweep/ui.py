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
from .modes import ResearchMode
from app.i18n.catalog import RU as SERVER_RU


def _display(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.8f}".rstrip("0").rstrip(".")
    return str(value)


def _winner_details(value: dict | None) -> str:
    if not value:
        return "—"
    parameters = "\n".join(
        f"  {name} = {_display(parameter_value)}"
        for name, parameter_value in sorted(dict(value.get("parameters") or {}).items())
    ) or "  —"
    return (
        f"Config ID: {_display(value.get('config_id'))}\n"
        f"Behavioral cluster: {_display(value.get('behavioral_cluster_id'))} · "
        f"numeric aliases: {int(value.get('numeric_alias_count') or 1)}\n"
        f"Параметры:\n{parameters}\n"
        f"Сделок: {_display(value.get('trade_count'))} · Побед: {_display(value.get('wins'))} · "
        f"Поражений: {_display(value.get('losses'))} · Win rate: {_display(value.get('win_rate'))}\n"
        f"Gross PnL: {_display(value.get('gross_pnl'))} · Fees: {_display(value.get('fees'))} · "
        f"Slippage: {_display(value.get('slippage'))} · Net PnL: {_display(value.get('net_pnl'))}\n"
        f"Expectancy R: {_display(value.get('expectancy_R'))} · Profit Factor: {_display(value.get('profit_factor'))} · "
        f"Max Drawdown: {_display(value.get('max_drawdown'))}\n"
        f"Avg win/loss/holding: {_display(value.get('avg_win'))} / {_display(value.get('avg_loss'))} / "
        f"{_display(value.get('avg_holding_time'))}\n"
        f"Independent periods: {_display(value.get('independent_periods'))} · "
        f"Symbol coverage: {_display(value.get('symbol_coverage'))}\n"
        f"Validation: {_display(value.get('validation_status'))} · Promotion eligible: "
        f"{'ДА' if value.get('promotion_eligible') else 'НЕТ'}"
    )

def _winner_effective_details(value: dict | None) -> str:
    if not value:
        return "Полный snapshot отсутствует"
    lines = ["Search parameters + effective values + sources"]
    for name, item in sorted((value.get("parameter_sources") or {}).items()):
        marker = "SEARCH_OVERRIDE" if item.get("search_overridden") else "INHERITED/BASE"
        source = item.get("source_yaml_path") or item.get("source_policy") or "—"
        lines.append(f"{name} = {_display(item.get('effective_value'))} · {marker} · {source}")
    effective = value.get("effective_configuration") or {}
    lines.append(f"\nConfig snapshot hash: {_display(value.get('resolved_config_hash'))}")
    lines.append(f"Replay parameters: {len(effective.get('replay_parameters') or {})}")
    lines.append(f"Resolved parameters: {len(effective.get('resolved_parameters') or {})}")
    return "\n".join(lines)


def format_positive_winner_card(state) -> str:
    if state.positive_net_pnl_found and state.best_positive_net_pnl_config:
        return "Статус: найдено\n" + _winner_details(state.best_positive_net_pnl_config)
    fallback = state.best_net_pnl_config
    return (
        SERVER_RU["parameter_sweep.winners.positive_not_found"] + "\n\n"
        + SERVER_RU["parameter_sweep.winners.best_net_pnl"] + ":\n"
        + _winner_details(fallback)
    )


def format_win_count_card(state) -> str:
    winner = state.best_win_count_config
    text = _winner_details(winner)
    if winner and float(winner.get("net_pnl") or 0) <= 0:
        text += "\n" + SERVER_RU["parameter_sweep.winners.negative_economic_result"]
    return text


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
        ttk.Label(
            self.body, text=SERVER_RU["parameter_sweep.winners.title"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(12, 5))
        profit_frame = ttk.LabelFrame(
            self.body, text=SERVER_RU["parameter_sweep.winners.max_positive_profit"],
            padding=8,
        )
        profit_frame.pack(fill="x", pady=4)
        self.best_profit = ttk.Label(profit_frame, justify="left", wraplength=800)
        self.best_profit.pack(anchor="w", fill="x")
        self.best_profit_details = ttk.Button(profit_frame, text="Показать полный набор параметров", command=lambda: self._show_winner_config("profit"))
        self.best_profit_details.pack(anchor="w", pady=(6, 0))
        wins_frame = ttk.LabelFrame(
            self.body, text=SERVER_RU["parameter_sweep.winners.max_win_count"],
            padding=8,
        )
        wins_frame.pack(fill="x", pady=4)
        self.best_wins = ttk.Label(wins_frame, justify="left", wraplength=800)
        self.best_wins.pack(anchor="w", fill="x")
        self.best_wins_details = ttk.Button(wins_frame, text="Показать полный набор параметров", command=lambda: self._show_winner_config("wins"))
        self.best_wins_details.pack(anchor="w", pady=(6, 0))
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
        ttk.Label(actions, text=SERVER_RU["parameter_sweep.selector.symbol"]).pack(side="left", padx=(0, 4))
        self.symbol_var = tk.StringVar(value=self.controller.state.symbol or "")
        self.symbol_selector = ttk.Combobox(
            actions, textvariable=self.symbol_var, state="readonly", width=12,
            values=self.controller.selector_values,
        )
        self.symbol_selector.pack(side="left", padx=(0, 8))
        self.mode_var = tk.StringVar(value=ResearchMode.ALL.value)
        self.mode_selector = ttk.Combobox(
            actions, textvariable=self.mode_var, state="readonly", width=28,
            values=(ResearchMode.ALL.value,),
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
            from app.i18n.catalog import RU as SERVER_RU
            selected = self.symbol_var.get()
            if selected == SERVER_RU["parameter_sweep.selector.all"]:
                selected = "ALL"
            self.controller.start_new_run(
                mode=self.mode_var.get(), symbol=selected,
            )
        except (RuntimeError, ValueError) as error:
            messagebox.showerror(RU["title"], str(error), parent=self.root)

    def _resume(self) -> None:
        if self.controller.state.run_id != "—":
            selected = self.symbol_var.get()
            if selected == SERVER_RU["parameter_sweep.selector.all"]:
                selected = "ALL"
            self.controller.resume_run(
                self.controller.state.run_id, symbol=selected,
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

    def _show_winner_config(self, role: str) -> None:
        state = self.controller.state
        value = state.best_positive_net_pnl_config if role == "profit" else state.best_win_count_config
        dialog = tk.Toplevel(self.root)
        dialog.title("Полный набор параметров winner")
        dialog.geometry("900x700")
        text = tk.Text(dialog, wrap="none", font=("Consolas", 9))
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", _winner_effective_details(value))
        text.configure(state="disabled")

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
        if state.symbol == "ALL":
            plan_text = (
                f"Режим поиска: {SERVER_RU['parameter_sweep.progress.all_mode']}\n"
                f"Символов обработано: {state.completed_symbols} / {len(state.resolved_symbols)}\n"
                f"Текущий символ: {state.current_symbol or '—'}\n"
                f"Текущая фаза: {state.pipeline_phase}\n"
                f"Комбинаций обработано: {state.search_evaluated}\n"
                f"Статус: {state.all_status}"
            )
        elif state.research_mode == ResearchMode.ALL.value:
            phase_lines = []
            labels = {
                "SEPARABILITY": "Separability",
                "DATA_DRIVEN_RANGE_GENERATION": "Data-Driven Ranges",
                "EXPANDED_AUTOMATIC_SEARCH": "Expanded Search",
                "ADAPTIVE_REFINEMENT": "Adaptive Refinement",
                "VALIDATION_RANKING": "Validation Ranking",
                "IMMUTABLE_FINALIST_FREEZE": "Finalist Freeze",
            }
            for phase, label in labels.items():
                summary = state.pipeline_phase_summaries.get(phase, {})
                detail = ", ".join(f"{key}={value}" for key, value in summary.items())
                phase_lines.append(
                    f"{label}: {state.pipeline_phase_statuses.get(phase, 'NOT_STARTED')}"
                    + (f" · {detail}" if detail else "")
                )
            plan_text = (
                f"Оркестратор: {state.gui_orchestrator}\n"
                f"Выбранный символ: {state.symbol or '—'}\n"
                f"Источник диапазонов: {state.search_source or 'NOT_AVAILABLE'}\n"
                f"Текущая фаза: {state.pipeline_phase}\n"
                f"Общий статус: {state.overall_status}\n"
                + "\n".join(phase_lines)
            )
        else:
            plan_text = (
            f"Фаза исследования: {state.research_phase}\n"
            f"HOLDOUT: {state.holdout_status}\n"
            f"Финалисты зафиксированы: {'ДА' if state.finalists_frozen else 'НЕТ'} · "
            f"Количество: {state.finalist_count}\n"
            f"Holdout открыт/оценён: {'ДА' if state.holdout_opened else 'НЕТ'} / "
            f"{'ДА' if state.holdout_evaluated else 'НЕТ'}\n"
            f"Validation Ranking: eligible numeric {state.validation_ranking_eligible_numeric}; "
            f"eligible behavioral {state.validation_ranking_eligible_behavioral}; "
            f"descriptive behavioral {state.validation_ranking_descriptive_behavioral}\n"
            f"Top eligible: {state.validation_ranking_top_eligible or 'NONE'}; "
            f"top descriptive: {state.validation_ranking_top_descriptive or 'NONE'}\n"
            f"Количество измерений: {len(state.search_dimensions)}\n"
            f"Исходных комбинаций: {state.raw_space:,}\n"
            f"{planned_label}: {state.planned:,}\n"
            f"Фактически обработано: {state.completed:,}\n"
            f"Стратегия: {state.strategy}"
            )
        self.plan.configure(text=plan_text.replace(",", " "))
        self.search_parameters.configure(state="normal")
        self.search_parameters.delete("1.0", "end")
        self.search_parameters.insert("1.0", state.format_search_parameters())
        self.search_parameters.configure(state="disabled")
        if state.symbol == "ALL":
            total = len(state.resolved_symbols)
            self.progress.configure(value=100.0 * state.completed_symbols / total if total else 0.0)
            self.progress_text.configure(text=(
                f"Символов обработано {state.completed_symbols} из {total} · {state.all_status}"
            ))
        elif state.research_mode == ResearchMode.ALL.value:
            phase_values = tuple(state.pipeline_phase_statuses.values())
            finished_phases = sum(value in {"COMPLETED", "LIMITED", "STOPPED", "FAILED"} for value in phase_values)
            pipeline_progress = 100.0 * finished_phases / 6
            if state.overall_status == "COMPLETED":
                pipeline_progress = 100.0
            self.progress.configure(value=pipeline_progress)
            self.progress_text.configure(text=(
                f"{pipeline_progress:.1f}% · Фаза {state.pipeline_phase} · {state.overall_status}"
            ))
        else:
            self.progress.configure(value=state.progress_percent)
            stopped = " · Остановлено" if state.terminal_state in {"FAILED", "CANCELLED"} else ""
            self.progress_text.configure(text=(
                f"{state.progress_percent:.1f}% · Обработано {state.completed} из {state.planned}{stopped}"
            ))
        if state.current_config is None:
            current_summary = f"Текущая комбинация: не применимо для фазы {state.pipeline_phase}"
        elif state.pipeline_phase == "ADAPTIVE_REFINEMENT":
            current_summary = (
                f"Раунд {state.adaptive_round}"
                + (f" из {state.adaptive_max_rounds}" if state.adaptive_max_rounds else "")
                + f" · Комбинация {state.current_index} из {state.adaptive_planned}"
                + (f" · {state.current_config_status}" if state.current_config_status else "")
            )
        else:
            current_summary = (
                f"Комбинация {state.current_index} из {state.planned}"
                + (f" · {state.current_config_status}" if state.current_config_status else "")
            )
        self.current_summary.configure(text=current_summary)
        self.parameters.configure(state="normal")
        self.parameters.delete("1.0", "end")
        self.parameters.insert(
            "1.0", state.format_current_parameters(show_all=self.show_all),
        )
        self.parameters.configure(state="disabled")
        result = state.current_result
        validation = state.canonical_validation
        result_status = result.get("result_status", result.get("evaluation_status", state.current_config_status or "—"))
        translated_status = {
            "ACCEPTED": "Принята", "REJECTED": "Отклонена",
            "EARLY_REJECTED": "Недостаточно данных",
        }.get(result_status, result_status)
        if state.current_config is None:
            self.result.configure(text="Результат текущей комбинации: отсутствует")
        else:
            self.result.configure(text=(
                f"Сделок: {validation.get('validation_trade_count', '—')}\n"
                f"Минимум сделок validation: {state.validation_minimum_trades or '—'}\n"
                f"Покрытие символов: {validation.get('symbol_coverage', '—')} / "
                f"{validation.get('symbol_coverage_expected', 1)}\n"
                f"Независимых периодов: {validation.get('independent_period_count', '—')} / "
                f"{state.minimum_independent_periods or '—'} "
                f"({state.independent_period_unit or '—'})\n"
                f"Статус: {translated_status}"
            ))
        self.best_profit.configure(text=format_positive_winner_card(state))
        self.best_wins.configure(text=format_win_count_card(state))
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
            f"Expanded evaluated: {state.expanded_evaluated}   Adaptive evaluated: {state.adaptive_evaluated}   "
            f"Total research evaluated: {state.total_research_evaluated}\n"
            f"Behavioral clusters: {state.behavioral_cluster_count}   Дубликаты: {state.behavioral_duplicate_count}\n"
            f"Adaptive round: {state.adaptive_round}   New clusters: {state.adaptive_new_clusters}   "
            f"Stop: {state.adaptive_stop_reason or 'NOT_AVAILABLE'}\n"
            f"Validation numeric/behavioral: {state.validation_total_numeric}/{state.validation_total_behavioral}   "
            f"eligible: {state.validation_eligible_numeric}/{state.validation_eligible_behavioral}\n"
            f"Freeze requested/selected: {state.freeze_requested_finalists}/{state.freeze_selected_finalists}   "
            f"Integrity: {state.integrity_status}   Reason: {state.freeze_reason or 'NOT_AVAILABLE'}\n"
            f"Production closed trades: {state.production_closed_trades}   Opportunity rows: {state.opportunity_evidence_rows}\n"
            f"Counterfactual configs/trades/wins/losses: {state.counterfactual_configs_evaluated}/"
            f"{state.counterfactual_trade_count}/{state.counterfactual_wins}/{state.counterfactual_losses}\n"
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
                text=f"{RU['replay_diagnostics']}: {state.replay_diagnostics_status}",
            )
        self.directory.configure(text=f"Каталог результатов: {state.output_directory}")
        self.toggle_button.configure(
            text=RU["show_changed"] if self.show_all else RU["show_all"],
            state="normal" if state.current_config is not None else "disabled",
        )
        valid_symbol = self.symbol_var.get() in self.controller.selector_values
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
