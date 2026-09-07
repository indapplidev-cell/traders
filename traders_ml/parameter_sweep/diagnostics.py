"""Public diagnostic surface backed by the authoritative engine."""

from .engine import _gate_funnel

gate_funnel = _gate_funnel

__all__ = ["gate_funnel"]
