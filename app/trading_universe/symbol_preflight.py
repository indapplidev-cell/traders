"""Fail-closed Binance authority checks for the configured Scalping universe."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import json
import os
from pathlib import Path
import tempfile
from typing import Mapping
from sqlalchemy import delete

from app.engine_market_data.binance_public_rest import BinancePublicRestClient
from app.engine_market_data.timeframe import timeframe_to_milliseconds
from app.engine_paper.binance_account_commission import BinanceAccountCommissionManager
from app.instrument_constraints.registry import (
    REGISTRY_VERSION,
    SOURCE_OBSERVED_AT_UTC,
    SOURCE_SNAPSHOT_SHA256,
)
from app.db.paper_models import TradingUniverseSymbolPreflightRecord
from app.trading_universe.domain import SCALPING_TRADING_UNIVERSE


PREFLIGHT_SCHEMA_VERSION = "BINANCE_SPOT_SYMBOL_PREFLIGHT/1"
PREFLIGHT_FILENAME = "binance-symbol-preflight.json"


class SymbolFailReason(StrEnum):
    SYMBOL_NOT_TRADING = "SYMBOL_NOT_TRADING"
    SYMBOL_FILTERS_UNAVAILABLE = "SYMBOL_FILTERS_UNAVAILABLE"
    SYMBOL_BOOK_UNAVAILABLE = "SYMBOL_BOOK_UNAVAILABLE"
    SYMBOL_1M_DATA_UNAVAILABLE = "SYMBOL_1M_DATA_UNAVAILABLE"
    SYMBOL_5M_DATA_UNAVAILABLE = "SYMBOL_5M_DATA_UNAVAILABLE"
    SYMBOL_DATA_STALE = "SYMBOL_DATA_STALE"
    SYMBOL_COMMISSION_UNAVAILABLE = "SYMBOL_COMMISSION_UNAVAILABLE"
    SYMBOL_METADATA_INVALID = "SYMBOL_METADATA_INVALID"


@dataclass(frozen=True, slots=True)
class SymbolPreflightStatus:
    symbol: str
    configured: bool
    active: bool
    status: str
    reason: str | None
    one_minute_fresh: bool
    five_minute_fresh: bool
    commission_authority: str
    tick_size: str | None = None
    step_size: str | None = None
    min_quantity: str | None = None
    min_notional: str | None = None


@dataclass(frozen=True, slots=True)
class UniversePreflightReport:
    observed_at: str
    configured_symbols: tuple[str, ...]
    active_symbols: tuple[str, ...]
    disabled_symbols: tuple[str, ...]
    symbols: tuple[SymbolPreflightStatus, ...]
    exchange_info_registry_version: str
    exchange_info_observed_at: str
    exchange_info_snapshot_sha256: str
    commission_snapshot_id: str | None
    schema_version: str = PREFLIGHT_SCHEMA_VERSION


def preflight_path_from_environment() -> Path:
    explicit = os.environ.get("TRADERS_BINANCE_SYMBOL_PREFLIGHT_PATH")
    if explicit:
        return Path(explicit)
    commission = os.environ.get("TRADERS_BINANCE_COMMISSION_SNAPSHOT_PATH")
    if commission:
        return Path(commission).with_name(PREFLIGHT_FILENAME)
    return Path("production_control/commission") / PREFLIGHT_FILENAME


def _positive(value: object) -> str:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("invalid decimal") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError("non-positive decimal")
    return format(parsed, "f")


def _closed_candles_ready(candles: list[object], timeframe: str, now_ms: int) -> tuple[bool, bool]:
    duration = timeframe_to_milliseconds(timeframe)
    closed = [item for item in candles if item.close_time_ms < now_ms]
    if len(closed) < 3:
        return False, False
    contiguous = all(
        current.open_time_ms - previous.open_time_ms == duration
        for previous, current in zip(closed, closed[1:])
    )
    fresh = now_ms - closed[-1].close_time_ms <= duration * 2
    return contiguous, fresh


def run_symbol_preflight(
    symbols: tuple[str, ...],
    *,
    public_client: BinancePublicRestClient,
    commission_manager: BinanceAccountCommissionManager | None,
    output_path: Path | None = None,
) -> UniversePreflightReport:
    now_ms = public_client.fetch_server_time_ms()
    try:
        exchange = public_client.fetch_exchange_info(symbols)
        exchange_rows = {
            str(item.get("symbol")): item
            for item in exchange["symbols"]
            if isinstance(item, Mapping)
        }
    except Exception:
        exchange_rows = {}
    commission = (
        commission_manager.ensure_fresh(force=True)
        if commission_manager is not None else None
    )
    commission_ready = bool(
        commission is not None
        and commission.status in {"READY", "CACHED_READY"}
        and commission.real_account_data
        and commission.ready_symbols == len(symbols)
    )
    statuses: list[SymbolPreflightStatus] = []
    for symbol in symbols:
        reason: SymbolFailReason | None = None
        one_fresh = five_fresh = False
        tick = step = minimum = notional = None
        row = exchange_rows.get(symbol)
        if not isinstance(row, Mapping):
            reason = SymbolFailReason.SYMBOL_METADATA_INVALID
        elif row.get("status") != "TRADING" or row.get("quoteAsset") != "USDT" or row.get("isSpotTradingAllowed") is not True:
            reason = SymbolFailReason.SYMBOL_NOT_TRADING
        else:
            if not all(
                isinstance(row.get(name), int) and not isinstance(row.get(name), bool) and row.get(name) >= 0
                for name in ("baseAssetPrecision", "quoteAssetPrecision")
            ):
                reason = SymbolFailReason.SYMBOL_METADATA_INVALID
            filters = {
                str(item.get("filterType")): item
                for item in row.get("filters", ())
                if isinstance(item, Mapping)
            }
            try:
                if reason is not None:
                    raise ValueError("invalid precision metadata")
                tick = _positive(filters["PRICE_FILTER"]["tickSize"])
                step = _positive(filters["LOT_SIZE"]["stepSize"])
                minimum = _positive(filters["LOT_SIZE"]["minQty"])
                market = filters.get("MARKET_LOT_SIZE")
                if market is not None:
                    _positive(market["maxQty"])
                notional_filter = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL")
                if not isinstance(notional_filter, Mapping):
                    raise KeyError("notional")
                notional = _positive(notional_filter["minNotional"])
            except (KeyError, ValueError, TypeError):
                if reason is None:
                    reason = SymbolFailReason.SYMBOL_FILTERS_UNAVAILABLE
        if reason is None:
            try:
                public_client.fetch_book_ticker(symbol)
            except Exception:
                reason = SymbolFailReason.SYMBOL_BOOK_UNAVAILABLE
        if reason is None:
            try:
                contiguous, one_fresh = _closed_candles_ready(
                    public_client.fetch_klines(symbol, "1m", limit=32), "1m", now_ms
                )
                if not contiguous:
                    reason = SymbolFailReason.SYMBOL_1M_DATA_UNAVAILABLE
                elif not one_fresh:
                    reason = SymbolFailReason.SYMBOL_DATA_STALE
            except Exception:
                reason = SymbolFailReason.SYMBOL_1M_DATA_UNAVAILABLE
        if reason is None:
            try:
                contiguous, five_fresh = _closed_candles_ready(
                    public_client.fetch_klines(symbol, "5m", limit=32), "5m", now_ms
                )
                if not contiguous:
                    reason = SymbolFailReason.SYMBOL_5M_DATA_UNAVAILABLE
                elif not five_fresh:
                    reason = SymbolFailReason.SYMBOL_DATA_STALE
            except Exception:
                reason = SymbolFailReason.SYMBOL_5M_DATA_UNAVAILABLE
        if reason is None and not commission_ready:
            reason = SymbolFailReason.SYMBOL_COMMISSION_UNAVAILABLE
        active = reason is None
        statuses.append(SymbolPreflightStatus(
            symbol=symbol, configured=True, active=active,
            status="PASS" if active else "SYMBOL_FAIL_CLOSED",
            reason=None if active else reason.value,
            one_minute_fresh=one_fresh, five_minute_fresh=five_fresh,
            commission_authority="BINANCE_ACCOUNT_COMMISSION_SNAPSHOT" if commission_ready else "UNAVAILABLE",
            tick_size=tick, step_size=step, min_quantity=minimum, min_notional=notional,
        ))
    active = tuple(item.symbol for item in statuses if item.active)
    report = UniversePreflightReport(
        observed_at=datetime.fromtimestamp(now_ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z"),
        configured_symbols=symbols,
        active_symbols=active,
        disabled_symbols=tuple(item.symbol for item in statuses if not item.active),
        symbols=tuple(statuses),
        exchange_info_registry_version=REGISTRY_VERSION,
        exchange_info_observed_at=SOURCE_OBSERVED_AT_UTC,
        exchange_info_snapshot_sha256=SOURCE_SNAPSHOT_SHA256,
        commission_snapshot_id=None if commission is None else commission.snapshot_id,
    )
    selected = output_path or preflight_path_from_environment()
    selected.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=selected.parent, delete=False) as stream:
        json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
        temporary = Path(stream.name)
    try:
        os.replace(temporary, selected)
    finally:
        temporary.unlink(missing_ok=True)
    return report


def load_symbol_preflight(path: Path | None = None) -> dict[str, object]:
    selected = path or preflight_path_from_environment()
    try:
        payload = json.loads(selected.read_text(encoding="utf-8"))
        if payload.get("schema_version") != PREFLIGHT_SCHEMA_VERSION:
            raise ValueError("schema")
        return payload
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {
            "schema_version": PREFLIGHT_SCHEMA_VERSION,
            "configured_symbols": [], "active_symbols": [],
            "disabled_symbols": [], "symbols": [],
        }


def persist_symbol_preflight(
    session_factory: object, report: UniversePreflightReport,
) -> None:
    observed_at = datetime.fromisoformat(report.observed_at.replace("Z", "+00:00"))
    with session_factory() as session:
        session.execute(delete(TradingUniverseSymbolPreflightRecord).where(
            TradingUniverseSymbolPreflightRecord.environment == "PRODUCTION",
            TradingUniverseSymbolPreflightRecord.universe_version_id == SCALPING_TRADING_UNIVERSE.version_id,
        ))
        for item in report.symbols:
            session.add(TradingUniverseSymbolPreflightRecord(
                environment="PRODUCTION",
                universe_version_id=SCALPING_TRADING_UNIVERSE.version_id,
                symbol=item.symbol, configured=item.configured, active=item.active,
                status=item.status, reason=item.reason,
                one_minute_fresh=item.one_minute_fresh,
                five_minute_fresh=item.five_minute_fresh,
                commission_authority=item.commission_authority,
                observed_at=observed_at,
                authority_details={
                    "tick_size": item.tick_size, "step_size": item.step_size,
                    "min_quantity": item.min_quantity, "min_notional": item.min_notional,
                    "exchange_info_registry_version": report.exchange_info_registry_version,
                    "exchange_info_snapshot_sha256": report.exchange_info_snapshot_sha256,
                    "commission_snapshot_id": report.commission_snapshot_id,
                },
            ))
        session.commit()


__all__ = (
    "PREFLIGHT_SCHEMA_VERSION", "SymbolFailReason", "SymbolPreflightStatus",
    "UniversePreflightReport", "load_symbol_preflight",
    "persist_symbol_preflight", "preflight_path_from_environment", "run_symbol_preflight",
)
