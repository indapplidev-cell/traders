from app.engine_market_data.continuous_sync_cli import build_parser, config_from_args


def test_cli_parses_lists_and_once():
    config = config_from_args(build_parser().parse_args(["--symbols", "BTCUSDT,ETHUSDT", "--timeframes", "1m,15m", "--once"]))
    assert config.symbols == ["BTCUSDT", "ETHUSDT"] and not config.continuous
