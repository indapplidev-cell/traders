"""Проверки риска перед исполнением paper-сделки."""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import get_settings
from app.execution.position_manager import PaperPortfolioState
from app.strategy.base_strategy import StrategyDecision
from app.strategy.trade_decision import DecisionType, TradeDecision


@dataclass(slots=True)
class RiskCheckResult:
    """Результат проверки риск-правил."""

    approved: bool
    final_action: str
    reason: str


class RiskManager:
    """Проверяет ограничения paper trading перед исполнением решения."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def validate_decision(self, decision: TradeDecision, portfolio_state: PaperPortfolioState) -> RiskCheckResult:
        """Старый контракт для Stage 1/2 поверх новых правил risk gate."""

        return self._validate_action(
            action=decision.decision.value,
            symbol=decision.symbol,
            confidence=1.0,
            portfolio_state=portfolio_state,
        )

    def validate_strategy_decision(
        self,
        decision: StrategyDecision,
        portfolio_state: PaperPortfolioState,
    ) -> RiskCheckResult:
        """Новый контракт runtime-слоя с учётом confidence."""

        return self._validate_action(
            action=decision.action,
            symbol=decision.symbol,
            confidence=decision.confidence,
            portfolio_state=portfolio_state,
        )

    def _validate_action(
        self,
        *,
        action: str,
        symbol: str,
        confidence: float,
        portfolio_state: PaperPortfolioState,
    ) -> RiskCheckResult:
        open_positions = portfolio_state.open_positions
        has_symbol_position = any(position.symbol == symbol for position in open_positions)

        if action == "HOLD":
            return RiskCheckResult(approved=True, final_action="HOLD", reason="HOLD всегда безопасен.")

        if confidence < self.settings.strategy_min_confidence:
            return RiskCheckResult(
                approved=False,
                final_action="HOLD",
                reason=(
                    "low_confidence: confidence ниже STRATEGY_MIN_CONFIDENCE "
                    f"({confidence:.2f} < {self.settings.strategy_min_confidence:.2f})."
                ),
            )

        if action == DecisionType.BUY.value:
            if len(open_positions) >= self.settings.paper_max_open_positions:
                return RiskCheckResult(
                    approved=False,
                    final_action="HOLD",
                    reason="Достигнут лимит открытых paper-позиций.",
                )
            if has_symbol_position:
                return RiskCheckResult(
                    approved=False,
                    final_action="HOLD",
                    reason="По символу уже есть открытая paper-позиция.",
                )

            required_notional = portfolio_state.balance_usdt * self.settings.paper_position_size_fraction
            if portfolio_state.balance_usdt <= 0:
                return RiskCheckResult(
                    approved=False,
                    final_action="HOLD",
                    reason="Недостаточно paper-баланса: баланс пустой.",
                )
            if required_notional > portfolio_state.balance_usdt:
                return RiskCheckResult(
                    approved=False,
                    final_action="HOLD",
                    reason="Недостаточно paper-баланса для расчётной доли позиции.",
                )
            return RiskCheckResult(
                approved=True,
                final_action="BUY",
                reason="BUY прошёл базовую риск-проверку.",
            )

        if action == DecisionType.SELL.value:
            if not has_symbol_position:
                return RiskCheckResult(
                    approved=False,
                    final_action="HOLD",
                    reason="Нельзя выполнить SELL: открытая позиция отсутствует.",
                )
            return RiskCheckResult(
                approved=True,
                final_action="SELL",
                reason="SELL прошёл базовую риск-проверку.",
            )

        return RiskCheckResult(
            approved=False,
            final_action="HOLD",
            reason="Неизвестный тип решения.",
        )
