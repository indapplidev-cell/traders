"""Bounded offline acceptance of natural exported rows and server stage parity."""
import argparse
import json
from pathlib import Path
from collections import Counter

from app.server_api.funnel_state import STAGE_ALIASES


EXPECTED = dict(min_net_edge_bps=73.004386, minimum_planned_rr=1.953403,
                stop_max_bps=48.496589, target_min_bps=49.163216)


def audit(rows):
    mismatches = []
    missing = []
    for row in rows:
        for stage, alias in STAGE_ALIASES.items():
            if alias not in row['funnel_trace']:
                missing.append({'symbol': row['symbol'], 'stage': stage})
                continue  # Older schema omitted these stages; mapping records additions.
            downstream = row['downstream_stage_trace'][stage]
            projected = row['funnel_trace'][alias]
            actual = projected.get('canonical_status', {'APPROVED': 'PASS', 'WAIT': 'DEFERRED', 'NO_PLAN': 'REJECTED'}.get(projected['status'], projected['status']))
            if downstream != actual:
                mismatches.append({'symbol': row['symbol'], 'stage': stage, 'downstream': downstream, 'funnel': actual})
    configs = [row.get('effective_configuration') for row in rows]
    valid = all(c and c['parameters'] == EXPECTED and len(c['config_content_hash']) == 64
                and len(c['config_epoch_id']) == 64 and c['source_commit'] and c['runtime_loaded_at_utc'] for c in configs)
    return dict(rows=len(rows), cycles=dict(Counter(r['timestamp'] for r in rows)),
                symbols=sorted({r['symbol'] for r in rows}), trace_mismatch_count=len(mismatches),
                mismatches=mismatches, every_row_provenance_valid=valid,
                missing_projection_stages=missing,
                epoch_ids=sorted({c['config_epoch_id'] for c in configs if c}),
                mapping=[dict(canonical_stage=k, downstream_field=k, funnel_field=v,
                              desktop_field='downstream_stage_trace.' + k) for k, v in STAGE_ALIASES.items()])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    result = audit(rows)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in {'mapping', 'mismatches'}}))


if __name__ == '__main__':
    main()
