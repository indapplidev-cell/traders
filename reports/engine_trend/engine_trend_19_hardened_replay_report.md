# ENGINE-TREND-19 — Hypothesis replay

The same fixed 60 validation rows were replayed read-only. Reference labels remain descriptive rather than ground truth.

## Critical answers

1. UNKNOWN: **22 / 60**. Causes: `{'NO_HYPOTHESES': 9, 'NO_CONFIRMED_WITH_TERMINAL_OR_CONFLICTED': 7, 'CONFIRMED_BUT_COMPOSER_FALLBACK': 2, 'ONLY_PENDING_NO_CONFIRMED': 4}`.
2. The cause split above distinguishes no hypotheses, pending-only, terminal/conflicted-only, and confirmed hypotheses blocked by composer fallback.
3. Regimes: `{'UP': 18, 'FLAT': 10, 'UNKNOWN': 22, 'DOWN': 10}`. UP: `['btc_15m_expected_up_001', 'eth_15m_expected_up_001', 'eth_15m_expected_unknown_or_mixed_001', 'sol_15m_expected_up_001', 'sol_15m_expected_flat_001', 'sol_15m_recent_baseline_001', 'btcusdt_15m_up_001', 'btcusdt_15m_high_volatility_chop_001', 'btcusdt_15m_flat_003', 'btcusdt_15m_up_004', 'solusdt_15m_up_001', 'solusdt_15m_flat_001', 'solusdt_15m_up_002', 'solusdt_15m_up_004', 'solusdt_15m_recent_baseline_001', 'ethusdt_15m_up_001', 'ethusdt_15m_mixed_001', 'ethusdt_15m_mixed_003']`; DOWN: `['btc_15m_expected_unknown_or_mixed_001', 'sol_15m_expected_down_001', 'sol_15m_expected_unknown_or_mixed_001', 'btcusdt_15m_mixed_001', 'solusdt_15m_down_001', 'solusdt_15m_mixed_001', 'solusdt_15m_down_002', 'solusdt_15m_down_003', 'ethusdt_15m_down_002', 'ethusdt_15m_down_003']`; FLAT: `['btc_15m_expected_down_001', 'eth_15m_expected_flat_001', 'btcusdt_15m_down_001', 'btcusdt_15m_down_002', 'solusdt_15m_high_volatility_chop_001', 'solusdt_15m_flat_002', 'solusdt_15m_mixed_003', 'ethusdt_15m_flat_001', 'ethusdt_15m_flat_002', 'ethusdt_15m_flat_003']`.
4. MISMATCH: **3**; windows: `['sol_15m_expected_flat_001', 'btcusdt_15m_flat_003', 'solusdt_15m_flat_001']`.
5. Trap hypotheses by lifecycle: `{'BULL_TRAP:INVALIDATED': 1, 'BEAR_TRAP:INVALIDATED': 1}`.
6. Candle contextual-event statuses: `{'INVALIDATED': 50, 'CANDIDATE': 74, 'CONTEXT_REJECTED': 764, 'CONFIRMED': 12, 'AWAITING_CONFIRMATION': 10}`. Reversal hypotheses: `{'PENDING': 7, 'CONFIRMED': 1}`.
7. FLAT selected hypothesis sources: `{'CONFIRMED_RANGE': 10}`; 10/10 FLAT results contain a CONFIRMED_RANGE, and 0 do not.

## Lifecycle contract observation

The requested `CANCELLED` status does not exist in the refactored enum. The engine emits `CONFLICTED`; reports retain an empty CANCELLED bucket and show CONFLICTED separately so the distinction is not hidden.

## Safety

Safety violations: 0; no trading action was evaluated or connected.

## Per-window comparison

Lifecycle column is confirmed/pending/invalidated/cancelled, followed by conflicted.

