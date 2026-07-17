from scripts.engine_orchestrator_online_pipeline import build_parser


def test_cli_modes_and_lists_parse():
    args = build_parser().parse_args(["--symbols", "BTCUSDT,ETHUSDT", "--once", "--dry-run"])
    assert args.symbols == ("BTCUSDT", "ETHUSDT")
    assert args.once and args.dry_run
