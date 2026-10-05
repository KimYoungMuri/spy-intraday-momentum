# Investor Pitch Slide Write-Up (CORRECTED — SIMPLIFY)

**Primary deck outline (7 pages, assignment-mapped):** `reports/pitch_deck_outline.md`  
**Decision memo:** `reports/STRATEGY_DECISION.md`  
**Numbers:** `outputs/tables/AF_comparison_summary.csv` (≥5 decimals)

Use with figures in `outputs/figures/`. All stock results are **exploratory Yahoo / current-constituent** unless noted. Pre-correction CAGRs are retired. Research decision: **SIMPLIFY**.

---

## Page 1 — Summary & $10mm AUM ask
- Objective: raise **$10mm AUM** (not working capital).
- After corrections: VQM after 5 bps/side CAGR **0.26712** vs SPY **0.20402**, universe-cap **0.22539**, momentum-only **0.35640**.
- Decision: combining V+Q does not justify fee/complexity vs simpler sleeves → **SIMPLIFY**.
- Chart: `growth_of_10000.png`

## Page 2 — Landscape
- Index (SPY) vs single-factor ETFs (VLUE/QUAL/MTUM) vs multifactor SMAs.
- We are not inventing VQM; research question is fee/complexity justification.

## Page 3 — Main idea + methodology + formulas
- \(V=B/M\); \(Q=\mathrm{NI}^{annual}/B_{avg}\); \(M=P_{t-21}/P_{t-252}-1\); \(R_p=\sum w_i r_i\); next-close; proportional cost approx.
- Sector weights match eligible universe at rebalance; top ~20%/sector.

## Page 4 — Results (A–F)
- Show gross / after-cost / after-fee distinctly.
- Momentum dominates; quality lags; VQM mid.
- Chart: `AF_comparison_cumret.png` / `design_cumret.png`

## Page 5 — Innovation & competitive advantage (honest)
- No new factors. Advantage = transparency, corrected accounting, reproducible rules — **not** proven alpha.
- ETF proxy ≈ +0.31%/yr vs SPY is a *different* product.

## Page 6 — Robustness & feasibility
- Math fixed; data still biased / not PIT.
- $10mm ADV: median position/ADV ≈ 0.000256; fee revenue $75k/yr ≠ firm economics.
- Charts: `vqm_drawdown.png`, `cost_sensitivity.png`

## Page 7 — Anticipated Q&A + close
- Why pay 75 bps? Evidence does not clearly support stock VQM fee vs momentum.
- 2026 previously examined; survivorship yes; old ~43% retired.
- Ask: $10mm to run published rules with full disclosure; claim simplified.

**Close:** Accurate research over flattering stories.
