# 10-Slide Investor Pitch Write-Up (CORRECTED)

Use with figures in `outputs/figures/` and tables in `outputs/tables/`. All stock results are **exploratory Yahoo / current-constituent** unless noted. Pre-correction CAGRs are retired.

---

## Slide 1 — Raising $10mm for a disciplined VQM process
**Title:** Raising $10 million for a systematic long-only value–quality–momentum book

**Bullets:**
- Objective: assets to manage ($10mm illustrative), not firm working capital.
- Process: sector-weight-matched, long-only, monthly, no leverage.
- Corrected evidence (short Yahoo panel): after 5 bps/side, CAGR 25.47% vs SPY 20.40% (Jul 2023–Dec 2025).
- Longer ETF factor blend: only +0.31%/yr vs SPY since 2014 — crowded factors.
- We do not claim novelty or durable 25% expected returns.

**Speaker notes:** Lead with mandate and honesty. Accounting was fixed; old ~43% figure was wrong. Biases remain.

**Chart:** `growth_of_10000.png`

---

## Slide 2 — Landscape: indexing, single-factor ETFs, multifactor
**Bullets:**
- Passive beta (SPY/VTI) is the default for cheap U.S. equity exposure.
- Single-factor ETFs (VLUE, QUAL, MTUM) package known premiums with low fees.
- Multifactor products already combine signals — we are not inventing VQM.
- Investor need: transparent rules, cost honesty, and risk controls—not another black box.

**Sources:** Provider factsheets; academic factor literature (Fama–French, Asness et al.) — cite as established, not our discovery.

---

## Slide 3 — Why value, quality, and momentum
**Bullets:**
- Value: compensation for cheap/riskier cash flows (hypothesis).
- Quality: profitable firms may earn persistent returns (hypothesis).
- Momentum: intermediate continuation with crash risk (hypothesis).
- Combining may diversify factor drawdowns — **testable**, not guaranteed.

**Formulas:** \(V=B/M\); \(Q=\mathrm{NI}/B_{avg}\); \(M=P_{t-21}/P_{t-252}-1\) (sessions).

---

## Slide 4 — Exact methodology
**Bullets:**
- Universe intent: top 500 eligible U.S. commons by historical mcap; **this build** uses current S&P panel (disclosed bias).
- Filters: unadjusted price ≥ $5; 20-session ADV ≥ $1mm; book > 0.
- Sector percentile ranks among top-N; equal-weight composite; top ~20%/sector.
- Sector weights match eligible-universe cap sectors **at rebalance** only.

**Table:** Methodology checklist from `strategy_spec.md`.

---

## Slide 5 — Risk controls and portfolio structure
**Bullets:**
- Long-only, no leverage; fully invested when targets exist.
- Sector-weight matching limits active sector bets vs the eligible universe at rebalance.
- Drift between months; ~28% monthly one-way turnover.
- Not market-neutral; not continuously sector-neutral.

**Chart:** holdings concentration from `rebalance_holdings_log.csv` (top names / sector mix).

---

## Slide 6 — Data and corrected performance
**Bullets:**
- Data: Yahoo prices/fundamentals + FRED yield RF + current constituents — **biased exploratory**.
- Accounting: \(R_p=w\cdot r\) then drift; next-close trades; costs scale NAV.
- After costs: **25.47%** CAGR vs SPY **20.40%**; after +75 bps fee: **24.53%**.
- Universe cap: **22.54%** — closer hurdle than SPY.
- Cumulative: VQM +76.0% vs SPY +58.8% (same window).

**Table:** Main results from READ_ME_FIRST §C.  
**Charts:** `design_cumret.png`, `vqm_drawdown.png`.  
**Limitation:** Not a 10-year PIT track record.

---

## Slide 7 — Robustness and limitations
**Bullets:**
- Sensitivities: weights, 10/20/30% selection, monthly/quarterly, cost grid, lags (`robustness_design.csv`).
- 2026 slice previously examined — **not** untouched OOS.
- Biases: survivorship, restatement, current sectors, annual quality fallback.
- Momentum drove much of the in-sample composite; quality lagged.

**Chart:** `cost_sensitivity.png`

---

## Slide 8 — Costs, liquidity, capacity, operating feasibility
**Bullets:**
- Assumed 5 bps/side (not measured TCA); 15 bps still leaves VQM ahead of SPY in-sample.
- ADV filter targets liquid names; $10mm trades are small vs large-cap ADV.
- Fee revenue: 0.75% × $10mm = **$75k/year** gross — ≠ firm viability.
- Capacity claims need holdings-level participation analysis on better data.

---

## Slide 9 — Differentiation (honest)
**Bullets:**
- Not a new factor discovery.
- Differentiation = transparent sector-weight matching, explicit timing/costs, and corrected accounting.
- Vs cheap factor ETF: only justified if process/mandate fit beats ~0.3%/yr ETF-proxy edge.
- Competitive advantage unproven until PIT data and longer clean sample exist.

**Chart:** `etf_proxy_cumret_long.png` (labelled separate).

---

## Slide 10 — Investor Q&A and ask
**Bullets:**
- Why persist? Unknown — factors can crowd and underperform for years.
- Why not an ETF? Cost and simplicity often win; we pitch process, not magic alpha.
- When lose? Momentum crashes, value traps, quality failures; see drawdown chart.
- How much market? Beta ≈ 1.09 vs SPY in-sample.
- Survive costs? Yes in this short sample at 5–15 bps; not proof forever.
- Invalidate? Clean PIT data wiping the edge; capacity binding; accounting/process errors.

**Ask:** Illustrative $10mm mandate to run the published rules with full reporting and bias disclosure.

**Close:** Accurate research over flattering stories — corrected numbers, labelled limits, clear next data upgrade (Sharadar/CRSP).
