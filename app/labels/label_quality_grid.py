from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LabelQualityGridConfig:
    config_id: str
    label_version: str
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
            "label_version": self.label_version,
            "horizon": self.horizon,
            "threshold": self.threshold,
            "take_profit_atr": self.take_profit_atr,
            "stop_loss_atr": self.stop_loss_atr,
            "flat_threshold": self.flat_threshold,
            "description": self.description,
            "risk_note": self.risk_note,
        }


class LabelQualityGridPlanner:
    PLANNER_NAME = "label_quality_grid_planner"
    PLANNER_VERSION = "ml30"

    def build_grid(self) -> dict[str, Any]:
        configs = [
            LabelQualityGridConfig(
                config_id="lv2_h08_thr04_tp10_sl10",
                label_version="lv2_h08_thr04_tp10_sl10",
                horizon=8,
                threshold=0.4,
                take_profit_atr=1.0,
                stop_loss_atr=1.0,
                flat_threshold=0.4,
                description="Short horizon with symmetric TP/SL to reduce directional over-commitment.",
                risk_note="May stay noisy because horizon is still close to lv1.",
            ),
            LabelQualityGridConfig(
                config_id="lv2_h08_thr05_tp15_sl10",
                label_version="lv2_h08_thr05_tp15_sl10",
                horizon=8,
                threshold=0.5,
                take_profit_atr=1.5,
                stop_loss_atr=1.0,
                flat_threshold=0.5,
                description="Closest extension of lv1 with stricter flat separation.",
                risk_note="Can still collapse if feature set remains weak.",
            ),
            LabelQualityGridConfig(
                config_id="lv2_h12_thr05_tp15_sl10",
                label_version="lv2_h12_thr05_tp15_sl10",
                horizon=12,
                threshold=0.5,
                take_profit_atr=1.5,
                stop_loss_atr=1.0,
                flat_threshold=0.5,
                description="Slightly longer horizon to smooth micro-noise in direction labels.",
                risk_note="Longer holding horizon can reduce signal density.",
            ),
            LabelQualityGridConfig(
                config_id="lv2_h16_thr06_tp20_sl10",
                label_version="lv2_h16_thr06_tp20_sl10",
                horizon=16,
                threshold=0.6,
                take_profit_atr=2.0,
                stop_loss_atr=1.0,
                flat_threshold=0.6,
                description="More selective direction threshold with stronger TP asymmetry.",
                risk_note="Can over-prune labels and increase class sparsity.",
            ),
            LabelQualityGridConfig(
                config_id="lv2_h24_thr07_tp20_sl15",
                label_version="lv2_h24_thr07_tp20_sl15",
                horizon=24,
                threshold=0.7,
                take_profit_atr=2.0,
                stop_loss_atr=1.5,
                flat_threshold=0.7,
                description="Longer trend-oriented horizon for stability-focused experiments.",
                risk_note="Highest risk of low sample count and slower feedback loop.",
            ),
            LabelQualityGridConfig(
                config_id="lv3_h12_thr06_tp10_sl10",
                label_version="lv3_h12_thr06_tp10_sl10",
                horizon=12,
                threshold=0.6,
                take_profit_atr=1.0,
                stop_loss_atr=1.0,
                flat_threshold=0.6,
                description="Balanced horizon with stricter flat zone to reduce forced UP predictions.",
                risk_note="Can lower signal count if features remain weak.",
            ),
            LabelQualityGridConfig(
                config_id="lv3_h16_thr06_tp15_sl15",
                label_version="lv3_h16_thr06_tp15_sl15",
                horizon=16,
                threshold=0.6,
                take_profit_atr=1.5,
                stop_loss_atr=1.5,
                flat_threshold=0.6,
                description="Symmetric TP/SL with longer horizon to reduce directional skew.",
                risk_note="May trade less often because symmetric exits are stricter.",
            ),
            LabelQualityGridConfig(
                config_id="lv3_h20_thr07_tp15_sl15",
                label_version="lv3_h20_thr07_tp15_sl15",
                horizon=20,
                threshold=0.7,
                take_profit_atr=1.5,
                stop_loss_atr=1.5,
                flat_threshold=0.7,
                description="Broader no-trade zone with moderate reward/risk symmetry.",
                risk_note="Higher flat threshold can underfit if trend opportunities are sparse.",
            ),
            LabelQualityGridConfig(
                config_id="lv3_h24_thr08_tp20_sl20",
                label_version="lv3_h24_thr08_tp20_sl20",
                horizon=24,
                threshold=0.8,
                take_profit_atr=2.0,
                stop_loss_atr=2.0,
                flat_threshold=0.8,
                description="Strong separation and symmetric exits for collapse-resistant trend labels.",
                risk_note="Most selective config; risk of low sample count is high.",
            ),
            LabelQualityGridConfig(
                config_id="lv3_h32_thr08_tp20_sl15",
                label_version="lv3_h32_thr08_tp20_sl15",
                horizon=32,
                threshold=0.8,
                take_profit_atr=2.0,
                stop_loss_atr=1.5,
                flat_threshold=0.8,
                description="Long horizon with stronger flat zone and milder asymmetry than earlier configs.",
                risk_note="Long holding horizon can hurt responsiveness in choppy regimes.",
            ),
        ]
        return {
            "planner_name": self.PLANNER_NAME,
            "planner_version": self.PLANNER_VERSION,
            "config_count": len(configs),
            "configs": [config.to_dict() for config in configs],
        }
