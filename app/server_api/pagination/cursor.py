from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone

from app.server_api.errors.api_errors import ApiError
from app.server_api.repositories.records import CursorPosition


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("cursor timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def encode_cursor(kind: str, position: CursorPosition) -> str:
    body = {"v": 1, "kind": kind, "updated_at": _utc_text(position.updated_at), "id": position.identifier}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    body["check"] = hashlib.sha256(canonical).hexdigest()[:16]
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode_cursor(value: str | None, kind: str) -> CursorPosition | None:
    if value is None:
        return None
    try:
        if not value or len(value) > 1024:
            raise ValueError
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        payload = json.loads(raw)
        if set(payload) != {"v", "kind", "updated_at", "id", "check"}:
            raise ValueError
        check = payload.pop("check")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if payload["v"] != 1 or payload["kind"] != kind:
            raise ValueError
        if check != hashlib.sha256(canonical).hexdigest()[:16]:
            raise ValueError
        timestamp = datetime.fromisoformat(str(payload["updated_at"]).replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError
        identifier = str(payload["id"])
        if not identifier or len(identifier) > 128:
            raise ValueError
        return CursorPosition(timestamp.astimezone(timezone.utc), identifier)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise ApiError(422, "INVALID_CURSOR", "The pagination cursor is invalid.") from None
