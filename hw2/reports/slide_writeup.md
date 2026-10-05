# Slide-by-Slide Investor Pitch Write-Up — VQM Sector-Neutral Long-Only

**Pitch objective:** Raise illustrative **$10,000,000** AUM (asset-raising, not firm working capital).  
**Source of numbers:** `outputs/tables/*.csv` from `scripts/run_research.py --skip-download` (terminal 149529, EXIT 0).  
**Cutoff:** 2026-10-05. All performance figures below are from that run; they are **not** fabricated.

**Critical sample disclosure (state on every results slide):** Stock-level Yahoo fundamentals only support a short design window (**2023-06-30 → 2025-12-31**, 629 daily obs). Longer evidence uses a **labelled ETF proxy** (2014–2026), which is **not** the stock-selection track record.

---

## Slide 1 — Seeking $10mm for a transparent, sector-neutral VQM process

**Title:** Seeking $10mm for a transparent, sector-neutral value–quality–momentum process

**Bullets:**
- Objective: manage an illustrative **$10,000,000** in a systematic **long-only** U.S. equity strategy (no leverage/shorts in baseline).
- Hypothesis (to test, not assume): combining cheap valuations, strong profitability, and positive 12–1 momentum *within sectors* may diversify single-factor failure modes.
- Process is fully specified, coded, and reproducible in `hw2/` with public data (Yahoo/FRED/GitHub constituents).
- We will show **gross-of-fee / net-of-estimated-cost** results honestly — including where the sample is too short to claim durable alpha.
- Ask: seed mandate to run the live process with monthly reporting of holdings, turnover, and factor exposures.

**Detailed prose:**  
Investors are not being sold a newly discovered factor. They are being offered a *documented implementation*: top-eligible large-cap panel, sector percentile ranks, top ~20% within sector, sector weights matching the eligible universe’s cap weights, equal-weight within sector, monthly rebalance. The capital ask is assets to manage, not startup working capital. Fee illustration is 75 bps/year (~$75k on $10mm) — enough for a thin research stack, not a standalone firm P&L narrative.

**Formulas:** (see Slide 4)  
**Chart:** none required; optional one-pager of process flowchart.  
**Sources/limits:** Public data only; not CRSP/Compustat point-in-time.

---

## Slide 2 — Factor products are cheap; process clarity is the real need

**Title:** Factor ETFs already exist — investors need process clarity, not another “secret sauce” claim

**Bullets:**
- Landscape: passive cap-weight (SPY/VTI), single-factor ETFs (e.g., VLUE, QUAL, MTUM), and multifactor products.
- Literature: value, quality/profitability, and momentum are **established**; equal-weight composites are **not novel**.
- Investor need: transparent construction, sector control, cost discipline, and honest limits — especially after factor crowding and multi-year underperformance episodes.
- Our differentiation is **implementation packaging** (sector-relative ranks + sector-cap matching + within-sector equal weight), not a new anomaly.
- Competitive bar: after costs, must justify fees vs buying cheap factor ETFs.

**Detailed prose:**  
An investor can buy VLUE/QUAL/MTUM (or a multifactor ETF) for low fees. Any active pitch must answer why a custom book is better. Our answer is *control and transparency*: explicit universe rules, sector neutrality relative to the eligible universe, documented lags/costs, and side-by-side single-factor sleeves. We will not claim proprietary discovery of V/Q/M.

**Chart:** product landscape table (passive / single-factor / multifactor / our book).  
**Sources:** iShares/BlackRock factor ETF materials; academic surveys of value, quality, momentum (e.g., Fama–French, Asness et al., Novy-Marx). Verify current expense ratios before presenting.

---

## Slide 3 — Economics of the three signals

**Title:** Value, quality, and momentum each have an economic story — and each can fail for years

**Bullets:**
- **Value (B/M):** compensation for risk and/or mispricing of distressed/cheap equities; can suffer in growth regimes.
- **Quality (ROE):** profitable firms may earn persistent returns if markets underweight durability of earnings.
- **Momentum (12–1):** intermediate-term continuation linked to underreaction/herding; crashes in sharp reversals.
- Combining them aims to **offset regime dependence**, not eliminate it.
- Sector-relative ranking reduces pure sector bets (e.g., banks’ book equity vs software).

**Formulas:**
\[
V_{i,t}=\frac{B_{i,t}}{\mathrm{MCap}_{i,t}},\quad
Q_{i,t}=\frac{\mathrm{NI}^{TTM}_{i,t}}{B_{i,t}},\quad
M_{i,t}=\frac{P^{\mathrm{adj}}_{i,t-21\mathrm{d}}}{P^{\mathrm{adj}}_{i,t-365\mathrm{d}}}-1
\]

