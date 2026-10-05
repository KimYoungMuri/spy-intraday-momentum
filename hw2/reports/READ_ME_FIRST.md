# READ ME FIRST — Corrected HW2 Research Package

**Decision (after corrections + A–F study):** **SIMPLIFY** — see `reports/STRATEGY_DECISION.md`.  
**Pitch outline:** `reports/pitch_deck_outline.md` (7 pages; maps to all assignment requirements).  
**Do not cite:** pre-correction ~43.5% stock CAGR, ~81.6% holdout CAGR, or ~14.7% ETF-proxy CAGR.

---

## A. What we tested

A **systematic long-only U.S. equity** process that combines:

1. **Value** — book equity / contemporaneous market cap  
2. **Quality** — vendor-labelled annual NI / period-matched average book (Yahoo exploratory baseline; genuine 4Q TTM too thin)  
3. **Momentum** — 12−1 total return using **21 / 252 trading sessions**

Within the eligible top-500-by-market-cap names (among a **current** S&P 500 research panel), we rank within sectors, equal-weight the three ranks, take the top ~20% per sector, set **sector weights to match the eligible-universe cap-weighted sector weights at rebalance**, and equal-weight names within sector. Monthly rebalance, long-only, no leverage.

**Pitch objective:** raise an illustrative **$10mm** AUM (not firm working capital).

**Research question:** Does adding value and quality to equity momentum improve the portfolio enough to justify extra data, complexity, and a management fee?

This is multifactor stock selection — **not** residual mean-reversion / stat-arb.

---

## B. What data we actually used

| Item | Source | Status |
|------|--------|--------|
| Prices (OHLCV + Adj Close) | Yahoo Finance via `yfinance` | Cached locally |
| Fundamentals | Yahoo quarterly/annual statements | **Restated**, not as-reported PIT |
| Shares | Yahoo share history / BS lines (availability = period_end + lag) | `constant_latest` excluded from mcap |
| Universe / sectors | Current GitHub S&P 500 constituents + current GICS | **Not** historical membership |
| Benchmark | SPY Adj Close | Real |
| ETF proxy | VLUE, QUAL, MTUM | Real; **separate** from stock strategy |
| Risk-free | FRED DGS3MO yield → `/100/252` | Yield approximation, not Ken French RF |

**Stock design window:** 2023-07-03 → 2025-12-31 (628 daily observations).

**Label:** `BIASED_EXPLORATORY_YAHOO_CURRENT_CONSTITUENT_PANEL` — survivorship, membership, restatement, and sector-retrojection biases remain **even after accounting fixes**.

**Sharadar / CRSP-Compustat:** not purchased. Minimum to reopen a stock claim: historical prices incl. delistings, as-reported fundamentals with availability dates, historical shares/mcap, historical membership — then rebuild PIT. Subscription ≠ point-in-time pipeline.

---

## C. Main results (CORRECTED; decision-study freeze)

**Event sequence:** signals at month-end close → existing book earns next session → trade at **next close** → costs scale NAV via **proportional L1 approximation**.  
**Portfolio return:** \(R_p = \sum w_i r_i\) with beginning-of-period weights (bug fixed).

### A–F comparison (design; after 5 bps/side unless noted)

| Portfolio | CAGR | Vol | Sharpe | Max DD | Beta | TE | Turnover (1-way) |
|-----------|------|-----|--------|--------|------|----|------------------|
| F VQM after 5 bps/side | **0.26712** | 0.18045 | 1.13333 | −0.22866 | 1.07595 | 0.06953 | 0.27630 |
| F VQM gross | 0.27134 | 0.18042 | 1.15192 | −0.22819 | 1.07575 | 0.06954 | 0.27630 |
| F VQM after cost + 75 bps fee | 0.25765 | 0.18044 | 1.09175 | −0.22944 | 1.07592 | 0.06953 | 0.27630 |
| C Momentum-only | **0.35640** | 0.21179 | 1.31642 | −0.26359 | 1.23946 | 0.09622 | 0.27495 |
| D Value-only | 0.25009 | 0.18856 | 1.02034 | −0.21520 | 1.01778 | 0.10310 | 0.11068 |
| E Quality-only | 0.19360 | 0.15670 | 0.89751 | −0.19831 | 0.95109 | 0.05330 | 0.07118 |
| A Eligible-universe cap-weight | 0.22539 | 0.15388 | 1.08206 | −0.19487 | 0.98679 | 0.01569 | 0.02971 |
| B Universe sector-equal | 0.21620 | 0.16223 | 0.98808 | −0.19920 | 0.98652 | 0.05383 | 0.05004 |
| SPY | **0.20402** | 0.15514 | 0.96085 | −0.18755 | — | — | — |

High-precision CSVs: `outputs/tables/AF_comparison_summary.csv`.

**Economic read:** VQM beats SPY and universe-cap on this short biased sample, but **momentum-only dominates VQM**. Adding value and quality does not justify the extra complexity/fee proposition → **SIMPLIFY**.

### Labelled ETF proxy (NOT the stock strategy) ~2014→2026

| | CAGR | Sharpe | Max DD |
|--|------|--------|--------|
| Equal-weight VLUE/QUAL/MTUM (5 bps/side approx) | **0.14434** | 0.73288 | −0.35649 |
| SPY | **0.14126** | 0.73998 | −0.33717 |

Active CAGR ≈ **+0.00308**/yr after accounting fix — crowded factors.

---

## D. Feasibility vs firm economics ($10mm)

- Median position/ADV ≈ **0.000256**; p95 ≈ **0.00136**; max ≈ **0.0559** (`adv_position_sizing_10mm.csv`).
- Operational trading at $10mm looks feasible for this large-cap panel; that is **separate** from whether a fee is earned.
- 75 bps × $10mm = **$75k/year** gross fee revenue ≠ firm viability (AUM pitch only).

---

## E. Confidence and limitations

| Type | Content |
|------|---------|
| **Fact** | Pre-correction engine inflated returns; regression tests pass. |
| **Fact** | Corrected A–F study on cached Yahoo inputs → SIMPLIFY. |
| **Assumption** | 5 bps/side costs; 75 bps fee; 60-day lag; next-close; annual quality. |
| **Bias** | Current S&P panel, restated Yahoo, current sectors, short sample. |
| **Not proven** | Durable alpha, capacity, novelty, investable PIT track record, fee justification. |

---

## Reproduce

```bash
cd hw2   # or equity_multifactor clone root
source .venv/bin/activate
export PYTHONPATH=$PWD/src MPLBACKEND=Agg
pytest tests/test_accounting.py -q
python scripts/run_decision_study.py   # cached raw under data/raw/
# fresh download: python scripts/run_research.py
```

Keep private keys, cookie DBs, and restricted raw dumps out of git.
