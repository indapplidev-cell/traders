# ML38.10.27 – Fold-1 Time-Slice / Exit-Mitigation Repair Probe

## Scope

- Add `lv31` research-only fold-1 repair probes for h08/h12.
- Propagate fold repair probe and blackout fields through label grid, training pipeline, diagnostics, walk-forward, reporters, and multi-symbol analysis.
- Keep `lv31` permanently acceptance-blocked with explicit research-only gate enforcement.

## Known Target Dates

- `2026-05-25`
- `2026-05-26`
- `2026-05-28`

## Runtime Counts

- `fast-debug`: `12` configs, expected candidates `24`
- `quick-quality --quick-quality-symbol SOLUSDT`: `26` configs, expected candidates `26`

## Safety

- `lv31` remains research-only and forced `REJECTED`.
- Time-slice blackout is diagnostic-only and can overfit known bad dates.
- No live activation logic was added.
- No acceptance gates were relaxed.

## Validation

- Added blackout summary propagation into profit-aware and walk-forward diagnostics.
- Added `FoldTimeSliceExitRepairProbe` multi-symbol board and markdown section.
- Added targeted stage test coverage for config registration, blackout filtering, runtime counts, probe aggregation, and research-only rejection gate.
