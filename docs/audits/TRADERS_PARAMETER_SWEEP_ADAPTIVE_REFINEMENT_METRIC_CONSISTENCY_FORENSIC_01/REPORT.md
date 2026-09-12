# Adaptive Refinement Metric Consistency Forensic

This is a read-only reconstruction from the accepted DOGEUSDT artifacts. No
expanded-search or adaptive evaluation was executed, and no result was changed.

## Metric consistency

`net_pnl` and `profit_factor` use the same per-config validation population:
persisted causal CLOSED PAPER trades admitted by that config. Their values are
the persisted net realized PnL after entry and exit fees. Net PnL is the signed
sum. Profit factor divides the positive sum by the absolute negative sum only
when a loss exists; otherwise it is unavailable (`null`).

The best-Net-PnL config has one win of `1.01784916` and zero losses. Its PF is
therefore unavailable, not greater than one. The separately reported PF leader
is selected among configs with a non-null PF and has one win versus two losses:
`1.01784916 / 1.06746858 = 0.9535167395746674`. The verdict is
`CONSISTENT_PF_MISSING_FOR_POSITIVE_CONFIG`; there is no population, split,
accounting, or reporting mismatch.

All three positive behavioral representatives have one win, zero losses, Net
PnL `1.01784916`, and unavailable PF. Their canonical ranks are 4, 5, and 6;
none is validation eligible.

## Boundary expansion

The sole boundary expansion was `min_net_edge_bps`, HIGH, from `82.589044`.
It reused adjacent value `73.004386`, derived spacing `9.584658`, and produced
`92.173702` without schema clipping. The candidate was generated in round 1
from positive parent cluster `f3bd818...` under `BOUNDARY_PRESSURE_HIGH` and
`WEAKLY_ACTIVE` evidence.

Evaluation produced new behavioral signature `93a3aa1...`, but it admitted no
validation trades: Net PnL `0`, PF unavailable, `INSUFFICIENT_SAMPLE`. It was
not positive and did not improve the best Net PnL. Provenance verdict: `PASS`.
