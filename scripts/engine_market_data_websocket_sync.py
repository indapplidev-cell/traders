"""Persist Binance final-kline WebSocket events for the low-latency fast path."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import websockets

from app.engine_market_data.binance_kline_ws import BinanceKlineWebSocketClient
from app.engine_market_data.db.candle_repository import CandleRepository
from app.engine_market_data.db.session import create_market_data_session_factory
from app.engine_market_data.sync_state_repository import SyncStateRepository
from app.engine_market_data.websocket_sync import WebSocketClosedCandleSync
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--symbols", default=",".join(PREPARED_NEXT_TRADING_UNIVERSE.symbols))
    result.add_argument("--timeframes", default="1m,5m,15m,1h")
    return result


async def run(argv: list[str] | None = None) -> None:
    args = parser().parse_args(argv)
    factory = create_market_data_session_factory()
    client = BinanceKlineWebSocketClient(websocket_factory=websockets.connect)
    service = WebSocketClosedCandleSync(
        client, CandleRepository(factory), SyncStateRepository(factory),
    )
    print(json.dumps({
        "event": "websocket_market_data_started",
        "symbols": list(_csv(args.symbols)),
        "timeframes": list(_csv(args.timeframes)),
    }, sort_keys=True))
    await service.run(_csv(args.symbols), _csv(args.timeframes))


def main() -> int:
    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
