from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RegimeLabelConfig:
    config_id: str
    base_label_config_id: str
    regime: str
    horizon: int
    threshold: float
    take_profit_atr: float
    stop_loss_atr: float
    flat_threshold: float
    description: str
    risk_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_id": self.config_id,
            "base_label_config_id": self.base_label_config_id,
            "regime": self.regime,
            "horizon": self.horizon,
            "threshold": self.threshold,
            "take_profit_atr": self.take_profit_atr,
            "stop_loss_atr": self.stop_loss_atr,
            "flat_threshold": self.flat_threshold,
            "description": self.description,
            "risk_note": self.risk_note,
        }


class RegimeLabelConfigPlanner:
    PLANNER_NAME = "regime_label_config_planner"
    PLANNER_VERSION = "ml32"

    def build_configs(
        self,
        *,
        base_label_config_id: str = "lv2_h12_thr05_tp15_sl10",
    ) -> dict[str, Any]:
        configs = [
            RegimeLabelConfig(
                config_id=f"{base_label_config_id}_trend_up",
                base_label_config_id=base_label_config_id,
                regime="trend_up",
                horizon=16,
                threshold=0.55,
                take_profit_atr=1.8,
                stop_loss_atr=1.0,
                flat_threshold=0.55,
                description="Longer horizon for trend-up segments to avoid forcing short labels too early.",
                risk_note="Can still overstate continuation if pullbacks dominate the segment.",
            ),
            RegimeLabelConfig(
                config_id=f"{base_label_config_id}_trend_down",
                base_label_config_id=base_label_config_id,
                regime="trend_down",
                horizon=16,
                threshold=0.55,
                take_profit_atr=1.5,
                stop_loss_atr=1.2,
                flat_threshold=0.55,
                description="Downside-aware symmetric labels for bearish segments.",
                risk_note="Short-side labels can stay sparse if downtrends are brief.",
            ),
            RegimeLabelConfig(
                config_id=f"{base_label_config_id}_range",
                base_label_config_id=base_label_config_id,
                regime="range",
                horizon=8,
                threshold=0.70,
                take_profit_atr=1.0,
                stop_loss_atr=1.0,
                flat_threshold=0.75,
                description="Stricter flat zone for range conditions to reduce overtrading.",
                risk_note="May suppress too many samples in low-volatility chop.",
            ),
            RegimeLabelConfig(
                config_id=f"{base_label_config_id}_high_volatility",
                base_label_config_id=base_label_config_id,
                regime="high_volatility",
                horizon=12,
                threshold=0.65,
                take_profit_atr=2.2,
                stop_loss_atr=1.8,
                flat_threshold=0.65,
                description="Wider TP/SL and stronger threshold for volatile segments.",
                risk_note="Signal count can drop sharply in bursty markets.",
            ),
            RegimeLabelConfig(
                config_id=f"{base_label_config_id}_low_volatility",
                base_label_config_id=base_label_config_id,
                regime="low_volatility",
                horizon=16,
                threshold=0.60,
                take_profit_atr=1.2,
                stop_loss_atr=1.0,
                flat_threshold=0.70,
                description="Conservative no-trade bias for low-volatility conditions.",
                risk_note="Can underfit if trend structure appears without volatility expansion.",
            ),
            RegimeLabelConfig(
                config_id=f"{base_label_config_id}_unknown",
                base_label_config_id=base_label_config_id,
                regime="unknown",
                horizon=12,
                threshold=0.65,
                take_profit_atr=1.4,
                stop_loss_atr=1.1,
                flat_threshold=0.70,
                description="Fallback config when the regime signal is missing or ambiguous.",
                risk_note="Conservative fallback can still hide edge if regime detection is weak.",
            ),
        ]
        return {
            "planner_name": self.PLANNER_NAME,
            "planner_version": self.PLANNER_VERSION,
            "config_count": len(configs),
            "configs": [config.to_dict() for config in configs],
        }
