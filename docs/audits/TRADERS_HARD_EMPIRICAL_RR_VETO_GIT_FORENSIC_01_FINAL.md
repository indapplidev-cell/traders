# Traders hard empirical RR veto Git forensic 01 — final

## Decision

```text
FINAL_STATUS = PASS_READ_ONLY_GIT_FORENSIC
ROOT_CLASSIFICATION = HARD_VETO_PREEXISTED_AND_LATER_ACTIVATED_BY_ESTABLISHED_AUTHORITY
TRADE_STOP_WAS_STATE_TRANSITION_NOT_CODE_DEPLOYMENT = YES
IMPLEMENTATION_CHANGE = NONE
DEPLOYMENT_CHANGE = NONE
DATABASE_CHANGE = NONE
LIVE_CHANGE = NONE
```

The hard negative-expectancy veto was not introduced by the exploration work
or its rollback. Git history proves that its semantic origin is
`c93693d815d3951ce40676aa21dc35435e1d34ce`, while the last production trading
revision was a descendant containing the same veto. Natural PAPER admission
continued while the authority had fewer than 20 observations. The twentieth
natural CLOSED position made that authority established; subsequent candidates
with the now-proven negative EV were terminally rejected.

## A. Current hard-veto code path

| Item | Proven path |
|---|---|
| File / function | `app/engine_paper/scalping_policy_v2.py::evaluate_expectancy` (starts at line 142) |
| Authority transition | the first hierarchy bucket with `samples >= minimum_samples`; default `minimum_samples=20` |
| Negative-EV logic | lines 219–247 compute empirical EV and require it to be non-negative as part of `admitted`; failure is `EMPIRICAL_SUFFICIENT_NEGATIVE_EV` |
| Mapping / terminal | `app/engine_paper/scalping_shadow.py` line 975 maps `not expectancy.admitted` to terminal `EXPECTANCY_GATE / SCALPING_EMPIRICAL_EXPECTANCY_REJECTED` |
| Downstream effect | RR rejected; Risk, Portfolio and PAPER-plan materialization are not reached |

The short path is: candidate reaches RR → empirical hierarchy lookup → sample
20 is sufficient → established empirical EV is negative →
`EMPIRICAL_SUFFICIENT_NEGATIVE_EV` →
`SCALPING_EMPIRICAL_EXPECTANCY_REJECTED` → terminal RR reject.

The supplied post-rollback Funnel evidence is consistent with that code path:
47 Target and Net Cost passes reached RR, all 47 were rejected, and zero PAPER
plans were produced. ENAUSDT also proves that this is an independent EV veto:
its net RR about `2.80469675` exceeded dynamic required RR about `2.75941928`
but negative empirical EV still rejected it.

## B. Introducing commit

```text
HARD_EMPIRICAL_VETO_INTRODUCING_COMMIT = c93693d815d3951ce40676aa21dc35435e1d34ce
DATE = 2026-09-02T20:15:55+03:00
SUBJECT = feat(scalping): add independent v2 policy research profile
```

This commit added `scalping_policy_v2.py::evaluate_expectancy` with all material
semantics in one change:

```text
minimum_samples = 20
if samples < 20: use static RR fallback
else: expected_value = p_win * net_win_bps - (1-p_win) * net_loss_bps
admitted = expected_value >= 0
negative result reason = EMPIRICAL_EV_REJECT
```

The same commit wired that decision into `scalping_shadow.py` and immediately
returned `SCALPING_EMPIRICAL_EXPECTANCY_REJECTED` when `admitted` was false.
Thus sufficient sample plus negative empirical expectancy became a terminal RR
veto in this commit. The current string `EMPIRICAL_SUFFICIENT_NEGATIVE_EV` is a
later clearer name for the already-existing semantic rule.

## C. Direct predecessor

```text
PRE_VETO_PREDECESSOR_COMMIT = d6f0771b3f68e34150d39a900ace7fae7c457f1a
```

The direct predecessor had no `scalping_policy_v2.py`, empirical expectancy
decision, sufficient-sample transition, or terminal empirical rejection. Its
relevant path admitted a geometrically actionable candidate on positive net
edge and static/cost-aware net RR. Therefore a hypothetical sufficient sample
with negative empirical EV was not evaluated and could not independently veto
the trade. After `c93693d…`, the same condition became a terminal RR rejection.

## D. Activation dependencies

