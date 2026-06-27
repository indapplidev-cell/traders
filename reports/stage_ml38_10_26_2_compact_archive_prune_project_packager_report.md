# ML38.10.26.2 - Compact Archive Prune and Project Packager Exclusions

## Status
CODE/TEST PASSED - runtime not executed by Codex.

## Problem
- ML38.10.26.1 fixed self-copy deletion but left per-symbol outputs unpruned.
- Runtime ZIP became too large because self-copy staging skipped compact pruning.
- Project light archive included root-level generated runtime reports, especially `reports/probability_diagnostics_*.json`.

## Changes
- Added in-place `prune_and_compact_report_tree()`.
- Wrapper self-copy staging now validates, compact-prunes, then validates again.
- Compact runtime size caps were added.
- Project packers now exclude generated root reports while keeping `reports/stage_*.md`.

## Runtime counts unchanged
- fast-debug: 20
- quick-quality SOLUSDT: 21

## Validation
- py_compile passed.
- Targeted tests passed.
- Full pytest passed.

## Runtime note
Runtime must be executed manually after this stage.
