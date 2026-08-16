"""Deterministic bounded public identities for canonical business lineage."""

from __future__ import annotations

from hashlib import sha256
import re
from typing import Final


BOUNDED_LINEAGE_IDENTITY_ALGORITHM_VERSION: Final = "bounded-lineage-sha256-v1"
_NAMESPACE_RE = re.compile(r"[a-z0-9][a-z0-9:-]{0,30}\Z")


def bounded_lineage_identity(
    namespace: str,
    canonical_full_identity: str,
    *,
    maximum_length: int = 128,
) -> str:
    """Return ``<namespace>:<sha256>`` over exact UTF-8 canonical text.

    The canonical value is intentionally not truncated or locale-normalized.
    Callers retain it in their typed lineage fields/payload while this helper
    supplies the bounded public identity used by downstream safety contracts.
    """

    if not isinstance(namespace, str) or _NAMESPACE_RE.fullmatch(namespace) is None:
        raise ValueError("bounded lineage namespace is invalid")
    if not isinstance(canonical_full_identity, str) or not canonical_full_identity:
        raise ValueError("canonical full lineage identity must not be empty")
    if not isinstance(maximum_length, int) or maximum_length < 1:
        raise ValueError("maximum identity length must be positive")
    digest = sha256(canonical_full_identity.encode("utf-8")).hexdigest()
    value = f"{namespace}:{digest}"
    if len(value) > maximum_length:
        raise ValueError("bounded lineage namespace exceeds the identity contract")
    return value


__all__ = (
    "BOUNDED_LINEAGE_IDENTITY_ALGORITHM_VERSION",
    "bounded_lineage_identity",
)
