from app.training.training_service import build_training_run_id


def test_training_run_id_is_unique_for_fast_parallel_calls() -> None:
    ids = {
        build_training_run_id(
            model_version="ml_candle_mlp_v1_2026_06_15_120520",
            symbol="ETHUSDT",
            interval="15m",
            horizon_candles=12,
            label_version="lv2_h12_thr03_tp10_sl10",
        )
        for _ in range(200)
    }

    assert len(ids) == 200
    assert all(run_id.startswith("train_ml_candle_mlp_v1") for run_id in ids)
    assert all(len(run_id) <= 100 for run_id in ids)
