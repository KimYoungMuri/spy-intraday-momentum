# Final Strategy Specification — VQM (CORRECTED)

## Pitch objective
Raise illustrative **$10,000,000** AUM for a systematic long-only U.S. equity strategy (not working capital).

## Hypothesis
Combining inexpensive valuations, strong profitability, and positive 12−1 momentum — ranked within sectors — may produce a more balanced selection process than any single characteristic. **Hypothesis to test.**

## Universe
**Intended:** 500 largest eligible U.S. common stocks by **historical** market cap at each rebalance among securities then available.

**Implemented in this package (labelled exploratory):** top 500 by contemporaneous mcap among a **current** S&P 500 ticker panel (GitHub constituents snapshot). Not historical S&P membership; not CRSP top-500. Multiple share classes: panel uses primary Yahoo tickers (no dual-class de-duplication beyond vendor symbols). ADRs/REITs: excluded only if not on the panel; no separate REIT filter.

**Filters (at signal date):** unadjusted close ≥ $5; ADV over **exactly 20 prior trading sessions** ≥ $1mm; book equity > 0; valid value, quality, and momentum; sector label present.

## Signals
- **Value:** \(B/M = B_{avail}/MCap\) with \(B\) available after period-end + 60 days.  
- **Quality:** prefer \(\mathrm{NI}^{TTM}_{4Q}/B_{avg}\); if 4Q unavailable, use **labelled annual** NI / \(B_{avg}\) (Yahoo limitation).  
- **Momentum:** \(P_{t-21}/P_{t-252}-1\) on the shared trading calendar (sessions, not 21 calendar days).  
- Percentile ranks within sector **among the top-N eligible universe** (not the broader panel).  
- Composite: equal-weight ranks.  
- Select \(\lceil 0.20 N_s\rceil\) per sector (min 1); ties: higher score, then mcap, then ticker.

## Portfolio construction
- Sector weights = eligible-universe **cap sector weights at rebalance**.  
- Equal-weight within sector.  
- Describe as **sector-weight matched to the eligible universe at rebalancing** — not continuous market neutrality or SPY-sector neutrality between rebalances.  
- Long-only; no leverage.

## Timing and accounting
1. Observe signals at month-end close \(T\).  
2. Existing portfolio earns return through next session close \(T+1\).  
3. Rebalance at \(T+1\) close from drifted weights to targets.  
4. \(R_p=\sum w_i r_i\) with **beginning** weights; then \(w'_i=w_i(1+r_i)/(1+R_p)\).  
5. Costs: \(L1=\sum|\Delta w|\); cost \(=L1\times bps_{side}/10^4\); net growth \((1+R_p)(1-\mathrm{cost})(1-\mathrm{fee})-1\).  
6. 5 bps/side baseline (assumption); 75 bps/year fee shown separately.

## Benchmarks
SPY; eligible-universe cap-weight; value-/quality-/momentum-only; labelled ETF proxy (VLUE/QUAL/MTUM) — separate methodology.

## Evaluation
- Design: first execution after 2023-06-30 signal → through 2025-12-31.  
- 2026 slice: **previously examined historical evaluation period**, not untouched OOS.
