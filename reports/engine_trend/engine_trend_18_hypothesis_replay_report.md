# ENGINE-TREND-18 — Post-refactor hypothesis replay

The same fixed 60 validation rows were replayed read-only. Reference labels remain descriptive rather than ground truth.

## Critical answers

1. UNKNOWN: **45 / 60**. Causes: `{'NO_HYPOTHESES': 17, 'PENDING_PLUS_CONFLICTED_NO_CONFIRMED': 21, 'ONLY_PENDING_NO_CONFIRMED': 7}`.
2. The cause split above distinguishes no hypotheses, pending-only, terminal/conflicted-only, and confirmed hypotheses blocked by composer fallback.
3. Regimes: `{'UNKNOWN': 45, 'FLAT': 12, 'UP': 3}`. UP: `['btcusdt_15m_mixed_003', 'solusdt_15m_up_002', 'solusdt_15m_up_003']`; DOWN: `[]`; FLAT: `['eth_15m_expected_flat_001', 'sol_15m_expected_flat_001', 'btcusdt_15m_up_002', 'btcusdt_15m_down_002', 'btcusdt_15m_flat_003', 'solusdt_15m_flat_001', 'solusdt_15m_flat_002', 'solusdt_15m_flat_003', 'ethusdt_15m_flat_001', 'ethusdt_15m_up_002', 'ethusdt_15m_flat_002', 'ethusdt_15m_flat_003']`.
4. MISMATCH: **0**; windows: `[]`.
5. Trap hypotheses by lifecycle: `{'BULL_TRAP:CONFIRMED': 1, 'BEAR_TRAP:CONFIRMED': 1}`.
6. Candle contextual-event statuses: `{'CONTEXT_REJECTED': 3321, 'CANDIDATE': 97, 'INVALIDATED': 56, 'AWAITING_CONFIRMATION': 5, 'CONFIRMED': 5}`. Reversal hypotheses: `{'PENDING': 5, 'CONFIRMED': 3}`.
7. FLAT selected hypothesis sources: `{'CONFIRMED_RANGE': 12}`; 12/12 FLAT results contain a CONFIRMED_RANGE, and 0 do not.

## Lifecycle contract observation

The requested `CANCELLED` status does not exist in the refactored enum. The engine emits `CONFLICTED`; reports retain an empty CANCELLED bucket and show CONFLICTED separately so the distinction is not hidden.

## Safety

Safety violations: 0; no trading action was evaluated or connected.

## Per-window comparison

Lifecycle column is confirmed/pending/invalidated/cancelled, followed by conflicted.