| Semantic piece | Commit | Finding |
|---|---|---|
| required sample `20` | `c93693d815d3951ce40676aa21dc35435e1d34ce` | introduced together with the hard veto |
| sufficient-sample authority transition | `c93693d815d3951ce40676aa21dc35435e1d34ce` | implicit `samples < 20` fallback versus sufficient-sample empirical branch |
| centralized configuration | `ccbc7776e48f84e98801fa49ea50ef496b44e805` | moved authoritative parameters into server configuration; did not originate the veto |
| conservative hierarchy selection | `87355695799d378b654700d744fa55d57df55c44` | selects a sufficiently sampled hierarchy bucket; did not originate the veto |
| conservative probability | `b4f6775df78771382246b713a7337c4a8eff145b` | added conservative p-win estimation |
| dynamic RR / expanded admission conjunction | `acc43671fe8852962c56a6f1d28dbdf17a9ebe77` | added dynamic required RR and additional EV-reserve gates; negative-EV veto remained |
| average-payoff authority | `cdaf1983177319817275b22b93a7e941c3590b2d` | isolated empirical expectancy authority and payoff inputs |
| explicit authority status / bootstrap / current reason name | `55d2614c2f79c5c9f770585163cb4ecb65505714` | names `ESTABLISHED`, permits bootstrap only below threshold, and renames the sufficient negative branch to `EMPIRICAL_SUFFICIENT_NEGATIVE_EV`; it preserves rather than introduces the veto |

No multi-commit combination is required to explain the core rule: `c93693d…`
already contained sample 20, negative EV evaluation and terminal rejection.
Later commits refined probability, hierarchy, payoff and observability.

## E. Last proven PAPER-trading revision

```text
LAST_PROVEN_TRADING_SOURCE_COMMIT = 4f602eff0e6381252f224cc59955589fc13efe45
LAST_PROVEN_TRADING_RR_PASS = GREATER_THAN_ZERO; AT_LEAST_ONE_FOR_THE_CITED_FINAL_NATURAL_CYCLE
LAST_PROVEN_TRADING_PAPER_PLANS = GREATER_THAN_ZERO; AT_LEAST_ONE_FOR_THE_CITED_FINAL_NATURAL_CYCLE
HARD_VETO_PRESENT_DURING_LAST_PROVEN_TRADING_PERIOD = YES
```

`TRADERS_FULL_CYCLE_BINANCE_TO_CLOSED_PAPER_TRADE_LATENCY_REMEDIATION_01_FINAL.md`
identifies the deployed orchestrator revision as `4f602eff…` and explicitly
records that RR was unchanged. The later read-only empirical forensic records
natural `trade-5m-v2` positions under that continuing orchestrator generation,
ending with the twentieth authority position, XRPUSDT, opened at
2026-09-27 21:21 UTC and closed at 21:32 UTC. A natural linked position proves
that its cycle had both an RR pass and a PAPER plan; the exact aggregate for
that revision was not reconstructed because this task forbids a new replay.

Git proves `c93693d…` is an ancestor of `4f602eff…`; inspection of
`4f602eff…:app/engine_paper/scalping_policy_v2.py` shows both default sample 20
and `EMPIRICAL_SUFFICIENT_NEGATIVE_EV`, and its shadow path contains the same
terminal mapping. The final admitted XRP cycle began before its own close could
raise the authority from 19 to 20. After it closed, subsequent cycles saw an
established 20/7/13 authority with EV about `-18.081946` bps and self-locked.

## F. Final classification

```text
ROOT_CLASSIFICATION = HARD_VETO_PREEXISTED_AND_LATER_ACTIVATED_BY_ESTABLISHED_AUTHORITY
TRADE_STOP_WAS_STATE_TRANSITION_NOT_CODE_DEPLOYMENT = YES
```

This is decision-matrix variant B. PAPER trades passed with the hard veto
already present because the authority had not yet reached the required sample.
The transition to sample 20 activated the older sufficient-sample branch.

## G. Safe next target

Reverting exploration v1/v2 could never remove this self-lock because the
rollback restored an older baseline that already contained it. A separately
authorized policy-design task should review the surgical hard-veto lineage:
semantic origin `c93693d…`, the dynamic/conservative admission refinement
`acc43671…`, and the established-authority/bootstrap transition
`55d2614c…`. Reverting the whole `c93693d…` is not recommended because it also
introduced the independent v2 profile. No rollback or code change was made in
this task.

## Safety record

```text
ROLLBACK_OR_CODE_CHANGE_PERFORMED = NO
PRODUCTION_CONFIG_CHANGED = NO
DATABASE_MUTATED = NO
SERVICES_RESTARTED = NO
LIVE_CHANGED = NO
REAL_BINANCE_ORDER_CALLS = 0
```
