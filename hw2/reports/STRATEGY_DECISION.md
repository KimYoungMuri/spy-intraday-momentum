# Strategy decision — VQM long-only

**Evaluation window (design):** 2023-07-03 → 2025-12-31  
**Data label:** BIASED exploratory Yahoo / current-constituent panel (not point-in-time; survivorship/membership bias remain).  
**2026 slice:** previously examined historical evaluation period — **not** untouched validation.

## One-paragraph verdict

**SIMPLIFY.** After correctness fixes, combining value and quality with momentum does not add enough (on this biased Yahoo panel) to justify the extra data and complexity versus simpler comparators. Drop the paid stock-selection claim; present an illustrative study with full disclosure, or redefine the assignment around a labelled factor-ETF allocation.

## Decision code

**SIMPLIFY**

## Concise comparison (design window)

Cost/fee layers are explicit in the `cost_fee_layer` column. Trading costs use a **proportional L1 approximation**, not exact cash-lot accounting.

| Strategy | cagr | ann_vol | sharpe | max_drawdown | total_return | beta | tracking_error | avg_turnover_one_way | cost_fee_layer |
|---|---|---|---|---|---|---|---|---|---|
| A_universe_cap | 22.54% | 15.39% | 1.08 | -19.49% | 65.95% | 0.99 | 1.57% | 2.97% | after_trading_cost_5bps |
| B_universe_sector_equal | 21.62% | 16.22% | 0.99 | -19.92% | 62.87% | 0.99 | 5.38% | 5.00% | after_trading_cost_5bps |
| C_momentum_only | 35.64% | 21.18% | 1.32 | -26.36% | 113.76% | 1.24 | 9.62% | 27.49% | after_trading_cost_5bps |
| D_value_only | 25.01% | 18.86% | 1.02 | -21.52% | 74.41% | 1.02 | 10.31% | 11.07% | after_trading_cost_5bps |
| E_quality_only | 19.36% | 15.67% | 0.90 | -19.83% | 55.43% | 0.95 | 5.33% | 7.12% | after_trading_cost_5bps |
| F_VQM_equal | 26.71% | 18.04% | 1.13 | -22.87% | 80.40% | 1.08 | 6.95% | 27.63% | after_trading_cost_5bps |
| F_VQM_gross | 27.13% | 18.04% | 1.15 | -22.82% | 81.90% | 1.08 | 6.95% | 27.63% | gross_0bps |
| F_VQM_after_fee | 25.77% | 18.04% | 1.09 | -22.94% | 77.06% | 1.08 | 6.95% | 27.63% | after_trading_cost_and_75bps_mgmt |
| C_mom_gross | 36.09% | 21.17% | 1.33 | -26.31% | 115.53% | 1.24 | 9.62% | 27.49% | gross_0bps |
| C_mom_after_fee | 34.63% | 21.18% | 1.28 | -26.44% | 109.80% | 1.24 | 9.62% | 27.49% | after_trading_cost_and_75bps_mgmt |
| A_univ_gross | 22.58% | 15.39% | 1.08 | -19.48% | 66.10% | 0.99 | 1.57% | 2.97% | gross_0bps |
| SPY | 20.40% | 15.51% | 0.96 | -18.76% | 58.84% |  |  |  | ETF_ER_embedded_no_extra_mgmt |

## What improved after corrections

- Missing held-stock returns are halt-zero-flagged (weight reported), not silent price fills.
- Daily returns use explicit pct_change(fill_method=None).
- Balance-sheet shares enter at period_end + lag (availability), not period_end.
- constant_latest share counts are audit-only and excluded from market-cap eligibility.
- Annual income uses vendor-labelled annual only (no gap→annual misclassification).
- Average book equity is matched to income-window period ends, not row positions.
- ADV requires all 20 session observations.
- Strategy/ETF returns recorded only from first execution close (no pre-trade SPY-like accrual).
- Cost accounting labelled as proportional approximation in meta and reports.

## What remains uncertain

- Yahoo restated fundamentals and a fixed lag are **not** as-filed point-in-time.
- Current S&P constituents applied historically → survivorship / membership bias.
- Current sector labels applied historically.
- Short fundamental window (first rebalance 2023-06-30).
- Quality uses **vendor-labelled annual** income on Yahoo (genuine 4Q TTM coverage too thin for a frozen baseline).
- Cost model remains a proportional approximation.
- 2026 results were already inspected in prior work.

## What the evidence says about combining value + quality + momentum

After corrected accounting on the Yahoo exploratory panel, VQM after-cost CAGR=26.71% vs momentum-only=35.64%, universe-cap=22.54%, SPY=20.40%. Sharpes: VQM=1.13, momentum=1.32. Avg one-way turnover: VQM=27.63%, momentum=27.49%. Largest calendar-year VQM−momentum spread is in 2025 (spread=-14.55%); treat single-year dominance as a risk to the claim. On this sample, adding value and quality does **not** clearly improve the portfolio enough to justify the extra fundamental data and implementation complexity versus momentum-only or the eligible-universe benchmarks.

## Paid management proposition ($10mm illustrative)

After-fee VQM CAGR=25.77% vs momentum-after-fee=34.63%, universe-cap (after cost)=22.54%, SPY=20.40%. The combination does not clearly earn a stock-level management fee; simplify the product definition for the assignment.

## Operational feasibility vs firm economics

At illustrative $10mm AUM, median position/ADV=0.0002560233382753957, p95=0.0013629586223820745, max=0.055944665608902704. Operational feasibility of small AUM is separate from whether a standalone firm can charge for alpha that has not been established on credible PIT data.

## Continue / simplify / reject

**SIMPLIFY** — Evidence supports simplifying toward (a) momentum-only within the same rules, or (b) the eligible-universe sector-equal/cap benchmarks as the honest baseline, or (c) a separately labelled monthly VLUE/QUAL/MTUM ETF allocation for the pitch — not as a substitute track record for the stock strategy. Do not claim the in-sample winner will keep winning.

## Minimum next research step that could change the decision

If keeping stocks: licensed historical membership + as-reported fundamentals with availability dates. If assignment-only: freeze a VLUE/QUAL/MTUM equal-weight monthly rebalance ETF sleeve with after-inception histories, one-sided costs, and no double-counting of ER.

## Baseline freeze (do not silently change)

```json
{
  "long_only": true,
  "rebalance": "monthly",
  "sector_weights": "match_eligible_universe_cap_weights_at_rebalance",
  "within_sector": "equal_weight_selected",
  "selection": "top_20pct_within_sector_on_equal_weight_VQM_composite",
  "execution": "next_session_close",
  "value": "book_equity / contemporaneous_market_cap",
  "quality": "vendor_labelled_annual_NI / period_matched_avg_book (Yahoo exploratory)",
  "quality_mode": "annual_labelled",
  "quality_note": "Genuine 4Q TTM unavailable for Yahoo panel at scale; annual labelled separately",
  "momentum": "total_return between 252-session and 21-session lookback endpoints",
  "cost_model": "PROPORTIONAL_APPROXIMATION L1 * bps_per_side",
  "missing_returns": "halt_zero_flagged",
  "first_rebalance": "2023-06-30",
  "design_end": "2025-12-31",
  "data_label": "BIASED_EXPLORATORY_YAHOO_CURRENT_CONSTITUENT_PANEL"
}
```
