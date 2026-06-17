from __future__ import annotations

from typing import Any

from app.labels.label_quality_grid import LabelQualityGridPlanner


ML38_5_ANTI_COLLAPSE_CONFIG_IDS = (
    "lv3_h04_thr02_tp08_sl08_ac",
    "lv3_h04_thr025_tp08_sl08_ac",
    "lv3_h06_thr025_tp10_sl08_ac",
    "lv3_h06_thr03_tp10_sl10_ac",
    "lv3_h08_thr025_tp10_sl08_ac",
    "lv3_h08_thr03_tp12_sl08_ac",
)

ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS = (
    "lv4_h06_thr035_tp12_sl08_cp",
    "lv4_h06_thr04_tp12_sl10_cp",
    "lv4_h08_thr035_tp12_sl08_cp",
    "lv4_h08_thr04_tp15_sl10_cp",
    "lv4_h12_thr04_tp12_sl08_cp",
    "lv4_h12_thr05_tp15_sl10_cp",
)

ML38_2_FV3_TUNING_CONFIG_IDS = (
    "lv2_h08_thr03_tp10_sl10",
    "lv2_h08_thr04_tp10_sl10",
    "lv2_h08_thr05_tp15_sl10",
    "lv2_h12_thr03_tp10_sl10",
    "lv2_h12_thr04_tp15_sl10",
    "lv2_h12_thr05_tp15_sl10",
    "lv2_h16_thr04_tp15_sl10",
    "lv2_h16_thr05_tp20_sl10",
    *ML38_5_ANTI_COLLAPSE_CONFIG_IDS,
    *ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS,
)
ML38_2_REQUIRED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
ML38_2_FEATURE_VERSION = "fv3_candle_ta_context"


class ML382FV3TuningMatrix:
    def build(self) -> dict[str, Any]:
        available = {
            item["config_id"]: dict(item)
            for item in LabelQualityGridPlanner().build_grid()["configs"]
        }
        configs = []
        missing = []
        for config_id in ML38_2_FV3_TUNING_CONFIG_IDS:
            payload = available.get(config_id)
            if payload is None:
                missing.append(config_id)
                continue
            config_payload = dict(payload)
            config_payload["feature_version"] = ML38_2_FEATURE_VERSION
            configs.append(config_payload)
        return {
            "stage": "ML38.2",
            "anti_collapse_stage": "ML38.5",
            "confidence_profitability_stage": "ML38.6",
            "feature_version": ML38_2_FEATURE_VERSION,
            "anti_collapse_config_ids": list(ML38_5_ANTI_COLLAPSE_CONFIG_IDS),
            "anti_collapse_config_count": len(ML38_5_ANTI_COLLAPSE_CONFIG_IDS),
            "confidence_profit_config_ids": list(ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS),
            "confidence_profit_config_count": len(ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS),
            "config_count": len(configs),
            "configs": configs,
            "config_ids": [item["config_id"] for item in configs],
            "required_symbols": list(ML38_2_REQUIRED_SYMBOLS),
            "missing_configs": missing,
            "safety": {
                "traders_core_integration": False,
                "live_trading": False,
                "orders_trades": False,
                "model_auto_activation": False,
            },
        }
