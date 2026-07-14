# ENGINE-TREND-24 Main Entry Post-mortem

- candidate: ET-HED-0001
- old score: 85.1778
- score_v2: 54.8 (rank 317/449)
- filter_v1: FAIL
- fail reasons: TOO_TIGHT_STOP, WEAK_CONFIRMATION_VOLUME
- would v2 still select it as global maximum: NO
- pre-entry warnings: TOO_TIGHT_STOP, WEAK_CONFIRMATION_VOLUME

The old RR=5.585654 receives no automatic maximum bonus. Its volume ratio is 0.6785, stop distance is 0.6756 ATR, and target distance is 3.7737 ATR. Rules must not be changed because of this single case: **NO rule change**.
