"""Thin executable wrapper for the market-data historical backfill CLI."""

from app.engine_market_data.historical_backfill_cli import main


if __name__ == "__main__":
    raise SystemExit(main())

