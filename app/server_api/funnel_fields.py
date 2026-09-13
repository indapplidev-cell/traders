"""Field availability is a server contract, distinct from its nullable value."""
from collections.abc import Mapping


def mapping(value):
    return value if isinstance(value, Mapping) else {}


def market_fields(analysis, *, analysis_reached=True):
    context = mapping(analysis.get('analysis_context'))
    impulse = mapping(mapping(context.get('quality_basis')).get('impulse_context'))
    descriptive = mapping(context.get('funnel_descriptive_sources'))
    values = {
        'atr_pct': impulse.get('atr_pct'),
        'direction_confidence': analysis.get('direction_confidence'),
        'liquidity_state': analysis.get('liquidity_state'),
        'structure_state': descriptive.get('structure_state'),
        'volume_state': analysis.get('volume_state'),
        'volume_context': descriptive.get('volume_context'),
    }
    states = {}
    for key, value in values.items():
        states[key] = ('AVAILABLE' if value is not None else
                       'NOT_REACHED' if not analysis_reached else
                       'NOT_EVALUATED' if key in {'direction_confidence', 'liquidity_state', 'volume_state'} else
                       'SOURCE_UNAVAILABLE')
    return {**values, 'semantic_states': states}


def timeframe_states(watermarks, required):
    return {tf: 'NOT_APPLICABLE' if tf not in required else
                'AVAILABLE' if stamp is not None else 'SOURCE_UNAVAILABLE'
            for tf, stamp in watermarks.items()}


def detail_states(detail, trace):
    states = dict(mapping(detail.get('semantic_states')))
    for key, value in detail.items():
        if key in {'semantic_states', 'canonical_stage_trace'}:
            continue
        if value is not None:
            states[key] = 'AVAILABLE'
            continue
        if key in states:
            continue
        if key.startswith(('entry', 'stop', 'atr', 'geometry')):
            owner = 'GEOMETRY_VALID'
        elif key.startswith(('target', 'minimum_economically')):
            owner = 'TARGET_VALID'
        elif key.startswith(('fee', 'cost', 'spread', 'depth', 'slippage', 'total_modeled', 'economic', 'expected_net')):
            owner = 'NET_COST_PASS'
        elif 'rr' in key or key.startswith(('probability', 'expected_ev')):
            owner = 'RR_PASS'
        elif key.startswith(('risk', 'quantity', 'planned_quantity', 'planned_notional', 'notional')):
            owner = 'RISK_ADMITTED'
        else:
            owner = 'PAPER_PLAN'
        states[key] = ('NOT_REACHED' if trace.get(owner) == 'NOT_REACHED' else
                       'NOT_APPLICABLE' if key.endswith(('reason', 'reason_code')) and trace.get(owner) == 'PASS' else
                       'NOT_EVALUATED')
    return states
