# READ ME FIRST — Corrected HW2 Research Package

**Branch:** `hw2/accounting-correction`  
**Original (superseded) commit:** `d51066f`  
**Do not cite:** pre-correction ~43.5% stock CAGR, ~81.6% holdout CAGR, or ~14.7% ETF-proxy CAGR.

---

## A. What we tested

A **systematic long-only U.S. equity** process that combines:

1. **Value** — book equity / market cap  
2. **Quality** — net income / average book equity (prefer 4-quarter TTM; Yahoo panel often uses **labelled annual** NI)  
3. **Momentum** — 12−1 total return using **21 / 252 trading sessions**

Within the eligible top-500-by-market-cap names (among a **current** S&P 500 research panel), we rank within sectors, equal-weight the three ranks, take the top ~20% per sector, set **sector weights to match the eligible-universe cap-weighted sector weights at rebalance**, and equal-weight names within sector. Monthly rebalance, long-only, no leverage.

**Pitch objective:** raise an illustrative **$10mm** AUM (not firm working capital).

This is multifactor stock selection — **not** residual mean-reversion / stat-arb.

---

## B. What data we actually used

| Item | Source | Status |
|------|--------|--------|
| Prices (OHLCV + Adj Close) | Yahoo Finance via `yfinance` | Cached locally |
| Fundamentals | Yahoo quarterly/annual statements | **Restated**, not as-reported PIT |
| Shares | Yahoo share history / BS lines | Historical preferred |
| Universe / sectors | Current GitHub S&P 500 constituents + current GICS | **Not** historical membership |
| Benchmark | SPY Adj Close | Real |
| ETF proxy | VLUE, QUAL, MTUM | Real; **separate** from stock strategy |
| Risk-free | FRED DGS3MO yield → `/100/252` | Yield approximation, not Ken French RF |

**Stock design window:** 2023-07-03 → 2025-12-31 (628 daily observations).  
Yahoo fundamentals usable for signals are sparse before ~2022 annuals; quarterly depth is recent. Prefer shorter credible sample over a fake 10-year stock track record.

**Label:** `BIASED_EXPLORATORY_YAHOO_CURRENT_CONSTITUENT_PANEL` — survivorship, membership, restatement, and sector-retrojection biases remain **even after accounting fixes**.

**Sharadar / CRSP-Compustat:** not purchased / not available. If you can grant Sharadar API access via env var (never paste keys in chat), we can rebuild a proper PIT version.

---

## C. Main results (CORRECTED accounting)

**Event sequence:** signals at month-end close → existing book earns next session → trade at **next close** → costs scale NAV: \((1+R_p)(1-\text{cost})(1-\text{fee})-1\).  
**Portfolio return:** \(R_p = \sum w_i r_i\) with beginning-of-period weights (bug fixed).

### Stock strategy (exploratory Yahoo panel)

| Portfolio | CAGR | Vol | Sharpe | Max DD | Beta | TE | IR | Turnover (1-way) | Sample |
|-----------|------|-----|--------|--------|------|----|----|------------------|--------|
| VQM **gross** (0 cost) | **25.89%** | 18.32% | 1.08 | −23.38% | 1.09 | 7.04% | 0.70 | 27.80% | 2023-07-03→2025-12-31 |
| VQM **after 5 bps/side** | **25.47%** | 18.32% | 1.06 | −23.43% | 1.09 | 7.04% | 0.65 | 27.80% | same |
| VQM after costs **+ 75 bps fee** | **24.53%** | 18.32% | 1.02 | −23.50% | 1.09 | 7.04% | 0.55 | 27.80% | same |
| Value-only | 25.01% | 18.86% | 1.02 | −21.52% | 1.02 | 10.31% | 0.42 | 11.07% | same |
| Quality-only | 18.20% | 15.92% | 0.82 | −19.86% | 0.97 | 5.39% | −0.33 | 7.19% | same |
| Momentum-only | 35.64% | 21.18% | 1.32 | −26.36% | 1.24 | 9.62% | 1.35 | 27.49% | same |
| Eligible-universe cap-weight | 22.54% | 15.39% | 1.08 | −19.49% | 0.99 | 1.57% | 1.11 | 2.97% | same |
| SPY | **20.40%** | 15.51% | 0.96 | −18.76% | — | — | — | — | same |

High-precision CSVs: `outputs/tables/design_period_summary.csv` (≥5 decimals).

**Cumulative (after costs):** VQM total return **+76.01%** vs SPY **+58.84%** over the same dates.

**Previously examined 2026 slice** (not untouched OOS): VQM ann. ~**29.94%** vs SPY ~**17.93%** (186 days) — short; do not treat as validation.

### Calendar years (partial 2023)

| Year | VQM after costs | SPY |
|------|-----------------|-----|
| 2023 (partial from Jul) | +6.98% | +8.04% |
| 2024 | +42.09% | +24.89% |
| 2025 | +15.79% | +17.72% |

### Labelled ETF proxy (NOT the stock strategy) 2014-01-31→2026-09-30

| | CAGR | Sharpe | Max DD |
|--|------|--------|--------|
| Equal-weight VLUE/QUAL/MTUM (5 bps/side) | **14.43%** | 0.73 | −35.65% |
| SPY | **14.13%** | 0.74 | −33.72% |

Active CAGR ≈ **+0.31%/yr** after the accounting fix.

---

## D. Economic interpretation

1. **After costs and fees**, exploratory VQM still beat SPY and the eligible-universe cap book in this short window — but the edge vs universe-cap is modest (~3 pp CAGR after costs).  
2. **Momentum-only** dominated the composite in-sample; quality lagged. Combining factors did **not** beat momentum alone here.  
3. **Turnover ~28%/month one-way** is material; 5→15 bps/side cuts CAGR from 25.47% to 24.63%.  
4. **$10mm feasibility:** large-cap panel + ADV filter make operations plausible; 75 bps × $10mm = **$75k/year** gross fee revenue ≠ firm viability.  
5. Longer **ETF proxy** shows only tiny active return vs SPY — consistent with crowded, cheap factor products.

---

## E. Confidence and limitations

| Type | Content |
|------|---------|
| **Fact** | Pre-correction engine inflated returns (weights updated before return). Regression test: 50/50 ±10% → 0% port return, 55/45 weights. |
| **Fact** | Corrected rerun on same cached Yahoo inputs produces the table above. |
| **Assumption** | 5 bps/side costs; 75 bps fee; 60-day fundamental lag; next-close execution. |
| **Assumption** | Annual NI / book is an acceptable quality proxy when 4Q TTM unavailable (labelled). |
| **Bias** | Current S&P panel, restated Yahoo fundamentals, current sectors. |
| **Not proven** | Durable alpha, capacity, novelty of VQM, or investable PIT track record. |

---

## Figures

- `outputs/figures/design_cumret.png`  
- `outputs/figures/growth_of_10000.png`  
- `outputs/figures/vqm_drawdown.png`  
- `outputs/figures/cost_sensitivity.png`  
- `outputs/figures/etf_proxy_cumret_long.png` / `etf_proxy_long_cumret.png`  
- `outputs/figures/full_cumret_holdout.png`

## Reproduce

```bash
cd hw2
source .venv/bin/activate
export PYTHONPATH=$PWD/src MPLBACKEND=Agg
pytest tests/test_accounting.py -q
python scripts/run_research.py --skip-download
```

## What I still need from you (optional upgrade)

Sharadar (or CRSP/Compustat) access via **local env var** (e.g. `SHARADAR_API_KEY`) — never paste the key in chat — plus confirmation of which bundle you can use. Without it, keep this package labelled as a **biased exploratory demonstration**.
