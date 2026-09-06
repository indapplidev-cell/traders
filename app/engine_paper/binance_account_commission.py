"""Protected Binance Spot account-commission authority for PAPER economics."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import tempfile
import time
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

from app.config.trade_parameters import SCALPING_V2
from app.engine_market_data.market_symbol import normalize_market_symbol


PROVIDER_VERSION = "binance-spot-account-commission-rest-v1"
SNAPSHOT_TYPE = "BINANCE_ACCOUNT_COMMISSION_SNAPSHOT"
DEFAULT_BASE_URL = "https://api.binance.com"


class CommissionTransport(Protocol):
    def get(
        self, url: str, *, params: Mapping[str, object], headers: Mapping[str, str]
    ) -> Any: ...


@dataclass(frozen=True, slots=True)
class BinanceCredentials:
    api_key: str
    secret_key: str


@dataclass(frozen=True, slots=True)
class RefreshResult:
    status: str
    active_symbols: int
    ready_symbols: int
    fetched_at: str | None
    snapshot_id: str | None
    real_account_data: bool
    stub_active: bool = False
    queried_symbols: int = 0


def _credential_pair(payload: Mapping[str, object]) -> BinanceCredentials | None:
    normalized = {str(key).lower().replace("-", "_"): str(value).strip() for key, value in payload.items()}
    api_key = normalized.get("api_key") or normalized.get("apikey") or normalized.get("key")
    secret = (
        normalized.get("api_secret") or normalized.get("api_secret_key")
        or normalized.get("secret_key") or normalized.get("secret")
    )
    if api_key and secret and len(api_key) >= 16 and len(secret) >= 16:
        return BinanceCredentials(api_key, secret)
    return None


def read_credentials(path: Path) -> BinanceCredentials:
    """Parse the mounted credential secret without logging its contents."""
    try:
        raw = path.read_text(encoding="utf-8-sig").strip()
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, Mapping):
            pair = _credential_pair(decoded)
            if pair is not None:
                return pair
        values: dict[str, str] = {}
        bare: list[str] = []
        for source_line in raw.splitlines():
            line = source_line.strip()
            if not line or line.startswith("#"):
                continue
            separator = "=" if "=" in line else ":" if ":" in line else None
            if separator is None:
                # Support locally documented forms such as
                # "Binance API key <value>" without ever echoing the value.
                candidates = re.findall(r"[A-Za-z0-9_-]{16,}", line)
                lowered = line.lower()
                if candidates and "secret" in lowered:
                    values["api_secret"] = candidates[-1]
                    continue
                if candidates and "api" in lowered:
                    values["api_key"] = candidates[-1]
                    continue
                bare.append(line)
                continue
            key, value = line.split(separator, 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        pair = _credential_pair(values)
        if pair is not None:
            return pair
        if len(bare) == 2 and all(len(value) >= 16 for value in bare):
            return BinanceCredentials(bare[0], bare[1])
    except (OSError, UnicodeError, TypeError, ValueError):
        pass
    raise RuntimeError("Binance account credential source is unavailable or invalid")


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise RuntimeError("invalid Binance account commission response") from exc
    if not result.is_finite() or result < 0:
        raise RuntimeError("invalid Binance account commission response")
    return result


def _rates(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise RuntimeError("invalid Binance account commission response")
    required = ("maker", "taker", "buyer", "seller")
    normalized = {key: format(_decimal(value.get(key)), "f") for key in required}
    return normalized


def parse_commission_response(
    symbol: str,
    payload: object,
    *,
    entry_role: str,
    exit_role: str,
) -> dict[str, object]:
    if not isinstance(payload, Mapping) or str(payload.get("symbol", "")).upper() != symbol:
        raise RuntimeError("invalid Binance account commission response")
    standard = _rates(payload.get("standardCommission"))
    special = _rates(payload.get("specialCommission"))
    tax = _rates(payload.get("taxCommission"))
    discount_raw = payload.get("discount")
    if not isinstance(discount_raw, Mapping):
        raise RuntimeError("invalid Binance account commission response")
    enabled_account = discount_raw.get("enabledForAccount")
    enabled_symbol = discount_raw.get("enabledForSymbol")
    if not isinstance(enabled_account, bool) or not isinstance(enabled_symbol, bool):
        raise RuntimeError("invalid Binance account commission response")
    discount_value = _decimal(discount_raw.get("discount"))
    if discount_value > 1:
        raise RuntimeError("invalid Binance account commission response")
    discount = {
        "enabled_for_account": enabled_account,
        "enabled_for_symbol": enabled_symbol,
        "asset": str(discount_raw.get("discountAsset") or ""),
        "value": format(discount_value, "f"),
    }
    multiplier = discount_value if enabled_account and enabled_symbol else Decimal("1")

    def effective(role: str) -> Decimal:
        role_key = role.lower()
        # Direction is unknown at the shared cost gate. Conservatively cover
        # either BUY or SELL using the larger account side component.
        side_standard = max(_decimal(standard["buyer"]), _decimal(standard["seller"]))
        side_special = max(_decimal(special["buyer"]), _decimal(special["seller"]))
        side_tax = max(_decimal(tax["buyer"]), _decimal(tax["seller"]))
        return (
            (_decimal(standard[role_key]) + side_standard) * multiplier
            + _decimal(special[role_key]) + side_special
            + _decimal(tax[role_key]) + side_tax
        ) * Decimal("10000")

    entry_bps = effective(entry_role)
    exit_bps = effective(exit_role)
    return {
        "standard_commission": standard,
        "special_commission": special,
        "tax_commission": tax,
        "discount": discount,
        "entry_liquidity_role": entry_role,
        "exit_liquidity_role": exit_role,
        "effective_entry_fee_bps": format(entry_bps, "f"),
        "effective_exit_fee_bps": format(exit_bps, "f"),
        "round_trip_fee_bps": format(entry_bps + exit_bps, "f"),
        # Compatibility fields consumed by the established cost adapter.
        "maker_bps": format(effective("MAKER"), "f"),
        "taker_bps": format(effective("TAKER"), "f"),
        "special_commission_state": (
            "PRESENT" if any(_decimal(value) > 0 for value in special.values()) else "NONE"
        ),
        "tax_commission_state": (
            "PRESENT" if any(_decimal(value) > 0 for value in tax.values()) else "NONE"
        ),
    }


class BinanceAccountCommissionClient:
    def __init__(
        self,
        credentials: BinanceCredentials,
        *,
        transport: CommissionTransport | None = None,
        base_url: str = DEFAULT_BASE_URL,
        clock_ms: Callable[[], int] | None = None,
        recv_window_ms: int = 5_000,
        request_timeout_seconds: float = 15.0,
        synchronize_clock: bool = True,
    ) -> None:
        self._credentials = credentials
        self._transport = transport or httpx.Client(timeout=request_timeout_seconds)
        self._base_url = base_url.rstrip("/")
        self._clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._recv_window_ms = recv_window_ms
        self._synchronize_clock = synchronize_clock
        self._server_offset_ms: int | None = None

    def _timestamp_ms(self) -> int:
        local = self._clock_ms()
        if not self._synchronize_clock:
            return local
        if self._server_offset_ms is None:
            try:
                response = self._transport.get(
                    f"{self._base_url}/api/v3/time", params={}, headers={},
                )
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                server_time = int(response.json()["serverTime"])
                self._server_offset_ms = server_time - local
            except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError) as exc:
                raise RuntimeError("Binance server-time synchronization failed") from exc
        return local + self._server_offset_ms

    def fetch(self, symbol: str) -> object:
        symbol = normalize_market_symbol(symbol)
        params: dict[str, object] = {
            "symbol": symbol,
            "recvWindow": self._recv_window_ms,
            "timestamp": self._timestamp_ms(),
        }
        query = urlencode(params)
        params["signature"] = hmac.new(
            self._credentials.secret_key.encode("utf-8"),
            query.encode("utf-8"),
            "sha256",
        ).hexdigest()
        try:
            response = self._transport.get(
                f"{self._base_url}/api/v3/account/commission",
                params=params,
                headers={"X-MBX-APIKEY": self._credentials.api_key},
            )
            if hasattr(response, "raise_for_status"):
                response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, OSError, ValueError, TypeError) as exc:
            raise RuntimeError("Binance account commission refresh failed") from exc


class BinanceAccountCommissionManager:
    """Refresh all configured symbols atomically and reuse a valid cached snapshot."""

    def __init__(
        self,
        client: BinanceAccountCommissionClient,
        snapshot_path: Path,
        symbols: Iterable[str],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self.snapshot_path = snapshot_path
        self.symbols = tuple(dict.fromkeys(normalize_market_symbol(value) for value in symbols))
        if not self.symbols:
            raise ValueError("at least one active symbol is required")
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._last_attempt: datetime | None = None
        self._last_failed = False

    @classmethod
    def from_environment(cls, symbols: Iterable[str]) -> "BinanceAccountCommissionManager | None":
        credential_path = os.environ.get("TRADERS_BINANCE_ACCOUNT_CREDENTIALS_PATH")
        snapshot_path = os.environ.get("TRADERS_BINANCE_COMMISSION_SNAPSHOT_PATH")
        if not credential_path or not snapshot_path:
            return None
        return cls(
            BinanceAccountCommissionClient(read_credentials(Path(credential_path))),
            Path(snapshot_path),
            symbols,
        )

    def _cached(self) -> tuple[dict[str, object] | None, float | None]:
        try:
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            if (
                payload.get("snapshot_type") != SNAPSHOT_TYPE
                or payload.get("real_account_data") is not True
                or payload.get("provider_version") != PROVIDER_VERSION
                or set(payload.get("symbols", {})) != set(self.symbols)
            ):
                return None, None
            fetched = datetime.fromisoformat(str(payload["fetched_at"]).replace("Z", "+00:00"))
            age = max(0.0, (self._clock().astimezone(timezone.utc) - fetched).total_seconds())
            return payload, age
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None, None

    @staticmethod
    def _result(
        payload: dict[str, object] | None, status: str, *, queried_symbols: int = 0,
    ) -> RefreshResult:
        symbols = payload.get("symbols", {}) if payload else {}
        return RefreshResult(
            status=status,
            active_symbols=len(symbols),
            ready_symbols=len(symbols),
            fetched_at=None if payload is None else str(payload.get("fetched_at")),
            snapshot_id=None if payload is None else str(payload.get("snapshot_id")),
            real_account_data=bool(payload and payload.get("real_account_data") is True),
            queried_symbols=queried_symbols,
        )

    def ensure_fresh(self, *, force: bool = False) -> RefreshResult:
        policy = SCALPING_V2.costs.commission
        now = self._clock().astimezone(timezone.utc)
        cached, age = self._cached()
        if not force and cached is not None and age is not None and age < policy.refresh_interval_seconds:
            return self._result(cached, "READY")
        if (
            not force and self._last_failed and self._last_attempt is not None
            and (now - self._last_attempt).total_seconds() < policy.retry_interval_seconds
        ):
            if cached is not None and age is not None and age <= policy.max_snapshot_age_seconds:
                return self._result(cached, "CACHED_READY")
            return RefreshResult("FEE_SOURCE_NOT_READY", len(self.symbols), 0, None, None, False)
        self._last_attempt = now
        try:
            rows = {}
            queried_symbols = 0
            for symbol in self.symbols:
                queried_symbols += 1
                rows[symbol] = parse_commission_response(
                    symbol,
                    self._client.fetch(symbol),
                    entry_role=policy.entry_liquidity_role,
                    exit_role=policy.exit_liquidity_role,
                )
            fetched_at = now.isoformat().replace("+00:00", "Z")
            material = {
                "snapshot_type": SNAPSHOT_TYPE,
                "provider_version": PROVIDER_VERSION,
                "source": "BINANCE_ACCOUNT_COMMISSION",
                "real_account_data": True,
                "fetched_at": fetched_at,
                "symbols": rows,
                "bnb_discount_state": (
                    "ENABLED" if any(
                        value["discount"]["enabled_for_account"]
                        and value["discount"]["enabled_for_symbol"]
                        for value in rows.values()
                    ) else "DISABLED"
                ),
            }
            canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
            material["snapshot_id"] = "binance:account-commission:" + sha256(canonical.encode()).hexdigest()
            self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.snapshot_path.parent,
                prefix=".commission-", suffix=".json", delete=False,
            ) as handle:
                json.dump(material, handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                temporary = Path(handle.name)
            try:
                os.chmod(temporary, 0o600)
                os.replace(temporary, self.snapshot_path)
            finally:
                temporary.unlink(missing_ok=True)
            self._last_failed = False
            return self._result(material, "READY", queried_symbols=queried_symbols)
        except Exception:
            self._last_failed = True
            cached, age = self._cached()
            if cached is not None and age is not None and age <= policy.max_snapshot_age_seconds:
                return self._result(
                    cached, "CACHED_READY", queried_symbols=queried_symbols,
                )
            return RefreshResult(
                "FEE_SOURCE_NOT_READY", len(self.symbols), 0, None, None, False,
                queried_symbols=queried_symbols,
            )


def commission_runtime_status(path: Path | None = None) -> dict[str, object]:
    selected = path or Path(os.environ.get("TRADERS_BINANCE_COMMISSION_SNAPSHOT_PATH", ""))
    try:
        payload = json.loads(selected.read_text(encoding="utf-8"))
        fetched = datetime.fromisoformat(str(payload["fetched_at"]).replace("Z", "+00:00"))
        age = max(0.0, (datetime.now(timezone.utc) - fetched).total_seconds())
        ready = (
            payload.get("snapshot_type") == SNAPSHOT_TYPE
            and payload.get("real_account_data") is True
            and payload.get("provider_version") == PROVIDER_VERSION
            and age <= SCALPING_V2.costs.commission.max_snapshot_age_seconds
        )
        symbols = payload.get("symbols", {}) if isinstance(payload.get("symbols"), Mapping) else {}
        return {
            "commission_source": "BINANCE_ACCOUNT_COMMISSION",
            "status": "READY" if ready else "FEE_SOURCE_NOT_READY",
            "real_account_data": bool(ready),
            "stub_active": False,
            "active_symbols": len(symbols),
            "active_symbols_ready": len(symbols) if ready else 0,
            "fetched_at": payload.get("fetched_at") if ready else None,
            "snapshot_age_seconds": age if ready else None,
            "provider_version": payload.get("provider_version") if ready else None,
            "effective_commission_provenance_visible": bool(ready and symbols),
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return {
            "commission_source": "BINANCE_ACCOUNT_COMMISSION",
            "status": "FEE_SOURCE_NOT_READY",
            "real_account_data": False,
            "stub_active": False,
            "active_symbols": 0,
            "active_symbols_ready": 0,
            "fetched_at": None,
            "snapshot_age_seconds": None,
            "provider_version": PROVIDER_VERSION,
            "effective_commission_provenance_visible": False,
        }


__all__ = (
    "BinanceAccountCommissionClient", "BinanceAccountCommissionManager",
    "BinanceCredentials", "PROVIDER_VERSION", "RefreshResult", "SNAPSHOT_TYPE",
    "commission_runtime_status", "parse_commission_response", "read_credentials",
)
