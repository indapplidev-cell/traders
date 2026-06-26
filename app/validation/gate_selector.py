from __future__ import annotations

from collections import Counter
from typing import Any


class GateSelector:
    diagnostic_name = "walk_forward_validation_gate_selection_diagnostics"
    diagnostic_version = "ml38.10.24"

    DEFAULT_MIN_SIGNAL_COUNT = 30
    DEFAULT_MIN_PROFIT_FACTOR = 1.0
    DEFAULT_MIN_TOTAL_R = 0.0
    DEFAULT_MIN_EXPECTANCY_R = 0.0

    def select(
        self,
        gate_results: list[dict[str, Any]],
        *,
        directional_side_filter_profile: str | None = None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None = None,
        side_aware_validation_relaxation_enabled: bool = False,
        side_aware_min_validation_signal_count: int | None = None,
        side_aware_min_validation_profit_factor: float | None = None,
        side_aware_min_validation_total_r: float | None = None,
        side_aware_min_validation_expectancy_r: float | None = None,
        side_aware_allow_single_direction_validation: bool = False,
    ) -> dict[str, Any]:
        context = self._selection_context(
            directional_side_filter_profile=directional_side_filter_profile,
            allowed_signal_directions=allowed_signal_directions,
            side_aware_validation_relaxation_enabled=side_aware_validation_relaxation_enabled,
            side_aware_min_validation_signal_count=side_aware_min_validation_signal_count,
            side_aware_min_validation_profit_factor=side_aware_min_validation_profit_factor,
            side_aware_min_validation_total_r=side_aware_min_validation_total_r,
            side_aware_min_validation_expectancy_r=side_aware_min_validation_expectancy_r,
            side_aware_allow_single_direction_validation=side_aware_allow_single_direction_validation,
        )
        passed: list[dict[str, Any]] = []
        probes: list[dict[str, Any]] = []
        for row in gate_results:
            probe = self._probe_gate(row=row, context=context)
            probes.append(probe)
            if probe["passed"]:
                item = {
                    "gate_type": row["gate_type"],
                    "threshold": row["threshold"],
                    "validation_signal_count": row["signal_count"],
                    "validation_profit_factor": row["profit_factor"],
                    "validation_total_r": row["total_r"],
                    "validation_expectancy_r": row["expectancy_r"],
                    "validation_long_count": row["long_count"],
                    "validation_short_count": row["short_count"],
                    "validation_max_drawdown_r": row["max_drawdown_r"],
                    "warnings": list(probe["warnings"]),
                    "validation_gate_selection_mode": context["selection_mode"],
                    "side_aware_validation_relaxation_used": bool(context["relaxation_active"]),
                }
                passed.append(item)

        diagnostics = self._diagnostics(context=context, probes=probes, passed=passed)
        if not passed:
            return {
                "selected_gate": None,
                "reject_reason": "no_validation_gate_passed",
                "diagnostics": diagnostics,
            }

        best = max(
            passed,
            key=lambda item: (
                float(item["validation_profit_factor"]),
                float(item["validation_total_r"]),
                float(item["validation_expectancy_r"]),
                int(item["validation_signal_count"]),
            ),
        )
        return {
            "selected_gate": best,
            "reject_reason": None,
            "diagnostics": diagnostics,
        }

    def _selection_context(
        self,
        *,
        directional_side_filter_profile: str | None,
        allowed_signal_directions: tuple[str, ...] | list[str] | None,
        side_aware_validation_relaxation_enabled: bool,
        side_aware_min_validation_signal_count: int | None,
        side_aware_min_validation_profit_factor: float | None,
        side_aware_min_validation_total_r: float | None,
        side_aware_min_validation_expectancy_r: float | None,
        side_aware_allow_single_direction_validation: bool,
    ) -> dict[str, Any]:
        normalized_directions = self._normalize_allowed_signal_directions(
            allowed_signal_directions=allowed_signal_directions,
            directional_side_filter_profile=directional_side_filter_profile,
        )
        profile = str(directional_side_filter_profile or "both_directions")
        side_profile_active = set(normalized_directions) != {"LONG", "SHORT"}
        relaxation_active = bool(side_aware_validation_relaxation_enabled and side_profile_active)
        return {
            "selection_mode": "side_aware_research_relaxed" if relaxation_active else "classic",
            "directional_side_filter_profile": profile,
            "allowed_signal_directions": normalized_directions,
            "side_profile_active": side_profile_active,
            "relaxation_active": relaxation_active,
            "allow_single_direction_validation": bool(
                side_aware_allow_single_direction_validation and side_profile_active
            ),
            "min_signal_count": int(
                side_aware_min_validation_signal_count
                if relaxation_active and side_aware_min_validation_signal_count is not None
                else self.DEFAULT_MIN_SIGNAL_COUNT
            ),
            "min_profit_factor": float(
                side_aware_min_validation_profit_factor
                if relaxation_active and side_aware_min_validation_profit_factor is not None
                else self.DEFAULT_MIN_PROFIT_FACTOR
            ),
            "min_total_r": float(
                side_aware_min_validation_total_r
                if relaxation_active and side_aware_min_validation_total_r is not None
                else self.DEFAULT_MIN_TOTAL_R
            ),
            "min_expectancy_r": float(
                side_aware_min_validation_expectancy_r
                if relaxation_active and side_aware_min_validation_expectancy_r is not None
                else self.DEFAULT_MIN_EXPECTANCY_R
            ),
        }

    def _probe_gate(self, *, row: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        reasons: list[str] = []
        warnings: list[str] = []
        signal_count = int(row.get("signal_count", 0) or 0)
        long_count = int(row.get("long_count", 0) or 0)
        short_count = int(row.get("short_count", 0) or 0)
        profit_factor = self._float_or_none(row.get("profit_factor"))
        total_r = self._float_or_none(row.get("total_r"))
        expectancy_r = self._float_or_none(row.get("expectancy_r"))
        max_drawdown_r = float(row.get("max_drawdown_r", 0.0) or 0.0)

        if signal_count < int(context["min_signal_count"]):
            reasons.append("signal_count_below_min")
        if profit_factor is None or profit_factor <= float(context["min_profit_factor"]):
            reasons.append("profit_factor_below_min")
        if total_r is None or total_r <= float(context["min_total_r"]):
            reasons.append("total_r_below_min")
        if expectancy_r is None or expectancy_r <= float(context["min_expectancy_r"]):
            reasons.append("expectancy_below_min")

        allowed = set(context["allowed_signal_directions"])
        if context["allow_single_direction_validation"]:
            if "LONG" in allowed and long_count <= 0:
                reasons.append("required_long_signal_missing")
            if "SHORT" in allowed and short_count <= 0:
                reasons.append("required_short_signal_missing")
            if "LONG" not in allowed and long_count > 0:
                warnings.append("validation_has_long_signals_outside_allowed_side")
            if "SHORT" not in allowed and short_count > 0:
                warnings.append("validation_has_short_signals_outside_allowed_side")
        else:
            # Preserve legacy behavior. Historically this selector required at least one LONG.
            if long_count <= 0:
                reasons.append("required_long_signal_missing")
            if short_count <= 0:
                warnings.append("no_short_signals")

        if long_count == 0:
            warnings.append("no_long_signals")
        if short_count == 0:
            warnings.append("no_short_signals")

        if total_r is not None and total_r > 0 and max_drawdown_r > abs(total_r) * 2:
            reasons.append("max_drawdown_too_high")

        return {
            "gate_type": row.get("gate_type"),
            "threshold": row.get("threshold"),
            "signal_count": signal_count,
            "long_count": long_count,
            "short_count": short_count,
            "profit_factor": profit_factor,
            "total_r": total_r,
            "expectancy_r": expectancy_r,
            "max_drawdown_r": max_drawdown_r,
            "passed": not reasons,
            "fail_reasons": reasons,
            "warnings": sorted(set(warnings)),
            "selection_mode": context["selection_mode"],
        }

    def _diagnostics(
        self,
        *,
        context: dict[str, Any],
        probes: list[dict[str, Any]],
        passed: list[dict[str, Any]],
    ) -> dict[str, Any]:
        reason_counts: Counter[str] = Counter(
            reason for probe in probes for reason in probe.get("fail_reasons", [])
        )
        failed = [probe for probe in probes if not probe.get("passed")]
        return {
            "diagnostic_name": self.diagnostic_name,
            "diagnostic_version": self.diagnostic_version,
            "diagnostic_status": "PASSED_GATE_FOUND" if passed else "NO_GATE_PASSED",
            "selection_mode": context["selection_mode"],
            "directional_side_filter_profile": context["directional_side_filter_profile"],
            "allowed_signal_directions": list(context["allowed_signal_directions"]),
            "side_aware_validation_relaxation_enabled": bool(context["relaxation_active"]),
            "side_aware_allow_single_direction_validation": bool(
                context["allow_single_direction_validation"]
            ),
            "effective_min_signal_count": int(context["min_signal_count"]),
            "effective_min_profit_factor": float(context["min_profit_factor"]),
            "effective_min_total_r": float(context["min_total_r"]),
            "effective_min_expectancy_r": float(context["min_expectancy_r"]),
            "gate_probe_count": len(probes),
            "passed_gate_count": len(passed),
            "failed_gate_count": len(failed),
            "failure_reason_counts": dict(reason_counts),
            "best_failed_gate_by_signal_count": self._best_probe(failed, "signal_count"),
            "best_failed_gate_by_total_r": self._best_probe(failed, "total_r"),
            "best_failed_gate_by_profit_factor": self._best_probe(failed, "profit_factor"),
            "passed_gates": passed,
            "gate_probes": probes,
        }

    @staticmethod
    def _best_probe(probes: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
        if not probes:
            return None
        return max(
            (dict(probe) for probe in probes),
            key=lambda row: (
                float(row.get(key, 0.0) or 0.0),
                float(row.get("total_r", 0.0) or 0.0),
                int(row.get("signal_count", 0) or 0),
            ),
        )

    @staticmethod
    def _normalize_allowed_signal_directions(
        *,
        allowed_signal_directions: tuple[str, ...] | list[str] | None,
        directional_side_filter_profile: str | None,
    ) -> tuple[str, ...]:
        if allowed_signal_directions:
            normalized = tuple(
                direction
                for direction in (
                    str(item or "").upper().strip() for item in allowed_signal_directions
                )
                if direction in {"LONG", "SHORT"}
            )
            if normalized:
                return tuple(dict.fromkeys(normalized))
        profile = str(directional_side_filter_profile or "").lower().strip()
        if profile in {"long_only_research", "suppress_short_research"}:
            return ("LONG",)
        if profile == "short_only_research":
            return ("SHORT",)
        return ("LONG", "SHORT")

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None