| Window | Reference | Old | New | Confidence | Comparison | Lifecycle | Selected hypothesis |
|---|---|---|---|---:|---|---|---|
| [btc_15m_expected_up_001](replay/markdown/btc_15m_expected_up_001.md) | EXPECTED_UP | UNKNOWN | UP | 0.7086685438685385 | MATCH | 1/0/0/0 (+1 conflicted) | UP_CONTINUATION |
| [btc_15m_expected_down_001](replay/markdown/btc_15m_expected_down_001.md) | EXPECTED_DOWN | UNKNOWN | FLAT | 0.49696969696969695 | NEEDS_REVIEW | 2/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [btc_15m_expected_flat_001](replay/markdown/btc_15m_expected_flat_001.md) | EXPECTED_FLAT | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [btc_15m_expected_unknown_or_mixed_001](replay/markdown/btc_15m_expected_unknown_or_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | DOWN | 0.050000000000000044 | NEEDS_REVIEW | 1/0/0/0 (+1 conflicted) | DOWN_CONTINUATION |
| [btc_15m_recent_baseline_001](replay/markdown/btc_15m_recent_baseline_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+1 conflicted) | none |
| [eth_15m_expected_up_001](replay/markdown/eth_15m_expected_up_001.md) | EXPECTED_UP | UNKNOWN | UP | 0.9011017608701286 | MATCH | 1/1/0/0 (+0 conflicted) | UP_CONTINUATION |
| [eth_15m_expected_down_001](replay/markdown/eth_15m_expected_down_001.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.0 | QUESTIONABLE_UNKNOWN | 1/0/0/0 (+1 conflicted) | none |
| [eth_15m_expected_flat_001](replay/markdown/eth_15m_expected_flat_001.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.4254901960784314 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [eth_15m_expected_unknown_or_mixed_001](replay/markdown/eth_15m_expected_unknown_or_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UP | 0.8480426724888609 | NEEDS_REVIEW | 1/0/0/0 (+1 conflicted) | UP_CONTINUATION |
| [eth_15m_recent_baseline_001](replay/markdown/eth_15m_recent_baseline_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+1 conflicted) | none |
| [sol_15m_expected_up_001](replay/markdown/sol_15m_expected_up_001.md) | EXPECTED_UP | UNKNOWN | UP | 0.050000000000000044 | MATCH | 1/0/0/0 (+1 conflicted) | UP_CONTINUATION |
| [sol_15m_expected_down_001](replay/markdown/sol_15m_expected_down_001.md) | EXPECTED_DOWN | UNKNOWN | DOWN | 0.9126369399914006 | MATCH | 1/0/0/0 (+1 conflicted) | DOWN_CONTINUATION |
| [sol_15m_expected_flat_001](replay/markdown/sol_15m_expected_flat_001.md) | EXPECTED_FLAT | UNKNOWN | UP | 0.2542242573755541 | MISMATCH | 1/1/0/0 (+0 conflicted) | UP_CONTINUATION |
| [sol_15m_expected_unknown_or_mixed_001](replay/markdown/sol_15m_expected_unknown_or_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | DOWN | 0.3666666666666667 | NEEDS_REVIEW | 1/0/0/0 (+0 conflicted) | DOWN_CONTINUATION |
| [sol_15m_recent_baseline_001](replay/markdown/sol_15m_recent_baseline_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UP | 0.7997951421353985 | NEEDS_REVIEW | 1/0/0/0 (+1 conflicted) | UP_CONTINUATION |
| [btcusdt_15m_up_001](replay/markdown/btcusdt_15m_up_001.md) | EXPECTED_UP | UNKNOWN | UP | 0.7086685438685385 | MATCH | 1/0/0/0 (+1 conflicted) | UP_CONTINUATION |
| [btcusdt_15m_down_001](replay/markdown/btcusdt_15m_down_001.md) | EXPECTED_DOWN | UNKNOWN | FLAT | 0.49696969696969695 | NEEDS_REVIEW | 2/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [btcusdt_15m_flat_001](replay/markdown/btcusdt_15m_flat_001.md) | EXPECTED_FLAT | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [btcusdt_15m_mixed_001](replay/markdown/btcusdt_15m_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | DOWN | 0.050000000000000044 | NEEDS_REVIEW | 1/0/0/0 (+1 conflicted) | DOWN_CONTINUATION |
| [btcusdt_15m_high_volatility_chop_001](replay/markdown/btcusdt_15m_high_volatility_chop_001.md) | HIGH_VOLATILITY_CHOP | UNKNOWN | UP | 0.3666666666666667 | NEEDS_REVIEW | 1/0/0/0 (+0 conflicted) | UP_CONTINUATION |
| [btcusdt_15m_up_002](replay/markdown/btcusdt_15m_up_002.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+1 conflicted) | none |
| [btcusdt_15m_down_002](replay/markdown/btcusdt_15m_down_002.md) | EXPECTED_DOWN | UNKNOWN | FLAT | 0.457608695652174 | NEEDS_REVIEW | 2/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [btcusdt_15m_flat_002](replay/markdown/btcusdt_15m_flat_002.md) | EXPECTED_FLAT | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/2/0/0 (+0 conflicted) | none |
| [btcusdt_15m_mixed_002](replay/markdown/btcusdt_15m_mixed_002.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+0 conflicted) | none |
| [btcusdt_15m_up_003](replay/markdown/btcusdt_15m_up_003.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/0/0 (+0 conflicted) | none |
| [btcusdt_15m_down_003](replay/markdown/btcusdt_15m_down_003.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [btcusdt_15m_flat_003](replay/markdown/btcusdt_15m_flat_003.md) | EXPECTED_FLAT | UNKNOWN | UP | 0.7166666666666667 | MISMATCH | 1/0/1/0 (+0 conflicted) | BULLISH_REVERSAL |
| [btcusdt_15m_mixed_003](replay/markdown/btcusdt_15m_mixed_003.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+0 conflicted) | none |
| [btcusdt_15m_up_004](replay/markdown/btcusdt_15m_up_004.md) | EXPECTED_UP | UNKNOWN | UP | 0.9176042707061757 | MATCH | 1/1/0/0 (+1 conflicted) | UP_CONTINUATION |
| [btcusdt_15m_recent_baseline_001](replay/markdown/btcusdt_15m_recent_baseline_001.md) | RECENT_BASELINE | UNKNOWN | UNKNOWN | 0.25 | ACCEPTABLE_UNKNOWN | 0/0/0/0 (+1 conflicted) | none |
| [solusdt_15m_up_001](replay/markdown/solusdt_15m_up_001.md) | EXPECTED_UP | UNKNOWN | UP | 0.050000000000000044 | MATCH | 1/0/0/0 (+1 conflicted) | UP_CONTINUATION |
| [solusdt_15m_down_001](replay/markdown/solusdt_15m_down_001.md) | EXPECTED_DOWN | UNKNOWN | DOWN | 0.9126369399914006 | MATCH | 1/0/0/0 (+1 conflicted) | DOWN_CONTINUATION |
| [solusdt_15m_flat_001](replay/markdown/solusdt_15m_flat_001.md) | EXPECTED_FLAT | UNKNOWN | UP | 0.2542242573755541 | MISMATCH | 1/1/0/0 (+0 conflicted) | UP_CONTINUATION |
| [solusdt_15m_mixed_001](replay/markdown/solusdt_15m_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | DOWN | 0.3666666666666667 | NEEDS_REVIEW | 1/0/0/0 (+0 conflicted) | DOWN_CONTINUATION |
| [solusdt_15m_high_volatility_chop_001](replay/markdown/solusdt_15m_high_volatility_chop_001.md) | HIGH_VOLATILITY_CHOP | UNKNOWN | FLAT | 0.45833333333333337 | NEEDS_REVIEW | 1/0/1/0 (+0 conflicted) | CONFIRMED_RANGE |
| [solusdt_15m_up_002](replay/markdown/solusdt_15m_up_002.md) | EXPECTED_UP | UNKNOWN | UP | 0.5166666666666667 | MATCH | 1/0/0/0 (+1 conflicted) | UP_CONTINUATION |
| [solusdt_15m_down_002](replay/markdown/solusdt_15m_down_002.md) | EXPECTED_DOWN | UNKNOWN | DOWN | 0.5166666666666667 | MATCH | 1/0/0/0 (+1 conflicted) | DOWN_CONTINUATION |
| [solusdt_15m_flat_002](replay/markdown/solusdt_15m_flat_002.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.6983739837398374 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [solusdt_15m_mixed_002](replay/markdown/solusdt_15m_mixed_002.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+1 conflicted) | none |
| [solusdt_15m_up_003](replay/markdown/solusdt_15m_up_003.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [solusdt_15m_down_003](replay/markdown/solusdt_15m_down_003.md) | EXPECTED_DOWN | UNKNOWN | DOWN | 0.8665197001104326 | MATCH | 1/0/0/0 (+0 conflicted) | DOWN_CONTINUATION |
| [solusdt_15m_flat_003](replay/markdown/solusdt_15m_flat_003.md) | EXPECTED_FLAT | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [solusdt_15m_mixed_003](replay/markdown/solusdt_15m_mixed_003.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | FLAT | 0.4636904761904762 | NEEDS_REVIEW | 1/0/1/0 (+0 conflicted) | CONFIRMED_RANGE |
| [solusdt_15m_up_004](replay/markdown/solusdt_15m_up_004.md) | EXPECTED_UP | UNKNOWN | UP | 0.8918672957453899 | MATCH | 1/0/0/0 (+0 conflicted) | UP_CONTINUATION |
| [solusdt_15m_recent_baseline_001](replay/markdown/solusdt_15m_recent_baseline_001.md) | RECENT_BASELINE | UNKNOWN | UP | 0.7997951421353985 | NEEDS_REVIEW | 1/0/0/0 (+1 conflicted) | UP_CONTINUATION |
| [ethusdt_15m_up_001](replay/markdown/ethusdt_15m_up_001.md) | EXPECTED_UP | UNKNOWN | UP | 0.9011017608701286 | MATCH | 1/1/0/0 (+0 conflicted) | UP_CONTINUATION |
| [ethusdt_15m_down_001](replay/markdown/ethusdt_15m_down_001.md) | EXPECTED_DOWN | UNKNOWN | UNKNOWN | 0.0 | QUESTIONABLE_UNKNOWN | 1/0/0/0 (+1 conflicted) | none |
| [ethusdt_15m_flat_001](replay/markdown/ethusdt_15m_flat_001.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.4254901960784314 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [ethusdt_15m_mixed_001](replay/markdown/ethusdt_15m_mixed_001.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UP | 0.8480426724888609 | NEEDS_REVIEW | 1/0/0/0 (+1 conflicted) | UP_CONTINUATION |
| [ethusdt_15m_high_volatility_chop_001](replay/markdown/ethusdt_15m_high_volatility_chop_001.md) | HIGH_VOLATILITY_CHOP | UNKNOWN | UNKNOWN | 0.25 | ACCEPTABLE_UNKNOWN | 0/0/0/0 (+0 conflicted) | none |
| [ethusdt_15m_up_002](replay/markdown/ethusdt_15m_up_002.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/2/1/0 (+0 conflicted) | none |
| [ethusdt_15m_down_002](replay/markdown/ethusdt_15m_down_002.md) | EXPECTED_DOWN | UNKNOWN | DOWN | 0.3666666666666667 | MATCH | 1/0/0/0 (+0 conflicted) | DOWN_CONTINUATION |
| [ethusdt_15m_flat_002](replay/markdown/ethusdt_15m_flat_002.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.7082397003745319 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [ethusdt_15m_mixed_002](replay/markdown/ethusdt_15m_mixed_002.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UNKNOWN | 0.25 | MATCH | 0/0/0/0 (+0 conflicted) | none |
| [ethusdt_15m_up_003](replay/markdown/ethusdt_15m_up_003.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/0/0/0 (+1 conflicted) | none |
| [ethusdt_15m_down_003](replay/markdown/ethusdt_15m_down_003.md) | EXPECTED_DOWN | UNKNOWN | DOWN | 0.927223357717916 | MATCH | 1/1/0/0 (+1 conflicted) | DOWN_CONTINUATION |
| [ethusdt_15m_flat_003](replay/markdown/ethusdt_15m_flat_003.md) | EXPECTED_FLAT | UNKNOWN | FLAT | 0.7021317829457364 | MATCH | 1/0/0/0 (+0 conflicted) | CONFIRMED_RANGE |
| [ethusdt_15m_mixed_003](replay/markdown/ethusdt_15m_mixed_003.md) | EXPECTED_UNKNOWN_OR_MIXED | UNKNOWN | UP | 0.3666666666666667 | NEEDS_REVIEW | 1/0/0/0 (+0 conflicted) | UP_CONTINUATION |
| [ethusdt_15m_up_004](replay/markdown/ethusdt_15m_up_004.md) | EXPECTED_UP | UNKNOWN | UNKNOWN | 0.25 | QUESTIONABLE_UNKNOWN | 0/1/1/0 (+0 conflicted) | none |
| [ethusdt_15m_recent_baseline_001](replay/markdown/ethusdt_15m_recent_baseline_001.md) | RECENT_BASELINE | UNKNOWN | UNKNOWN | 0.25 | ACCEPTABLE_UNKNOWN | 0/0/0/0 (+1 conflicted) | none |
