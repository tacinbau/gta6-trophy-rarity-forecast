# Strategy

A trophy's rate is earned / tracked, so model the two counts, not the ratio.

- **Tracked** grows in log-time since release; slope fitted from the case's
  reads when they vary, else a prior of 1.0.
- **Earned** grows per trophy the same way, fitted and shrunk toward its
  tier's mean, else a prior of 0.3.
- **Staleness:** Exophase refreshes in jumps. The lag is the hours since the
  tracked count last moved. Both counts are caught up over the lag, then
  grown to the target. The earned catch-up is only a fraction of the tracked
  one, because newly synced players hold far fewer trophies; the trophy
  everyone holds stays at 100%.
- **Spread:** logit-normal quantiles, widening with horizon, extrapolation
  distance and display lag.

Local practice (reconstructed answers, local only): pinball loss 0.10–0.22
vs the persistence baseline's 1.40–1.58.
