# ML38.10.21.1 вЂ” directional side comparator payload/source-of-truth fix

## Status
Implemented.

## Why this fix exists
ML38.10.21 runtime produced valid `lv28` side-ablation candidates, but the multi-symbol comparator board classified all candidates as `BOTH_DIRECTIONS` and returned `NO_SIDE_ABLATION_CANDIDATES`. The top-level candidate payload already contained `directional_side_filter_profile`, `allowed_signal_directions`, `profit_factor`, and `profit_total_r`; the comparator did not use those fields as source-of-truth.

## Fix
- Comparator now reads side profile from top-level `directional_side_filter_profile`.
- Fallback uses `allowed_signal_directions` and `label_config`.
- Comparator reads PF/Total R from top-level candidate fields before nested diagnostics.
- Delta board now becomes available when `LONG_ONLY`, `SHORT_ONLY`, or `SUPPRESS_SHORT` candidates exist.
- Added regression tests using runtime-like `lv28` payloads.

## Safety
- live trading disabled
- auto activation disabled
- traders-core integration disabled
- research-only side suppression remains research-only
- no runtime commands were executed by Codex
