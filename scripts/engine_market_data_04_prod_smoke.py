"""Run the opt-in real PostgreSQL/Binance ENGINE-MARKET-DATA-04 smoke."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.engine_market_data.prod_smoke import ProdSmokeRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="reports/engine_market_data/prod_smoke_04")
    parser.add_argument("--database-url")
    parser.add_argument("--restart-wait-seconds", type=int, default=130)
    parser.add_argument("--preflight-symbol", default="BTCUSDT")
    parser.add_argument("--preflight-timeframe", default="15m")
    args = parser.parse_args(argv)
    trace = ProdSmokeRunner(Path(args.output_dir), database_url=args.database_url,
                            restart_wait_seconds=args.restart_wait_seconds,
                            preflight_symbol=args.preflight_symbol,
                            preflight_timeframe=args.preflight_timeframe).run()
    print(json.dumps({"final_verdict": trace["final_verdict"],
                      "artifacts": str(Path(args.output_dir))}, indent=2))
    return 0 if trace["final_verdict"] == "PROD_SMOKE_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