**Sources/limits:** Yahoo fundamentals are **restated**; 60-day lag ≠ as-filed point-in-time. Financials’ book equity remains imperfectly comparable even with sector ranks.

---

## Slide 4 — Exact methodology (no ambiguity)

**Title:** Exact rules: top-eligible panel, sector ranks, top 20%, sector-cap / equal-within

**Bullets:**
- **Universe:** among *current* GitHub S&P 500-panel tickers (not historical S&P 500 membership), take top ≤500 by contemporaneous market cap after filters (price ≥ $5, ADV ≥ $1mm, book > 0, signals non-missing).
- **Ranks:** percentile ranks within GICS sector; higher = more attractive.
- **Composite:** \(S=\frac13 R^V+\frac13 R^Q+\frac13 R^M\).
- **Selection:** top \(\lceil 0.20 N_{\mathrm{sec}}\rceil\) per sector (min 1).
- **Weights:** sector weight = eligible-universe sector cap weight; equal-weight names inside sector; monthly rebalance; long-only.

**Timing:** signals at month-end close; costs on rebalance; weights drift daily via Adj Close returns.  
**Chart:** methodology schematic.  
**Limits:** current constituents → survivorship/membership bias; constant latest shares used for MCap ranking when history sparse.

---

## Slide 5 — Portfolio construction and risk management

**Title:** Sector-matched, fully invested, no leverage — risk managed by construction, not overlays

**Bullets:**
- Baseline: fully invested, leverage = 1, no shorts.
- Sector exposures intentionally close to eligible-universe cap sectors; stock selection is the active bet.
- Concentration: ~90 names typical at a rebalance (top 20% within 11 sectors); within-sector equal weight reduces mega-cap dominance vs pure cap-weight.
- Drift between month-ends tracked; no intra-month rebalance.
- Risk reporting: beta, TE, IR vs SPY; drawdowns; turnover.

**From design tables:** VQM beta vs SPY **1.07155**; TE **0.07443**; IR **2.35803** (short sample — IR is not a capacity/edge guarantee).  
**Chart:** `outputs/figures/vqm_drawdown.png`.

---

## Slide 6 — Data, backtest design, and performance (REAL RESULTS)

**Title:** Short-sample stock backtest beats SPY after costs — treat the CAGR as a hypothesis test, not a promise

**Bullets (design 2023-06-30→2025-12-31, net 5 bps/side):**
- **Not a decade-long stock backtest:** Yahoo `period_end` in our processed feed starts **2021-10-31**; first rebalance is **2023-06-30** after lag, momentum, and TTM-quality requirements (`config.yaml`).
- **VQM CAGR 0.43458**, vol 0.18184, Sharpe 1.80919, max DD −0.21980 (629 days).
- **SPY CAGR 0.20934**, Sharpe 0.98903, max DD −0.18755 over the same window.
- Single-factor sleeves: momentum 0.53167 > value 0.36813 > quality 0.31422; universe cap-weight 0.32432.
- Net 75 bps fee: VQM CAGR **0.42387**; 15 bps/side costs: **0.42486**.
- Avg monthly one-way turnover **0.27376**.

**Annual returns (calendar):**  
2023 (partial from first rebalance): VQM 0.13655 vs SPY 0.09315;  
2024: VQM 0.53676 vs SPY 0.24886;  
2025: VQM 0.40926 vs SPY 0.17719.

**Holdout 2026-01-01→2026-09-29:** VQM CAGR 0.81584 vs SPY 0.17925 — **too short; do not call this proof of prospective skill**.

**Labelled ETF proxy 2014–2026 (NOT stock track record):** EW VLUE/QUAL/MTUM CAGR **0.14678** vs SPY **0.14069** (active ≈ +0.00609/yr).

**Charts:** `design_cumret.png`, `full_cumret_holdout.png`, `annual_returns.png`, `etf_proxy_long_cumret.png`.  
**Tables:** `design_period_summary.csv`, `annual_returns.csv`, `holdout_summary.csv`, `etf_proxy_long_horizon_summary.csv`.

---

## Slide 7 — Robustness and limitations

**Title:** Results are directionally stable across pre-specified knobs — but the sample is short and biased

**Bullets (design CAGRs from `robustness_design.csv`):**
- Selection 10%/20%/30%: 0.44820 / 0.43458 / 0.35687.
- Lags 45/60/90d: 0.42622 / 0.43458 / 0.44931.
- Weight tilts: value-heavy 0.37579; quality-heavy 0.32507; momentum-heavy 0.45233.
- Quarterly rebalance: 0.44307; costs 5→25 bps/side: 0.43458 → 0.41521.
- Biases remain: survivorship/membership, restatement, retroactive sectors, incomplete delistings, **~2.5y stock sample driven by Yahoo fundamental history (~2021+), not CRSP/Compustat**, data-mining risk on a short window.

