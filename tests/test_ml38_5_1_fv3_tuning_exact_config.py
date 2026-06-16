from pathlib import Path
from unittest.mock import patch

from app.cli.commands import run_ml38_2_fv3_tuning


def test_ml38_2_fv3_tuning_can_select_exact_base_label_config_id() -> None:
    with patch("app.cli.commands.run_feature_regime_experiment") as mocked:
        mocked.return_value = {"status": "ok"}

        payload = run_ml38_2_fv3_tuning(
            symbol="BTCUSDT",
            interval="15m",
            start_date="2026-05-01",
            end_date="2026-06-15",
            experiment_id="debug",
            base_label_config_ids=["lv2_h08_thr03_tp10_sl10"],
            output_dir=Path("reports/feature_regime_experiments"),
        )

    assert payload == {"status": "ok"}
    kwargs = mocked.call_args.kwargs
    assert kwargs["base_label_config_ids"] == ["lv2_h08_thr03_tp10_sl10"]
    assert kwargs["max_configs"] is None
    assert kwargs["skip_candle_load"] is True
