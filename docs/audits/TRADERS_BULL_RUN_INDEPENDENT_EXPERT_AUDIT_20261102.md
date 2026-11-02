# Independent expert audit of October 2026 bull runs

## Verdict

`PASS_EVENT_CONDITIONED_RESEARCH`

The independent causal rubric produced one shared calibration which completed a
net-positive trade of at least `+8 bps` on 100 of 140 labelled October bull
runs. Coverage is `71.43%`, above the required `60%`. The median successful net
return is `+20.5196 bps`; mean successful net return is `+23.0690 bps`.

This is a retrospective, event-conditioned module audit. It proves that the
recommended interpretation and weights can express profitable entries and
exits on the labelled bull-run cohort. It is not a whole-market strategy result
and is not eligible for PAPER or LIVE activation without a separate negative-
window qualification.

## Independent analysis contract

- Labels may inspect future candles; entry and exit verdicts may not.
- Every entry signal uses closed 1m/5m OHLCV and fills at the next 1m open.
- Every analytical exit uses only candles closed at its decision boundary and
  fills at the next 1m open.
- The evaluator calculates EMA 9/21, SMA 20/50, MACD 12/26/9, RSI 14, ATR 14,
  ADX 14, Bollinger 20/2, rolling VWAP and volume expansion directly from OHLCV.
  Project direction and final scores are comparison evidence only.
- Graphical entry evidence is weighted 35% structure, 25% breakout/retest, 15%
  candle confirmation, 15% multi-timeframe agreement and 10% invalidation
  quality. Technical evidence is weighted 25% moving averages, 15% MACD, 10%
  RSI, 15% ADX, 15% VWAP, 10% volume and 10% ATR/Bollinger.
- Fees are 10 bps per side. Persisted causal spread, slippage and adverse-fill
  reserve are charged separately. The ledger invariant is enforced by contract.

## Recommended shared values

```yaml
active: false
authority: RESEARCH_ONLY_NOT_ACTIVATED
calibration_id: 4f3a271ee444814506ea6e67992798d37208a3c79e7f8801fdde40a9bf937e57
regime: ALL
entry_weights:
  structure: 8
  context: 22
  momentum: 14
  volume: 2
  entry_quality: 22
  liquidity: 22
  confirmation: 10
exit_weights:
  graphical_structure: 5
  technical_indicators: 11
  momentum_volume: 43
  holding_economics: 41
thresholds:
  entry: 50
  at_risk: 40
  exit: 60
  strong_reversal: 75
minimum_net_profit_bps: 8
profit_lock_buffer_bps: 8
```

The 8 bps profit-lock buffer waits for a causally observed `+16 bps` estimated
net cushion so that the following-open fill can remain at least `+8 bps` after
adverse movement.

## Results

| Measure | Result |
|---|---:|
| Labelled bull runs | 140 |
| Successful trades | 100 |
| Failed or missed events | 40 |
| Coverage | 71.43% |
| Median successful net return | +20.5196 bps |
| Mean successful net return | +23.0690 bps |
| Mean captured net excursion | 65.46% |
| Successful gross return, sum | 5,215.1694 bps |
| Fees, sum | 2,000.0000 bps |
| Spread/slippage/reserve, sum | 908.2659 bps |
| Successful net return, sum | 2,306.9035 bps |

Project-versus-expert discrepancies across the 140 events:

- 85 events: project confidence understated the independent bullish strength;
- 36 events: no qualifying profitable causal exit was retained;
- four events: no independent entry crossed the shared threshold;
- one event: entry was delayed by more than one 5m candle.

The project also persisted 2,240 bullish observations outside the labelled bull
runs. They are reported as false-signal context but deliberately do not reject
this event-conditioned calibration. This is the principal limitation that must
be tested before any deployment proposal.

## Reproducibility and artifacts

The complete run and a fresh verifier run were byte-identical, including all
140 event evaluations and 140 SVG charts.

- Dataset fingerprint: `37da24cf47d88e5d627b00ba8a704f5fd18490d09a0b8ed603b440cab5887845`.
- `SUMMARY.json`: `f7e371068acc121ef01c20b511481ac4bbed53c77bf1e23624690d334a6e7628`.
- `EVENT_AUDIT.jsonl`: `5c673f89ceb4f46910c6341b9f915eec3353f6233003fae253066199dd377a7d`.
- `SUCCESSFUL_TRADES.csv`: `71fc85953c7de1a85b9974ec4e73e9b7d6d7f12ae116db29248ec50f7a29764b`.
- `MODULE_CORRECTIONS.json`: `eb95ca52a156b1fd8af2f2012d5f92312cce2f4c57a1ba245b40fbb52f149c60`.
- `RECOMMENDED_MODULE_CALIBRATION.yaml`: `1b0ad99d930e79dadef2356c02013016b351a6a47f83c07075f0b4dea134a169`.
- Integrity manifest: `6802f189032eafd731526b6b8c498716dd6e10d25e4d8b9fa69dfa4a7e8c7185`.

Artifacts are under
`artifacts/bull_run_expert_audit/october_202610_20261102_final`. The inactive
YAML cannot alter runtime configuration.

## Safety and next gate

- Production database writes: 0.
- Production restarts: 0.
- PAPER/LIVE changes: 0.
- Binance order API calls: 0.

The next separate task is whole-market shadow qualification of this correction
layer, including the 2,240 outside-event observations. Until that passes, the
calibration remains research-only.