**Chart:** `robustness_cagr.png`, `cost_sensitivity.png`.  
**Holdout:** historical only; design frozen before evaluating 2026.

---

## Slide 8 — Trading costs, liquidity, capacity, operating feasibility

**Title:** $10mm is operationally feasible in liquid large-caps; fee income is modest

**Bullets:**
- Costs are **estimated** proportional bps **per side**, not observed TCA (state clearly).
- Design turnover ~27%/month one-way; at 5–25 bps/side, CAGR falls from 0.43458 to 0.41521 in-sample.
- Universe filters (price/ADV) target tradable names; $10mm is small vs large-cap ADV — capacity is not the binding constraint at this AUM.
- Illustrative fee 75 bps × $10mm ≈ **$75,000/year** — covers tools/time lightly; **not** a standalone firm viability case.
- Distinguish investment feasibility (can trade the book) from firm financial viability (need more AUM or other revenue).

**Chart:** `cost_sensitivity.png`.  
**Table:** `turnover.csv`.

---

## Slide 9 — Competitive advantages and honest differentiation

**Title:** Advantage is process control and honesty — not a claim that VQM is newly discovered

**Bullets:**
- **Not novel:** value, quality, momentum, and multifactor mixes are widely known and productized.
- **Distinctive packaging:** sector-relative ranks + eligible-universe sector-cap matching + within-sector equal weight + explicit lag/cost protocol.
- **Evidence for edge vs cheap ETFs is weak on the long ETF proxy** (+0.00609 CAGR vs SPY since 2014 after 5 bps/side).
- Short stock sample outperformance is real in our code output but **not** sufficient to claim a durable competitive advantage.
- Investor choice case: customization, transparency, and governance — not guaranteed excess return.

**What would support a true advantage later:** longer PIT database, stable net IR out-of-sample across regimes, and capacity-aware implementation shortfall below fee drag.

---

## Slide 10 — Investor Q&A and closing ask

**Title:** $10mm seed to run a documented process — with explicit invalidation conditions

**Bullets — anticipated objections:**
- *Why should this persist?* Factor premia may persist as risk/behavioral compensation, but crowding and regime shifts can erase them for years; we do not guarantee persistence.
- *Why not a factor ETF?* Longer ETF proxy barely beats SPY; choose us only if you value custom sector control/reporting — not for a proven fee-beating edge.
- *When does this lose money?* Momentum crashes, value drawdowns, quality lagging speculative rallies; max design DD −0.21980.
- *How much is market exposure?* Design beta ≈ 1.07 vs SPY; much of return is equity beta; active risk TE ≈ 7.4%.
- *Survive trading costs?* Yes in-sample through 25 bps/side (CAGR still 0.41521) — still a short sample.
- *What invalidates?* Persistent net underperformance after costs through a full market cycle; inability to obtain PIT fundamentals; capacity growth that forces higher impact.

**Close:** Ask for **$10mm** to operate the baseline book with monthly transparency. Commit to reporting gross/net returns, turnover, sector weights, and an annual review against SPY and the labelled ETF proxy.

---

## Formulas appendix (for annotated handout)

**Total return:** \(r_t = P^{\mathrm{adj}}_t/P^{\mathrm{adj}}_{t-1}-1\) (Yahoo Adj Close; do not double-count dividends).

**Percentile rank within sector:** rank ascending for V/Q/M raw scores so higher rank = more attractive; method = average, pct=True.

**Composite:** \(S=\sum_{k\in\{V,Q,M\}} w_k R^k\) with \(w=(1/3,1/3,1/3)\).

**One-way turnover:** \(\frac12\sum_i |w_{i,t}-w_{i,t^-}|\).

**Cost (per side bps \(c\)):** \(\big(\sum_i |w_{i,t}-w_{i,t^-}|\big)\cdot c/10^4\).

**CAGR:** \(\big(\prod(1+r_t)\big)^{252/N}-1\).

**Sharpe:** \(\bar r_{\mathrm{ex}}\cdot 252 / (\sigma_{\mathrm{ex}}\sqrt{252})\) with daily rf ≈ DGS3MO/100/252.

**Max DD:** min of \(W_t/\max_{s\le t}W_s-1\).

**TE / IR:** \(\sigma(r-r_b)\sqrt{252}\); \(\overline{r-r_b}\cdot 252/\mathrm{TE}\).
