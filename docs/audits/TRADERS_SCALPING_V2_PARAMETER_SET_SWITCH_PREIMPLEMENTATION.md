# Scalping v2 parameter-set switch preimplementation audit

```text
PROFILE = trade-5m-v2
BASELINE_SOURCE = config/trading/trade_parameters.yaml/profiles/trade-5m-v2
CURRENT_PROFILE_VERSION = scalping-v2-baseline-1
SET_1_SEMANTIC_HASH_BEFORE = 074244034d0969cafdfa779013819eeaeeb710d4e29aa17fc3010c7f87315b1f
ACTIVE_PARAMETER_SOURCE_BEFORE = one validated server-owned YAML profile
ACTIVE_PARAMETER_RESOLUTION_PATH_BEFORE = YAML -> TradeParameters -> SCALPING_V2 -> TradeSearchProfile -> RuntimeProfileParameters -> PipelineRunner
```

The baseline effective values were `minimum_planned_rr=0.4`,
`risk_per_trade_bps=10`, `target_min_bps=45`, `min_ev_reserve_r=0`,
`soft/hard timeout=600/900`, `extension_seconds=300`, and
`max_extensions=1`. Costs were dynamic Binance account commission plus the
current public spread model, fixed `2 bps` entry/exit slippage, and conservative
`3 bps` adverse-fill reserve. Operational configuration was one new command per
cycle, two profile-level concurrent positions, and `50 bps` total open risk;
the separately enforced continuous PAPER control remained authoritative for
its tighter runtime bounds.

Runtime-active families were signal windows, geometry/RR, risk sizing,
cost/economics, portfolio, and PAPER lifecycle. The 1m entry refinement and
stale-position time stop were both `SHADOW`. Commission was owned by the
authenticated Binance account-commission snapshot; spread/depth by the public
market adapter; configured fee values remained fail-closed conservative inputs.

Existing pipeline JSON already carried the old derived
`runtime_parameter_set_id`, and command/position lineage could be joined back
to the pipeline run. It did not provide a stable named-set label, independent
resolved semantic hash, activation cutoff, or immutable opportunity-level set
attribution. Readonly funnel exposed only the whole-file config hash. Desktop
was a read-only consumer and had no selector authority.

Implementation constraints established by this audit:

- retain the baseline profile as the semantic source for Set #1;
- add Set #2 only as named inheritance plus explicit overrides;
- keep the YAML PAPER selector as the sole authority;
- fail closed for unknown/invalid sets;
- freeze one immutable resolution per cycle and retain historical attribution;
- do not change LIVE, 15m, Scalping v1, cost authority, or mode switches.
