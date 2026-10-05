# Appendix — VQM investor pitch (readable)

Self-contained companion to `reports/slides/pitch_deck.html` and `pitch_deck.pdf`.

## A. High-precision design-window results

Source: `outputs/tables/AF_comparison_summary.csv`  
Window: 2023-07-03 → 2025-12-31

| strategy | cagr | ann_vol | sharpe | max_drawdown | avg_turnover_one_way | cost_fee_layer |
| --- | --- | --- | --- | --- | --- | --- |
| F_VQM_equal | 0.2671197 | 0.18044592 | 1.13332664 | -0.22866483 | 0.27629895 | after_trading_cost_5bps |
| C_momentum_only | 0.35640087 | 0.21179152 | 1.31642217 | -0.26359087 | 0.2749483 | after_trading_cost_5bps |
| A_universe_cap | 0.22538931 | 0.15388229 | 1.08205759 | -0.1948667 | 0.02971047 | after_trading_cost_5bps |
| SPY | 0.2040235 | 0.15514332 | 0.96084893 | -0.18755221 | nan | ETF_ER_embedded_no_extra_mgmt |
| F_VQM_after_fee | 0.25765171 | 0.18044055 | 1.09175279 | -0.22944497 | 0.27629895 | after_trading_cost_and_75bps_mgmt |
| F_VQM_gross | 0.27134196 | 0.18041964 | 1.15192104 | -0.22818815 | 0.27629895 | gross_0bps |

### Turnover reconciliation
- Engine average one-way turnover (**includes initial formation**): **0.27629895** (27.63%) — matches `AF_comparison_summary.csv` / backtest rebalance log.
- Average across **29 subsequent rebalances only** (ex-formation, from holdings weight changes): **0.25480938** (25.48%).
- Definition: one-way turnover = ½ × Σᵢ |Δwᵢ| at each rebalance.

Performance tables on main slides are **after estimated trading costs of 5 bps per side; before management fees** (unless an after-fee row is shown).

## B. Complementarity diagnostics (slide 5)

### Holdings overlap — averages across rebalances
Each statistic is the **average across rebalance dates** (n_dates = 30).

| pair | avg_jaccard | avg_weight_overlap | n_dates |
| --- | --- | --- | --- |
| VQM_vs_Momentum | 0.423033 | 0.596679 | 30 |
| VQM_vs_Value | 0.122759 | 0.224445 | 30 |
| VQM_vs_Quality | 0.205782 | 0.335544 | 30 |
| Momentum_vs_Value | 0.049034 | 0.098579 | 30 |
| Momentum_vs_Quality | 0.138546 | 0.244293 | 30 |
| Value_vs_Quality | 0.009449 | 0.011208 | 30 |

### Characteristic ranks — portfolio-weighted averages
At each rebalance, compute Σ wᵢ × (sector percentile rank)ᵢ, then average those portfolio-level numbers across rebalances.

| portfolio | wavg_rank_value | wavg_rank_quality | wavg_rank_momentum | wavg_value_bm | wavg_quality_roe | wavg_momentum |
| --- | --- | --- | --- | --- | --- | --- |
| Momentum | 0.386822 | 0.511532 | 0.90204 | 1.464942 | 0.408936 | 0.749282 |
| Quality | 0.200447 | 0.903479 | 0.548749 | 0.088708 | 1.385137 | 0.284572 |
| UniverseCap | 0.353854 | 0.626283 | 0.590049 | 0.185317 | 0.595413 | 0.288967 |
| VQM | 0.502248 | 0.644153 | 0.798888 | 7.077104 | 0.549695 | 0.55183 |
| Value | 0.90481 | 0.272787 | 0.388966 | 8.35908 | 0.074968 | 0.072305 |

Interpretation for VQM (~0.50 / 0.64 / 0.80): **momentum-tilted with additional profitability exposure**. A value rank near 0.50 is near the middle of the ranking universe — not a strong value tilt.

### Active-return correlations
**Active return** = sleeve daily return − SPY daily return on the same dates.  
Benchmark = SPY total return (Adj Close). These are **active returns**, not regression residuals.

|  | VQM | Momentum | Value | Quality |
| --- | --- | --- | --- | --- |
| VQM | 1.0 | 0.74442 | 0.380564 | 0.564729 |
| Momentum | 0.74442 | 1.0 | 0.012733 | 0.184049 |
| Value | 0.380564 | 0.012733 | 1.0 | 0.448187 |
| Quality | 0.564729 | 0.184049 | 0.448187 | 1.0 |

## C. Short robustness table

Source: `outputs/tables/robustness_design.csv`

| variant | cagr | sharpe | max_drawdown |
| --- | --- | --- | --- |
| selection_pct=0.1 | 0.31048614 | 1.21478654 | -0.23241734 |
| selection_pct=0.2 | 0.25466536 | 1.06499391 | -0.23425173 |
| selection_pct=0.3 | 0.22391664 | 0.97399467 | -0.21564504 |
| lag_days=45 | 0.24674044 | 1.02430543 | -0.23779875 |
| lag_days=60 | 0.25466536 | 1.06499391 | -0.23425173 |
| lag_days=90 | 0.25510447 | 1.06625367 | -0.23418087 |
| weights=[0.5, 0.25, 0.25] | 0.26104654 | 1.13908953 | -0.20380867 |
| weights=[0.25, 0.5, 0.25] | 0.19189741 | 0.82228584 | -0.21506892 |
| weights=[0.25, 0.25, 0.5] | 0.28032737 | 1.12340472 | -0.24377101 |
| rebalance=Q | 0.25699999 | 1.0645096 | -0.23583092 |
| cost_bps_per_side=5.0 | 0.25466536 | 1.06499391 | -0.23425173 |
| cost_bps_per_side=10.0 | 0.25047103 | 1.04655847 | -0.23473527 |
| cost_bps_per_side=15.0 | 0.24628949 | 1.02810038 | -0.23521868 |
| cost_bps_per_side=25.0 | 0.23796467 | 0.99112252 | -0.23618509 |

## D. Sources
- Asness, C., Moskowitz, T., & Pedersen, L. (2013). Value and Momentum Everywhere. *Journal of Finance*. Also summarized at aqr.com.
- Fama, E. & French, K. (1992, 2015).
- iShares VLUE / QUAL / MTUM fact sheets (ishares.com), published expense ratio 0.15% (mid-2026 fact sheets).
- Market/fundamental inputs: Yahoo Finance via yfinance (exploratory; restated). Risk-free: FRED DGS3MO. Universe: current S&P research constituent panel.

## E. Artifact checklist
- `outputs/tables/holdings_overlap_summary.csv`
- `outputs/tables/holdings_overlap_VQM_vs_Mom.csv`
- `outputs/tables/portfolio_signal_exposures.csv` / `_avg.csv`
- `outputs/tables/sleeve_active_return_corr.csv`
- `outputs/tables/complementarity_evidence.json`
- `outputs/figures/holdings_overlap_VQM_Mom.png`
- `outputs/figures/portfolio_characteristic_exposures.png`
- `outputs/figures/sleeve_active_corr.png`
