"""Read only persisted decision provenance; never resolve the API host's YAML."""
from collections.abc import Mapping
from copy import deepcopy


def effective_configuration(result):
    if result is None:
        return None
    snapshots = []
    for name in ('analysis', 'setup', 'strategy', 'risk', 'paper'):
        payload = getattr(result, name + '_payload_json', None)
        value = payload.get('effective_configuration') if isinstance(payload, Mapping) else None
        if isinstance(value, Mapping):
            snapshots.append(dict(value))
    if not snapshots:
        return None  # Historical rows are not relabelled with a newer epoch.
    if any(value != snapshots[0] for value in snapshots[1:]):
        raise ValueError('conflicting persisted runtime configuration snapshots')
    return deepcopy(snapshots[0])
