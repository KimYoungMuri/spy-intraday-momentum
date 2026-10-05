# Executive Summary — B9339 HW2 (CORRECTED)

**Pitch objective:** Raise illustrative **$10,000,000** AUM for a systematic long-only U.S. equity VQM strategy (asset-raising pitch).

**Status:** Accounting bug fixed; results below replace all pre-correction numbers.  
**Do not cite:** 43.458% stock CAGR, 81.584% holdout CAGR, or 14.678% ETF-proxy CAGR.

**Student:** Young Kim · **Cutoff:** 2026-10-05 · **Code:** `hw2/` · **Branch:** `hw2/accounting-correction`

## Corrected answer summary

### Stock exploratory panel (Yahoo / current S&P constituents — biased)
Design window **2023-07-03 → 2025-12-31** (628 days). Next-close execution. Beginning-weight return accounting.

| Portfolio | CAGR | Vol | Sharpe | Max DD | IR vs SPY |
|-----------|------|-----|--------|--------|-----------|
| VQM after 5 bps/side | **25.47%** | 18.32% | 1.065 | −23.43% | 0.654 |
| VQM after costs + 75 bps fee | **24.53%** | 18.32% | 1.024 | −23.50% | 0.547 |
| Value-only | 25.01% | 18.86% | 1.020 | −21.52% | 0.420 |
| Quality-only | 18.20% | 15.92% | 0.824 | −19.86% | −0.331 |
| Momentum-only | 35.64% | 21.18% | 1.316 | −26.36% | 1.348 |
| Universe cap-weight | 22.54% | 15.39% | 1.082 | −19.49% | 1.112 |
| SPY | **20.40%** | 15.51% | 0.961 | −18.76% | — |

Avg monthly one-way turnover (VQM): **27.80%**.  
See `outputs/tables/design_period_summary.csv` for ≥5 decimal places.

### Labelled ETF proxy (NOT stock track record), 2014→2026-09
Equal-weight VLUE/QUAL/MTUM after 5 bps/side: CAGR **14.43%** vs SPY **14.13%** (active ≈ +0.31%/yr).

## What evidence supports
1. Corrected, tested portfolio accounting (`tests/test_accounting.py`).  
2. On this short biased panel, VQM after costs/fees beat SPY; universe-cap is a tougher hurdle.  
3. Longer ETF blend only barely beats SPY.

## What evidence does **not** support
1. Durable ~25% expected CAGR or investable PIT alpha.  
2. Novelty of value/quality/momentum.  
3. Using the ETF proxy as the proposed stock strategy’s track record.  
4. Treating the 2026 slice as untouched out-of-sample validation.

## Feasibility at $10mm
Operationally plausible in liquid large caps. Fee revenue 75 bps × $10mm ≈ **$75,000/year** gross — not a standalone firm P&L case.

## Pitch recommendation
Sell **process transparency and risk controls**. Show corrected short-sample results honestly as an exploratory hypothesis test; use the ETF proxy for longer context; disclose Yahoo/current-constituent biases. Prefer Sharadar/CRSP before claiming an investable track record.
