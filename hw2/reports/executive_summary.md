# Executive Summary — B9339 HW2 Investor Pitch

**Pitch objective:** Raise an illustrative **$10,000,000** of AUM for a systematic long-only U.S. equity strategy combining value, quality, and momentum (VQM), sector-neutralized.

**Student:** Young Kim · **Cutoff:** 2026-10-05 · **Code:** `hw2/`

## Answer summary (key numbers; ≥5 decimals in tables under `outputs/tables/`)

### Stock-selection backtest (Yahoo fundamentals-limited sample — **not** a 10-year stock track record)
Processed Yahoo fundamentals begin **2021-10-31** (`period_end`); the coded design window is only what `first_rebalance` through `design_end` allow (~2.5 calendar years).
| Portfolio (design: 2023-06-30 → 2025-12-31, net 5 bps/side) | CAGR | Ann. vol | Sharpe | Max DD | TE vs SPY | IR vs SPY |
|---|---:|---:|---:|---:|---:|---:|
| **VQM baseline** | 0.43458 | 0.18184 | 1.80919 | −0.21980 | 0.07443 | 2.35803 |
| Value-only | 0.36813 | 0.18416 | 1.53052 | −0.19057 | 0.09817 | 1.30795 |
| Quality-only | 0.31422 | 0.15855 | 1.49649 | −0.18496 | 0.05472 | 1.53106 |
| Momentum-only | 0.53167 | 0.21367 | 1.87609 | −0.24360 | 0.10188 | 2.42828 |
| Eligible-universe cap-weight | 0.32432 | 0.15872 | 1.54322 | −0.18555 | 0.01708 | 5.35429 |
| SPY | 0.20934 | 0.15518 | 0.98903 | −0.18755 | — | — |

- Net of 75 bps fee: CAGR **0.42387**; high-cost 15 bps/side: CAGR **0.42486**.
- Avg monthly one-way turnover (VQM): **0.27376**.
- Historical holdout 2026-01-01→2026-09-29: VQM CAGR **0.81584** vs SPY **0.17925** — **too short to interpret as validation**.

### Labelled ETF proxy (NOT the stock strategy) 2014-01-31→2026-09-30
| | CAGR | Sharpe | Max DD |
|---|---:|---:|---:|
| Equal-weight VLUE/QUAL/MTUM (5 bps/side) | 0.14678 | 0.74467 | −0.35588 |
| SPY | 0.14069 | 0.73712 | −0.33717 |

Active CAGR ≈ **+0.00609**/yr — modest, not a compelling standalone case for expensive active management.

## What the evidence supports
1. The **implementation is runnable and internally consistent** (signals, sector ranks, top-20% selection, sector-cap / within-sector equal weights, costs, fees).
2. Over the **short Yahoo-fundamentals window (mid-2023–2025)**, the VQM book beat SPY and the eligible-universe cap benchmark **after estimated costs and fees**.
3. A **longer ETF factor blend** only modestly beat SPY since 2014 — consistent with a crowded, low-cost factor world.

## What the evidence does **not** support
1. **Durable outperformance** or a 40%+ “expected” CAGR — the stock sample is short and coincides with a strong equity regime; sampling uncertainty is large.
2. **Point-in-time / CRSP–Compustat quality** — Yahoo fundamentals are restated; sectors are current labels; panel is current S&P 500 names (survivorship/membership bias).
3. **Novelty** of value, quality, momentum, or equal-weight composites — these are established.
4. Using the ETF proxy as the **stock-selection track record** — forbidden; labelled separately.

## Feasibility at $10mm
Operationally feasible for liquid large-caps at ~27%/month one-way turnover with 5–15 bps/side assumptions. Fee revenue at 75 bps on $10mm ≈ **$75,000/year** — may cover a thin research stack but is **not** a standalone firm P&L case.

## Recommendation for the pitch
Raise capital on **process transparency and risk controls**, not on the short-sample CAGR. Lead with methodology, costs, and limitations; show stock results as **hypothesis tests on constrained public data**, and the ETF proxy as the longer **labelled** comparison.
