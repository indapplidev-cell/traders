"""Compatibility shim for the authoritative ``traders_ml.parameter_sweep`` package."""

from traders_ml.parameter_sweep.engine import *  # noqa: F401,F403
from traders_ml.parameter_sweep.engine import (
    _baseline_control, _candidate_config, _candidate_indices, _config_from_index,
    _conditional_variants, _dataset_coverage, _gate_funnel,
    _shadow_observation, _stale_policy,
)


def main() -> None:
    from traders_ml.parameter_sweep.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
