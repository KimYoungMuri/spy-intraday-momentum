# Final Strategy Specification — VQM Sector-Neutral Long-Only

## Pitch objective
Raise an illustrative **$10,000,000** of assets to manage in a systematic, long-only U.S. equity strategy (asset-raising pitch, not a firm working-capital raise).

## Hypothesis
Combining inexpensive valuations, strong profitability, and positive intermediate-term price momentum — measured within sectors — may produce a more balanced selection process than any single characteristic. **Hypothesis to test, not an assumed result.**

## Universe (precise definition)
**Eligible research panel:** current S&P 500 constituent tickers from the public GitHub `datasets/s-and-p-500-companies` snapshot (retrieval timestamp stored).  

**At each month-end rebalance:** among panel names passing tradability filters, select the **500 largest by contemporaneous market capitalization** (or all eligible if fewer than 500).

This is **not** the historical S&P 500 index, not CRSP top-500, and not a point-in-time membership file.

### Tradability / data filters
- Last close ≥ $5  
- Mean 20-day dollar volume ≥ $1,000,000  
- Book equity > 0  
- Non-missing value, quality, and momentum signals after lag  
- Non-missing sector label  

## Signals
Let \(i\) index stocks and \(t\) a month-end rebalance date.

1. **Value (book-to-market):**  
   \[
   V_{i,t} = \frac{B_{i,t}}{\mathrm{MCap}_{i,t}}
   \]
   where \(B_{i,t}\) is the latest book equity with period-end + 60 days ≤ \(t\).

2. **Quality (ROE):**  
   \[
   Q_{i,t} = \frac{\mathrm{NI}^{TTM}_{i,t}}{B_{i,t}}
   \]
   with \(\mathrm{NI}^{TTM}\) the sum of up to four lagged quarterly net incomes.

3. **Momentum (12–1):**  
   \[
   M_{i,t} = \frac{P^{\mathrm{adj}}_{i,t-21\mathrm{d}}}{P^{\mathrm{adj}}_{i,t-365\mathrm{d}}} - 1
   \]

## Ranking and composite
Within each GICS sector among eligible top-N names:
\[
R^{V}_{i,t}, R^{Q}_{i,t}, R^{M}_{i,t} \in (0,1]
\]
are percentile ranks (higher = more attractive).

Composite (baseline equal weights):
\[
S_{i,t} = \tfrac{1}{3} R^{V}_{i,t} + \tfrac{1}{3} R^{Q}_{i,t} + \tfrac{1}{3} R^{M}_{i,t}
\]

## Portfolio construction
1. Within each sector, select the top \(\lceil 0.20 \cdot N_{\mathrm{sector}}\rceil\) names by \(S_{i,t}\) (minimum 1 if \(N_{\mathrm{sector}}\ge 1\)).  
2. Sector weight = sector’s share of eligible-universe market cap.  
3. Equal-weight selected names within sector.  
4. Renormalize to sum to 1.  
5. **No leverage, no shorting** in baseline.

## Rebalance, timing, drift
- **Frequency:** month-end.  
- **Formation:** signals use information available as of rebalance close.  
- **Trading:** target weights set at rebalance close.  
- **Returns:** daily portfolio return from drifting weights using Adj Close returns; costs charged on rebalance days.  
- **Drift:** weights float with relative returns between rebalances.

## Costs and fees
- Baseline transaction cost: **5 bps per side** × sum of absolute weight changes (estimated, not observed execution).  
- High-cost scenario: 15 bps per side (plus robustness grid).  
- Illustrative management fee: **75 bps/year**, accrued ~daily, reported separately from trading-cost-only results.

## Benchmarks
1. **SPY** total return (primary broad U.S. large-cap ETF proxy).  
2. **Cap-weighted eligible universe** (same filters/top-N, cap weights).  
3. Single-factor portfolios: value-only, quality-only, momentum-only (same construction).  
4. **Labelled ETF proxy** (equal-weight VLUE/QUAL/MTUM): comparison only — **not** the strategy track record.

## Evaluation design
- **Stock-selection design** (Yahoo fundamentals-limited): `first_rebalance` **2023-06-30** → **2025-12-31** (`config.yaml`; ~629 daily return obs). Earliest processed `period_end` in data is **2021-10-31**; with 60-day lag, 12–1 momentum, and TTM quality, earlier rebalances are not credible on this feed.
- **Historical holdout:** 2026-01-01 → 2026-09-30 (design frozen; too short to validate).
- **Labelled ETF proxy** (not stock track record): 2014-01-31 → 2026-09-30 for longer horizon comparison.
- Pre-specified robustness: signal weights, selection %, monthly vs quarterly, lags, cost bps  

## Material limitations (must disclose)
Survivorship/membership bias; restated fundamentals; retroactive sectors; incomplete delisting returns; estimated (not observed) trading costs; Yahoo coverage gaps.
