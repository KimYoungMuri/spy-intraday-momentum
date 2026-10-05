# Strategy decision — VQM long-only (complementarity framing)

**Evaluation window (design):** 2023-07-03 → 2025-12-31  
**Data label:** BIASED exploratory Yahoo / current-constituent panel  
**2026 slice:** previously examined — not untouched validation  
**Product:** stock-level long-only VQM throughout (not an ETF substitute)

## One-paragraph verdict

**KEEP VQM; simplify the fee / deployability claim.** The investment hypothesis is complementarity: combining valuation, profitability, and momentum may reduce dependence on any single selection criterion. Literature (e.g., *Value and Momentum Everywhere*) motivates investigating combinations beyond the recent sample winner; it does not validate this formula. In the reported sample, VQM had lower observed volatility and max drawdown than momentum-only, with lower return and Sharpe; vs universe-cap, higher return with higher risk and only a modest Sharpe lift. Holdings and active residuals differ across sleeves (Mom–Value active corr ≈ 0.01; VQM–Mom weight overlap ≈ 60%). That is enough to keep studying VQM — not enough to claim readiness to deploy or that 75 bps is justified.

## Decision code

**KEEP PRODUCT / SIMPLIFY FEE CLAIM**

## Concise comparison (design window, after ~5 bps/side)

| Strategy | CAGR | Vol | Sharpe | Max DD | Notes |
|---|---|---|---|---|---|
| VQM | 26.71% | 18.04% | 1.13 | −22.87% | Composite |
| Momentum-only | 35.64% | 21.18% | 1.32 | −26.36% | Same sector rules |
| Universe cap | 22.54% | 15.39% | 1.08 | −19.49% | Eligible universe |
| SPY | 20.40% | 15.51% | 0.96 | −18.76% | Benchmark |
| VQM after 75 bps fee | 25.77% | 18.04% | 1.09 | −22.94% | Fee once in pitch |

## Complementarity evidence (new)

| Check | Result |
|---|---|
| VQM vs Mom name Jaccard | 42.3% |
| VQM vs Mom weight overlap | 59.7% |
| Mom vs Value weight overlap | 9.9% |
| Value vs Quality weight overlap | 1.1% |
| VQM avg ranks (V / profitability / M) | 0.50 / 0.64 / 0.80 |
| Active corr Value–Mom | ≈ 0.01 |
| Active corr VQM–Mom | ≈ 0.74 |

Sources: `holdings_overlap_summary.csv`, `portfolio_signal_exposures_avg.csv`, `sleeve_active_return_corr.csv`, figures under `outputs/figures/`.

## What the evidence says

- Three labels ≠ automatic independence; overlap/exposure/active-corr tests are the right checks.
- Single sleeves differ materially; the composite still leans on momentum in this window.
- “Quality” here is a **profitability proxy**, not comprehensive financial strength.
- Equal-weight composite balances overall scores — not a three-hurdle filter.
- Lower vol/DD vs momentum is an **observed sample feature**, not an isolated momentum-crash result.
- A rationale for VQM does **not** automatically justify 75 bps.

## Paid management / ask

Illustrative **$10mm** for the **stock mandate**, **conditional** on PIT validation. Do not pitch an ETF sleeve as the product.

## Operational feasibility @ $10mm

Position/ADV median 0.026%, max 5.59%. Rebalance trade/ADV median 0.001%, max 5.59%. Plausible, not proven.

## Continue / simplify / reject

**Keep researching / pitching VQM** as criteria diversification under uncertainty. **Simplify** any claim that the fee is earned or that the book is ready to deploy.

## Minimum next step that could change the decision

Licensed PIT data; rebuild; re-run A–F **and** overlap/exposure/active-corr tests unchanged.