| Window | Reference | Old | New | Confidence | Comparison | Lifecycle | Selected hypothesis |
|---|---|---|---|---:|---|---|---|
| [btc_15m_expected_up_001](hypothesis_replay/markdown/btc_15m_expected_up_001.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [btc_15m_expected_down_001](hypothesis_replay/markdown/btc_15m_expected_down_001.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [btc_15m_expected_flat_001](hypothesis_replay/markdown/btc_15m_expected_flat_001.md) | EXPECTED_FLAT | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [btc_15m_expected_unknown_or_mixed_001](hypothesis_replay/markdown/btc_15m_expected_unknown_or_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/1/0/0 (+0 conflicted) | none |
| [btc_15m_recent_baseline_001](hypothesis_replay/markdown/btc_15m_recent_baseline_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/1/0/0 (+1 conflicted) | none |
| [eth_15m_expected_up_001](hypothesis_replay/markdown/eth_15m_expected_up_001.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [eth_15m_expected_down_001](hypothesis_replay/markdown/eth_15m_expected_down_001.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [eth_15m_expected_flat_001](hypothesis_replay/markdown/eth_15m_expected_flat_001.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.4370967741935484 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [eth_15m_expected_unknown_or_mixed_001](hypothesis_replay/markdown/eth_15m_expected_unknown_or_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+0 conflicted) | none |
| [eth_15m_recent_baseline_001](hypothesis_replay/markdown/eth_15m_recent_baseline_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/1/0/0 (+1 conflicted) | none |
| [sol_15m_expected_up_001](hypothesis_replay/markdown/sol_15m_expected_up_001.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [sol_15m_expected_down_001](hypothesis_replay/markdown/sol_15m_expected_down_001.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+0 conflicted) | none |
| [sol_15m_expected_flat_001](hypothesis_replay/markdown/sol_15m_expected_flat_001.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.6555555555555556 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [sol_15m_expected_unknown_or_mixed_001](hypothesis_replay/markdown/sol_15m_expected_unknown_or_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/1/0/0 (+1 conflicted) | none |
| [sol_15m_recent_baseline_001](hypothesis_replay/markdown/sol_15m_recent_baseline_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/1/0/0 (+1 conflicted) | none |
| [btcusdt_15m_up_001](hypothesis_replay/markdown/btcusdt_15m_up_001.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [btcusdt_15m_down_001](hypothesis_replay/markdown/btcusdt_15m_down_001.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [btcusdt_15m_flat_001](hypothesis_replay/markdown/btcusdt_15m_flat_001.md) | EXPECTED_FLAT | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [btcusdt_15m_mixed_001](hypothesis_replay/markdown/btcusdt_15m_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/1/0/0 (+0 conflicted) | none |
| [btcusdt_15m_high_volatility_chop_001](hypothesis_replay/markdown/btcusdt_15m_high_volatility_chop_001.md) | HIGH_VOLATILITY_CHOP | UNKNOWN | UNKNOWN | 0.25 | ACCEPTABLE_UNKNOWN | 0/1/0/0 (+0 conflicted) | none |
| [btcusdt_15m_up_002](hypothesis_replay/markdown/btcusdt_15m_up_002.md) | EXPECTED_UP | UNKNOWN | FLAT | 0.39137931034482765 | NEEDS_REVIEW | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [btcusdt_15m_down_002](hypothesis_replay/markdown/btcusdt_15m_down_002.md) | EXPECTED_DOWN | UNKNOWN | FLAT | 0.4614583333333334 | NEEDS_REVIEW | 2/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [btcusdt_15m_flat_002](hypothesis_replay/markdown/btcusdt_15m_flat_002.md) | EXPECTED_FLAT | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+0 conflicted) | none |
| [btcusdt_15m_mixed_002](hypothesis_replay/markdown/btcusdt_15m_mixed_002.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+0 conflicted) | none |
| [btcusdt_15m_up_003](hypothesis_replay/markdown/btcusdt_15m_up_003.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [btcusdt_15m_down_003](hypothesis_replay/markdown/btcusdt_15m_down_003.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [btcusdt_15m_flat_003](hypothesis_replay/markdown/btcusdt_15m_flat_003.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.700709219858156 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [btcusdt_15m_mixed_003](hypothesis_replay/markdown/btcusdt_15m_mixed_003.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UP | 0.6666666666666666 | NEEDS_REVIEW | 1/0/0/0 (+0 conflicted) | BULLISH_REVERSAL |
| [btcusdt_15m_up_004](hypothesis_replay/markdown/btcusdt_15m_up_004.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [btcusdt_15m_recent_baseline_001](hypothesis_replay/markdown/btcusdt_15m_recent_baseline_001.md) | RECENT_BASELINE | UNKNOWN | UNKNOWN | 0.25 | ACCEPTABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [solusdt_15m_up_001](hypothesis_replay/markdown/solusdt_15m_up_001.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [solusdt_15m_down_001](hypothesis_replay/markdown/solusdt_15m_down_001.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+0 conflicted) | none |
| [solusdt_15m_flat_001](hypothesis_replay/markdown/solusdt_15m_flat_001.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.6555555555555556 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [solusdt_15m_mixed_001](hypothesis_replay/markdown/solusdt_15m_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/1/0/0 (+1 conflicted) | none |
| [solusdt_15m_high_volatility_chop_001](hypothesis_replay/markdown/solusdt_15m_high_volatility_chop_001.md) | HIGH_VOLATILITY_CHOP | UNKNOWN | UNKNOWN | 0.25 | ACCEPTABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [solusdt_15m_up_002](hypothesis_replay/markdown/solusdt_15m_up_002.md) | EXPECTED_UP | UNKNOWN | UP | 0.6666666666666666 | MATCH | 1/0/0/0 (+0 conflicted) | BULLISH_REVERSAL |
| [solusdt_15m_down_002](hypothesis_replay/markdown/solusdt_15m_down_002.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [solusdt_15m_flat_002](hypothesis_replay/markdown/solusdt_15m_flat_002.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.7044715447154472 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [solusdt_15m_mixed_002](hypothesis_replay/markdown/solusdt_15m_mixed_002.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+0 conflicted) | none |
| [solusdt_15m_up_003](hypothesis_replay/markdown/solusdt_15m_up_003.md) | EXPECTED_UP | UNKNOWN | UP | 0.6666666666666666 | MATCH | 1/0/0/0 (+0 conflicted) | BULLISH_REVERSAL |
| [solusdt_15m_down_003](hypothesis_replay/markdown/solusdt_15m_down_003.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [solusdt_15m_flat_003](hypothesis_replay/markdown/solusdt_15m_flat_003.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.6262411347517731 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [solusdt_15m_mixed_003](hypothesis_replay/markdown/solusdt_15m_mixed_003.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/1/0/0 (+0 conflicted) | none |
| [solusdt_15m_up_004](hypothesis_replay/markdown/solusdt_15m_up_004.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [solusdt_15m_recent_baseline_001](hypothesis_replay/markdown/solusdt_15m_recent_baseline_001.md) | RECENT_BASELINE | UNKNOWN | UNKNOWN | 0.25 | ACCEPTABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [ethusdt_15m_up_001](hypothesis_replay/markdown/ethusdt_15m_up_001.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [ethusdt_15m_down_001](hypothesis_replay/markdown/ethusdt_15m_down_001.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [ethusdt_15m_flat_001](hypothesis_replay/markdown/ethusdt_15m_flat_001.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.4370967741935484 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [ethusdt_15m_mixed_001](hypothesis_replay/markdown/ethusdt_15m_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+0 conflicted) | none |
| [ethusdt_15m_high_volatility_chop_001](hypothesis_replay/markdown/ethusdt_15m_high_volatility_chop_001.md) | HIGH_VOLATILITY_CHOP | UNKNOWN | UNKNOWN | 0.25 | ACCEPTABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [ethusdt_15m_up_002](hypothesis_replay/markdown/ethusdt_15m_up_002.md) | EXPECTED_UP | UNKNOWN | FLAT | 0.4650000000000001 | NEEDS_REVIEW | 2/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [ethusdt_15m_down_002](hypothesis_replay/markdown/ethusdt_15m_down_002.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [ethusdt_15m_flat_002](hypothesis_replay/markdown/ethusdt_15m_flat_002.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.7166666666666667 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [ethusdt_15m_mixed_002](hypothesis_replay/markdown/ethusdt_15m_mixed_002.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/1/0/0 (+1 conflicted) | none |
| [ethusdt_15m_up_003](hypothesis_replay/markdown/ethusdt_15m_up_003.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [ethusdt_15m_down_003](hypothesis_replay/markdown/ethusdt_15m_down_003.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
| [ethusdt_15m_flat_003](hypothesis_replay/markdown/ethusdt_15m_flat_003.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.7077380952380953 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [ethusdt_15m_mixed_003](hypothesis_replay/markdown/ethusdt_15m_mixed_003.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+0 conflicted) | none |
| [ethusdt_15m_up_004](hypothesis_replay/markdown/ethusdt_15m_up_004.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [ethusdt_15m_recent_baseline_001](hypothesis_replay/markdown/ethusdt_15m_recent_baseline_001.md) | RECENT_BASELINE | UNKNOWN | UNKNOWN | 0.25 | ACCEPTABLE_UNKNOWN | 0/1/0/0 (+1 conflicted) | none |
