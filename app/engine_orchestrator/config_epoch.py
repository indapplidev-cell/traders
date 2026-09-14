"""Public configuration identity captured with the decision runner, never at export."""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import os

from app.config.trade_parameters import ResolvedParameterSet


@dataclass(frozen=True, slots=True)
class ConfigurationEpoch:
    parameter_set_id: str
    parameter_set_version: str
    config_content_hash: str
    runtime_loaded_at_utc: str
    runtime_activated_at_utc: str | None
    config_generation: int | None
    config_source: str
    source_commit: str | None
    parameters: tuple[tuple[str, float], ...]

    @classmethod
    def capture(cls, resolved: ResolvedParameterSet, *, loaded_at: str | None = None):
        p = resolved.parameters
        return cls(
            resolved.id, resolved.version, resolved.resolved_config_hash,
            loaded_at or resolved.loaded_at or datetime.now(timezone.utc).isoformat(),
            resolved.activated_at,
            resolved.config_generation,
            resolved.source_path or 'config/trading/trade_parameters.yaml',
            os.environ.get('TRADERS_RUNTIME_SOURCE_IDENTITY'),
            (('min_net_edge_bps', p.economics.min_net_edge_bps),
             ('minimum_planned_rr', p.geometry.minimum_planned_rr),
             ('stop_max_bps', p.geometry.stop_max_bps),
             ('target_min_bps', p.geometry.target_min_bps)),
        )

    def project(self):
        return {
            'trade_profile_id': 'trade-5m-v2',
            'parameter_set_id': self.parameter_set_id,
            'parameter_set_version': self.parameter_set_version,
            'config_content_hash': self.config_content_hash,
            'config_epoch_id': sha256((self.config_content_hash + '\0' + self.runtime_loaded_at_utc).encode()).hexdigest(),
            'runtime_loaded_at_utc': self.runtime_loaded_at_utc,
            'runtime_activated_at_utc': self.runtime_activated_at_utc,
            'config_generation': self.config_generation,
            'source_commit': self.source_commit,
            'config_source': self.config_source,
            'parameters': dict(self.parameters),
        }
