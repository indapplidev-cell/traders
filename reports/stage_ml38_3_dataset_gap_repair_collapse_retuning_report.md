# Stage ML38.3 — Dataset Gap Repair and Collapse Retuning

## Status

technical_status: completed  
model_accepted: no  
can proceed to ML38.4: yes  
can proceed to ML39: no  

## Starting Point

ML38.2.1 showed that all FV3 tuning candidates were rejected. The main blocker looked like dataset gap quality.

The old raw candle gap check reported missing candles after the last available candle:

- BTCUSDT: 59 requested missing candles
- ETHUSDT: 59 requested missing candles
- SOLUSDT: 59 requested missing candles

ML38.3 was created to separate real internal historical gaps from trailing incomplete current-day ranges.

## Gap Diagnostics

New diagnostic command:

```text
dataset-gap-report

Result for BTCUSDT / ETHUSDT / SOLUSDT:

SymbolActual candlesRequested missingInternal gapsEffective gaps for trainingTrailing incompleteTraining safeSeverity for training
BTCUSDT50917590059trueOK
ETHUSDT50917590059trueOK
SOLUSDT50917590059trueOK

Important fields:

effective_gap_count_for_training = 0
gap_severity_for_training = OK
training_safe = true
dataset_safe_for_training = true
Root Cause

The detected missing timestamps are not real historical gaps inside the dataset.

Root cause:

trailing_incomplete_current_day_only

The candles are continuous from:

2025-01-01T00:00:00+00:00

to:

2026-06-15T09:00:00+00:00

The missing timestamps are only after the last loaded candle and belong to the incomplete trailing part of the requested end day.

Fixes

Implemented:

added app/diagnostics/dataset_gap_report.py;
added CLI command dataset-gap-report;
separated raw requested missing candles from effective training gaps;
excluded trailing incomplete current-day range from training gap severity;
kept real internal gaps as blocking;
added tests for ML38.3 gap diagnostics and training-safe gap semantics.

The old raw gap check may still report:

gap_count = 59
is_valid = false

But ML training must use:

effective_gap_count_for_training = 0
gap_severity_for_training = OK
training_safe = true
Tests

Passed locally:

python -m pytest tests/test_ml38_3_dataset_gap_report.py
python -m pytest tests/test_ml38_3_gap_gate_uses_dataset_report.py
python -m pytest tests/test_stage_ml38_3_report.py
python -m pytest

Full result:

446 passed, 1 warning
Decision

ML38.3 is accepted as a dataset gap semantics fix.

Dataset gap blocker is clarified:

no real internal historical gaps were found for BTCUSDT / ETHUSDT / SOLUSDT;
trailing incomplete current-day range must not block training;
FV3 tuning can be rerun with corrected gap semantics.

Decision:

can proceed to ML38.4: yes
can proceed to ML39: no
Next Step

Next stage:

ML38.4 — Fresh FV3 Tuning Rerun After Gap Semantics Fix

Goal:

rerun BTCUSDT / ETHUSDT / SOLUSDT FV3 tuning matrix;
confirm gap_quality_gate no longer fails because of trailing incomplete current-day range;
confirm wrapper_completed_end_to_end = true;
confirm manual_archive_assembly_used = false;
check whether collapse remains after gap blocker removal.

ML39 is still too early.