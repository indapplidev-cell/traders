# Block 07 — dynamic Net RR and conservative EV

```text
TASK_STATUS = PASS
FORMULA = EV_R=p_win_conservative*candidate_net_rr-(1-p_win_conservative)
DYNAMIC_REQUIRED_NET_RR = max(break_even_rr+min_ev_reserve,(1-p+min_positive_ev)/p)
SIMULTANEOUS_GATES = dynamic_net_rr,positive_ev,ev_reserve,min_net_edge_after_costs
NEGATIVE_CONSERVATIVE_EV_PASS = IMPOSSIBLE
THRESHOLD_SOURCE = config/trading/trade_parameters.yaml
LIVE = DISABLED
BINANCE_ORDER_API_CALLS = 0
```
