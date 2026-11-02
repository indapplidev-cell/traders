# Bull-run weight calibration results — 2026-11-02

## Final verdict

`NO_ELIGIBLE_CANDIDATE`

No tested entry/exit weight and threshold combination produced a positive,
gate-compliant result. Consequently no weight set is eligible for PAPER or LIVE
activation. The generated candidate YAML is inactive and contains no selected
configuration. This is an economic result, not a tooling failure: the complete
search and an independent deterministic verifier both finished successfully.

## Frozen data

- Period: 2026-10-01 00:00:00 UTC through 2026-11-01 00:00:00 UTC.
- Universe: all 20 `trading-universe-v3` symbols.
- Closed 5m candles: 178,560.
- Cost-authoritative LONG observations: 1,951.
- Conservative-policy LONG observations: 2,540.
- Conservative split coverage: SEARCH 2,022; VALIDATION 358; HOLDOUT 160.
- Algorithmically selected bullish events: 140.
- Dataset fingerprint: `37da24cf47d88e5d627b00ba8a704f5fd18490d09a0b8ed603b440cab5887845`.
- Candle SHA-256: `d350ca2e3d422ee31bbc43c4aa319e06552a698db4d7ae857b239137606c6a00`.
- Observation SHA-256: `2140186dab29260f6a066a03318596abc5d7f7a50c170ed9e8e16d7d061556cb`.

The conservative policy does not substitute current fees. At each persisted
historical boundary it uses the recorded public bid/ask and spread, recorded
slippage and reserve, and floors each persisted taker fee side at 10 bps.
Discounts below that cap are ignored. Missing boundaries are not backfilled.

## Search protocol

- Baseline replay was evaluated first.
- 500 unique configurations were evaluated with seed `20261001` and one TPE worker.
- Entry and exit weights were non-negative, summed to 100, and no group exceeded 45.
- Only entry score, `at_risk`, exit, and strong-reversal thresholds changed.
- Geometry, stop, target, sizing, 5 bps risk budget, costs, lifecycle, and
  two-position capacity remained frozen.
- Search/validation/holdout boundaries were chronological and non-overlapping.
- Holdout was opened after finalist freeze and replayed twice.

## Baseline economics

| Split | Trades | Net PnL, USDT | PF | Win rate | Days |
|---|---:|---:|---:|---:|---:|
| Search | 780 | -497.928595 | 0.0812 | 13.85% | 19 |
| Holdout | 50 | -33.618124 | 0.0241 | 6.00% | 3 |

The baseline lost money after the persisted 20 bps round-trip taker cap,
historical spread, slippage, and reserve. All 20 symbols were negative in search.

## Best rejected reference

The least-bad Pareto finalist is recorded only to explain the result. It is not
an eligible candidate and must not be activated.

```yaml
active: false
status: REJECTED_NEGATIVE_ECONOMICS
entry_weights:
  structure: 19
  context: 19
  momentum: 18
  volume: 9
  entry_quality: 27
  liquidity: 5
  confirmation: 3
exit_weights:
  graphical_structure: 7
  technical_indicators: 41
  momentum_volume: 37
  holding_economics: 15
thresholds:
  entry: 90
  at_risk: 60
  exit: 70
  strong_reversal: 85
configuration_hash: e5b30438b52471e263937452d37cd6456b917a1d60487864839d3c7995216023
```

| Split | Trades | Net PnL, USDT | Expectancy | PF | Win rate | Days |
|---|---:|---:|---:|---:|---:|---:|
| Search | 98 | -54.893448 | -0.560137 | 0.1625 | 21.43% | 19 |
| Validation | 18 | -7.286683 | -0.404816 | 0.1166 | 27.78% | 4 |
| Holdout | 6 | -3.298400 | -0.549733 | 0.0293 | 16.67% | 3 |

Holdout failed minimum trades, independent days, positive net PnL, positive
expectancy, PF 1.20, Win Rate above 50%, and non-negative false-entry PnL.
Although this reference reduces loss versus baseline, it does not create a
positive margin. Treating lower loss as profit would be incorrect.

## Threshold probe

An additional baseline-weight probe checked entry thresholds 90, 92, 94, 96,
98, and 99 with exit thresholds 55, 65, 75, and 85. Results remained negative:

- entry 96: 13 search trades, net -2.142670 USDT, PF 0.6139;
- entry 98: four search trades, net -0.534559 USDT, PF 0.7323;
- entry 99: no trades.

Therefore raising the entry threshold does not reveal a profitable tail.

## Independent verifier

The complete 500-configuration campaign was rerun from the same dataset and
seed. These artifacts were byte-identical:

- `SEARCH_RESULT.json`: `e69a22188a468393d2e8742a3f20aeaf1bfce451dd22eaf87671d3161a417bb6`;
- `FINALISTS.json`: `565b7cae2961a86410749aa034440a9674419663ad2b015f05fb6416e55b7b32`;
- `TRADES.csv`: `b31588c54f02b1386be0c694f45f4bc1c064e03175934f7510f374ad45fdb852`;
- `INACTIVE_CANDIDATE.yaml`: `02dd36494b6a5d4354d1f84afb66f202ba7e2638d3ed23325cddeb13c2218d2f`;
- `BULL_RUN_EVENTS.jsonl`: `e599f6f72824577a0dda91294c0719c48b8b568dbef5c4efdca675a0f1708b1f`.

## Engineering conclusion

The requested positive result cannot be obtained by changing only the seven
entry weights, four analytical-exit weights, and four score thresholds while
freezing geometry, risk, and lifecycle. Component scores do not separate
profitable LONG entries sufficiently; false entries dominate, and several
targets hit gross-positive remain net-negative after conservative costs.

The next justified research step is a separately approved change to the
signal/geometry feature space, such as an explicit minimum gross excursion above
total costs, improved negative-window discrimination, or revised target/stop
economics, followed by a new chronological calibration. Until then the only
correct candidate status is `NO_ELIGIBLE_CANDIDATE`.

## Safety

- Production database mutations: 0.
- Production service restarts: 0.
- PAPER/LIVE parameter changes: 0.
- Binance order API calls: 0.
- Candidate activation: false.
