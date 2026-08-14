"""Narrow production CLI for one audited, atomic universe activation."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker

from app.engine_paper.production_preparation_backend import RUNTIME_DATABASE_KEY
from app.trading_universe.activation import SqlAlchemyTradingUniverseStore, TradingUniverseActivationError


def _sessions():
    raw = os.environ.get(RUNTIME_DATABASE_KEY)
    if not raw:
        raise TradingUniverseActivationError("RUNTIME_DATABASE_BINDING_UNAVAILABLE")
    url = make_url(raw)
    host = os.environ.get("TRADERS_PAPER_RUNTIME_DATABASE_HOST")
    port = os.environ.get("TRADERS_PAPER_RUNTIME_DATABASE_PORT")
    if host is not None or port is not None:
        if url.host not in {"127.0.0.1", "localhost"} or url.port != 5433 or host != "postgres" or port != "5432":
            raise TradingUniverseActivationError("RUNTIME_DATABASE_BINDING_INVALID")
        url = url.set(host=host, port=int(port))
    engine = create_engine(url, hide_parameters=True, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False), engine


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--runtime-revision", required=True)
    args = parser.parse_args(argv)
    engine = None
    try:
        sessions, engine = _sessions()
        state = SqlAlchemyTradingUniverseStore(sessions).activate(
            expected_active_version_id=args.expected,
            target_version_id=args.target,
            reason=args.reason,
            runtime_revision=args.runtime_revision,
        )
        print(json.dumps({
            "active_version_id": state.active_version_id,
            "previous_version_id": state.previous_version_id,
            "generation": state.generation,
            "activated_at": state.activated_at.isoformat().replace("+00:00", "Z"),
            "activation_reason": state.activation_reason,
            "runtime_revision": state.runtime_revision,
            "atomic": True,
            "secret_output": False,
        }, sort_keys=True, separators=(",", ":")))
        return 0
    except TradingUniverseActivationError as error:
        print(json.dumps({"error": str(error), "secret_output": False}, sort_keys=True))
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
