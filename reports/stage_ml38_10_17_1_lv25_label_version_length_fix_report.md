# ML38.10.17.1 — lv25 label_version length fix

## Status
Implemented / technical runtime fix.

## Problem
ML38.10.17 runtime failed for lv25 candidates during `build_labels` with PostgreSQL error:

```text
psycopg.errors.StringDataRightTruncation: value too long for type character varying(50)
```

The failing values were lv25 `label_version` strings longer than the current `ml_labels.label_version VARCHAR(50)` database limit.

## Fix
Kept long `config_id` values for readable experiment reports and runtime shortlists, but shortened only the DB-facing `label_version` values:

- `lv25_h08_tts_thr065_sqmask060_epq070_sp045_exit_mit` -> `lv25_h08_tts_epq70_sp45_xmit`
- `lv25_h12_tts_thr065_sqmask060_epq070_sp045_exit_mit` -> `lv25_h12_tts_epq70_sp45_xmit`
- `lv25_h12_tts_thr065_sqmask060_epq072_sp043_exit_mit_strict` -> `lv25_h12_tts_epq72_sp43_xmit_strict`

## Safety
- live trading: disabled
- orders: disabled
- traders-core integration: disabled
- model auto-activation: disabled
- research-only configs: yes

## Validation expectation
- all label versions are <= 50 chars
- `--fast-debug`: expected_candidate_count = 10, failed_candidate_count = 0
- `--quick-quality --quick-quality-symbol SOLUSDT`: expected_candidate_count = 9, failed_candidate_count = 0
