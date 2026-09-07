"""Public replay surface backed by the authoritative engine implementation."""

from .engine import _baseline_control, _dataset_coverage, _replay_time_stop

baseline_control = _baseline_control
dataset_coverage = _dataset_coverage
replay_time_stop = _replay_time_stop

__all__ = ["baseline_control", "dataset_coverage", "replay_time_stop"]
