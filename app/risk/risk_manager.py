"""Проверки риска перед исполнением paper-сделки."""

from dataclasses import dataclass

from app.config.settings import get_settings
from app.execution.position_manager import PaperPortfolioState
from app.strategy.trade_decision import DecisionType, TradeDecision


@dataclass(slots=True)
class RiskCheckResult:
    """Результат проверки риск-правил."""

    approved: bool
    reason: str


class RiskManager:
    """Проверяет ограничения paper trading перед исполнением решения."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def validate_decision(self, decision: TradeDecision, portfolio_state: PaperPortfolioState) -> RiskCheckResult:
        """Разрешает или отклоняет решение стратегии.

        Этот слой нужен затем, чтобы стратегия не могла напрямую открыть
        позицию в обход базовых ограничений по балансу и количеству позиций.
        """

        open_positions = portfolio_state.open_positions
        has_symbol_position = any(position.symbol == decision.symbol for position in open_positions)

        if decision.decision == DecisionType.HOLD:
            return RiskCheckResult(approved=True, reason="HOLD не требует риск-блокировки.")

        if decision.decision == DecisionType.BUY:
            if len(open_positions) >= self.settings.paper_max_open_positions:
                return RiskCheckResult(approved=False, reason="Достигнут лимит открытых paper-позиций.")
            if has_symbol_position:
                return RiskCheckResult(approved=False, reason="По символу уже есть открытая paper-позиция.")

            required_notional = portfolio_state.balance_usdt * self.settings.paper_position_size_fraction
            if portfolio_state.balance_usdt <= 0:
                return RiskCheckResult(approved=False, reason="Недостаточно paper-баланса: баланс пустой.")
            if required_notional > portfolio_state.balance_usdt:
                return RiskCheckResult(
                    approved=False,
                    reason="Недостаточно paper-баланса для расчётной доли позиции.",
                )
            return RiskCheckResult(approved=True, reason="BUY прошёл базовую риск-проверку.")

        if decision.decision == DecisionType.SELL:
            if not has_symbol_position:
                return RiskCheckResult(approved=False, reason="Нельзя выполнить SELL: открытая позиция отсутствует.")
            return RiskCheckResult(approved=True, reason="SELL прошёл базовую риск-проверку.")

        return RiskCheckResult(approved=False, reason="Неизвестный тип решения.")
