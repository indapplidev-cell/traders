from app.engine_orchestrator.runtime_parameters import resolve_runtime_parameters


def test_scalping_performance_bounds_are_finite_and_15m_identity_is_unchanged():
    five = resolve_runtime_parameters("trade-5m-v1")
    fifteen = resolve_runtime_parameters("trade-15m-v1")
    assert five.bounded_book_depth_limit == 100
    assert five.market_data_context_windows == (("1m", 60), ("5m", 120), ("15m", 64), ("1h", 50))
    assert fifteen.parameter_set_id == "trade-15m-v1-runtime-v1-44aa91202a60146c"
