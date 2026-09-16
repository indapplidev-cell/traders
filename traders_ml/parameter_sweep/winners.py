"""Streaming analytical winners for all evaluated research configurations.

The tracker is deliberately independent from validation/finalist eligibility.  It
keeps only three bounded incumbents and their aliases; durable result ledgers
remain the authority for the complete evaluated population.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Any, Iterable, Mapping


WINNER_SCHEMA_VERSION = 1
METRIC_FIELDS = (
    "trade_count", "wins", "losses", "win_rate", "gross_pnl", "fees",
    "slippage", "net_pnl", "expectancy_R", "profit_factor", "max_drawdown",
    "avg_win", "avg_loss", "avg_holding_time", "independent_periods",
    "symbol_coverage",
)


def _high(value: object) -> float:
    return -inf if value is None else float(value)


def _low(value: object) -> float:
    return inf if value is None else float(value)


def _config_id(row: Mapping[str, Any]) -> str:
    return str(row.get("config_id") or row.get("numeric_config_id") or "")


def positive_net_pnl_rank(row: Mapping[str, Any]) -> tuple[object, ...]:
    return (
        _high(row.get("net_pnl")), _high(row.get("expectancy_R")),
        _high(row.get("profit_factor")), -_low(row.get("max_drawdown")),
        int(row.get("trade_count") or 0), _config_id(row),
    )


def net_pnl_fallback_rank(row: Mapping[str, Any]) -> tuple[object, ...]:
    return positive_net_pnl_rank(row)


def win_count_rank(row: Mapping[str, Any]) -> tuple[object, ...]:
    return (
        int(row.get("wins") or row.get("win_count") or 0),
        _high(row.get("net_pnl")), _high(row.get("expectancy_R")),
        -int(row.get("losses") or row.get("loss_count") or 0),
        -_low(row.get("max_drawdown")), int(row.get("trade_count") or 0),
        _config_id(row),
    )


def _projection(row: Mapping[str, Any]) -> dict[str, Any]:
    numeric_id = _config_id(row)
    behavior = str(
        row.get("behavioral_cluster_id") or row.get("behavioral_signature")
        or row.get("validation_behavioral_signature") or numeric_id
    )
    parameters = dict(
        row.get("parameters") or row.get("candidate_parameters")
        or row.get("overrides") or {}
    )
    wins = int(row.get("wins") or row.get("win_count") or 0)
    losses = int(row.get("losses") or row.get("loss_count") or 0)
    projected = {
        "symbol": row.get("symbol"),
        "config_id": numeric_id,
        "numeric_config_id": numeric_id,
        "config_index": row.get("config_index", row.get("result_index")),
        "behavioral_cluster_id": behavior,
        "numeric_alias_count": 1,
        "parameters": parameters,
        "trade_count": int(row.get("trade_count") or 0),
        "wins": wins,
        "losses": losses,
        "win_rate": row.get("win_rate"),
        "gross_pnl": row.get("gross_pnl"),
        "fees": row.get("fees"),
        "slippage": row.get("slippage"),
        "net_pnl": row.get("net_pnl"),
        "expectancy_R": row.get("expectancy_R"),
        "profit_factor": row.get("profit_factor"),
        "max_drawdown": row.get("max_drawdown"),
        "avg_win": row.get("avg_win"),
        "avg_loss": row.get("avg_loss"),
        "avg_holding_time": row.get("avg_holding_time"),
        "independent_periods": row.get(
            "independent_periods", row.get("independent_period_count")
        ),
        "symbol_coverage": row.get("symbol_coverage"),
        "validation_status": row.get(
            "validation_status", row.get("performance_class", "NOT_EVALUATED")
        ),
        "promotion_eligible": bool(row.get("promotion_eligible", False)),
    }
    return projected


def _merge_aliases(
    incumbent: Mapping[str, Any], candidate: Mapping[str, Any],
    rank,
) -> dict[str, Any]:
    selected = dict(candidate if rank(candidate) > rank(incumbent) else incumbent)
    selected["numeric_alias_count"] = int(incumbent.get("numeric_alias_count") or 1) + 1
    return selected


def _consider(
    incumbent: Mapping[str, Any] | None, candidate: Mapping[str, Any], rank,
) -> dict[str, Any]:
    projected = _projection(candidate)
    if incumbent is None:
        return projected
    if incumbent.get("behavioral_cluster_id") == projected["behavioral_cluster_id"]:
        return _merge_aliases(incumbent, projected, rank)
    return projected if rank(projected) > rank(incumbent) else dict(incumbent)


@dataclass(slots=True)
class WinnerTracker:
    """O(1) incumbent state; no evaluated-result collection is retained."""

    evaluated: int = 0
    best_positive_net_pnl: dict[str, Any] | None = None
    best_net_pnl_fallback: dict[str, Any] | None = None
    best_win_count: dict[str, Any] | None = None

    @classmethod
    def restore(cls, value: Mapping[str, Any] | None) -> "WinnerTracker":
        if not value:
            return cls()
        return cls(
            evaluated=int(value.get("search_evaluated") or value.get("evaluated") or 0),
            best_positive_net_pnl=(
                dict(value["best_positive_net_pnl"])
                if value.get("best_positive_net_pnl") else None
            ),
            best_net_pnl_fallback=(
                dict(value["best_net_pnl_fallback"])
                if value.get("best_net_pnl_fallback") else None
            ),
            best_win_count=(
                dict(value["best_win_count"])
                if value.get("best_win_count") else None
            ),
        )

    @classmethod
    def from_rows(cls, rows: Iterable[Mapping[str, Any]]) -> "WinnerTracker":
        tracker = cls()
        for row in rows:
            tracker.update(row)
        return tracker

    def update(self, row: Mapping[str, Any]) -> bool:
        """Consider one completed configuration and report presentation change."""
        before = self.state()
        self.evaluated += 1
        self.best_net_pnl_fallback = _consider(
            self.best_net_pnl_fallback, row, net_pnl_fallback_rank,
        )
        self.best_win_count = _consider(self.best_win_count, row, win_count_rank)
        if float(row.get("net_pnl") or 0) > 0:
            self.best_positive_net_pnl = _consider(
                self.best_positive_net_pnl, row, positive_net_pnl_rank,
            )
        return before != self.state()

    def state(self) -> dict[str, Any]:
        return {
            "schema_version": WINNER_SCHEMA_VERSION,
            "search_evaluated": self.evaluated,
            "positive_net_pnl_found": self.best_positive_net_pnl is not None,
            "best_positive_net_pnl": self.best_positive_net_pnl,
            "best_net_pnl_fallback": self.best_net_pnl_fallback,
            "best_win_count": self.best_win_count,
        }

    def artifact(
        self, *, symbol: str, profile: str, search_budget: int,
        search_status: str,
    ) -> dict[str, Any]:
        return {
            "artifact": "BEST_CONFIGS",
            **self.state(),
            "symbol": symbol,
            "profile": profile,
            "search_budget": int(search_budget),
            "search_status": search_status,
            "selection_population": "ALL_EVALUATED_RESEARCH_CONFIGS",
            "validation_eligibility_filter": False,
            "deterministic_tie_break": "CONFIG_ID_DESC",
            "behavioral_alias_dedupe": True,
            "streaming_memory": "O(1)_BOUNDED_INCUMBENTS",
        }


def search_incumbents(
    winners: Mapping[str, Any], balanced: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return distinct analytical parents without changing economic ranking."""
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for role, value in (
        ("BEST_POSITIVE_NET_PNL_CONFIG", winners.get("best_positive_net_pnl")),
        ("BEST_WIN_COUNT_CONFIG", winners.get("best_win_count")),
        ("BEST_BALANCED_CONFIG", balanced),
    ):
        if not value:
            continue
        candidate = dict(value)
        behavior = str(
            candidate.get("behavioral_cluster_id")
            or candidate.get("behavioral_signature") or candidate.get("config_id")
        )
        if behavior in seen:
            continue
        seen.add(behavior)
        output.append({"incumbent_role": role, **candidate})
    return output
