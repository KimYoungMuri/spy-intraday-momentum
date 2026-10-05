# Research Log — HW2 VQM Strategy

**Retrieval / analysis cutoff:** 2026-10-05  
**Pitch objective:** Raise illustrative $10,000,000 AUM.

## Pre-registered baseline (before evaluating results)

### Hypothesis
Combining inexpensive valuations (B/M), strong profitability (ROE), and positive 12–1 momentum — ranked within sectors and equal-weighted — may produce a more balanced selection process than any single characteristic. **Hypothesis to test, not an assumed edge.**

### Baseline rules (locked)
- Research panel: current GitHub/S&P-500-constituent snapshot (explicitly **not** historical S&P 500 membership).
- Each month-end: top ≤500 by market cap among eligible panel names.
- Eligibility: price ≥ $5, 20-day ADV ≥ $1mm, book equity > 0, required signals non-missing.
- Value = B/M; Quality = TTM (or latest annual) NI / book; Momentum = 12–1 Adj Close.
- Sector percentile ranks; composite equal-weight; top ~20% within sector.
- Sector weights = eligible-universe cap sector weights; equal-weight within sector.
- Monthly rebalance; long-only; no leverage.
- Fundamental lag = 60 calendar days.
- Trading cost baseline = 5 bps **per side** (estimated).
- Illustrative management fee = 75 bps/year (separate).

### Evaluation splits (final, after Yahoo coverage audit)
- **Design:** 2023-06-30 → 2025-12-31 (Yahoo annual+quarterly fundamentals only support ~2021+; first rebalance moved later for credibility).
- **Historical holdout:** 2026-01-01 → 2026-09-29 (frozen until design fixed; too short to validate).

### Robustness variants (pre-specified; executed)
Signal weights, selection 10/20/30%, monthly vs quarterly, lags 45/60/90, costs 5/10/15/25 bps — see `outputs/tables/robustness_design.csv`.

## Pipeline incidents and fixes

| When | Event | Resolution |
|------|-------|------------|
| 2026-10-05 | Full `run_download` crashed after fundamentals 503/503 on `ValueError: Cannot mix tz-aware with tz-naive values` at shares_all date normalize | Added `sis_hw2.utils.dates.to_naive_timestamp`; applied in `download.py` before saving shares |
| 2026-10-05 | Zero-metric run (terminal 696600) used quarterly-only fund history ending 2025+ for a 2014 design start | **Ignore** that run; enriched annual statements; set `first_rebalance=2023-06-30` |
| 2026-10-05 | Successful recovery: `run_research.py --skip-download` (terminal 149529, EXIT 0) | Tables/figures written under `outputs/` |
| 2026-10-05 | `shares_all` missing after crash | Rebuilt from fundamentals `shares_bs` + `shares_latest` constants (no Yahoo redownload) |

## Material assumptions and departures

1. Universe ≠ historical S&P 500 (current panel only).
2. Yahoo fundamentals restated; lag ≠ as-filed PIT.
3. Annual Yahoo history ~4 years → short stock sample by design.
4. Constant latest shares for MCap ranking when history sparse.
5. Current GICS sectors applied historically.
6. Costs estimated, not observed TCA.
7. ETF proxy labelled separately — not stock track record.

## Executed variants (real outputs)

| Artifact | Path |
|----------|------|
| Design summary | `outputs/tables/design_period_summary.csv` |
| Holdout | `outputs/tables/holdout_summary.csv` |
| Robustness | `outputs/tables/robustness_design.csv` |
| ETF proxy (aligned short) | `outputs/tables/etf_proxy_summary.csv` |
| ETF proxy long 2014–2026 | `outputs/tables/etf_proxy_long_horizon_summary.csv` |
| Turnover / annual / holdings | `outputs/tables/turnover.csv`, `annual_returns.csv`, `rebalance_holdings_log.csv` |

### Headline design results (net 5 bps/side)
- VQM CAGR **0.43457765**, Sharpe **1.80919169**, max DD **−0.21979657**
- SPY CAGR **0.20933880**, Sharpe **0.98903178**
- Avg monthly one-way turnover **0.27376326**

## Biases checklist

| Bias | Present? | Disclosure |
|------|----------|------------|
| Survivorship / membership | Yes | Current panel only |
| Restatement | Yes | Yahoo; lag only |
| Sector retrojection | Yes | Current GICS |
| Delisting incompleteness | Yes | Yahoo |
| Short-sample / data mining | Elevated | Pre-specified knobs; holdout tiny |
| Look-ahead prices | Controlled | Month-end formation |

## Honesty notes for presentation
- Do not quote ~43% CAGR as an expected forward return.
- Do not present ETF proxy as the stock book’s track record.
- Lead with process + limits; treat short-sample outperformance as a constrained public-data hypothesis test.
