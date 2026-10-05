# HW2 Investor Pitch — 7-Page Deck Outline

**Course:** B9339 Systematic Investment Strategies (Fall 2026)  
**Assignment:** Investor pitch (presentation) — raise assets and/or working capital  
**Our objective (stated on p.1):** Raise illustrative **$10,000,000 AUM** to manage a systematic long-only U.S. equity process (not firm working capital).  
**Research decision (after corrections):** **SIMPLIFY** — do not pitch a fee-justified stock-level VQM product on the current evidence; present an honest illustrative study.

**Data label on every stock chart:** `BIASED_EXPLORATORY_YAHOO_CURRENT_CONSTITUENT_PANEL`  
**Design window:** 2023-07-03 → 2025-12-31 (628 daily observations)  
**2026 slice:** previously examined — not untouched validation  
**Costs:** proportional L1 approximation at 5 bps/side (not exact lot accounting)  
**Figures/tables:** `outputs/figures/`, `outputs/tables/` (≥5 decimal digits in CSVs)

---

## Assignment coverage map

| Required element (PDF) | Where in this deck |
|------------------------|--------------------|
| Clear pitch objective | Page 1 |
| Landscape / context | Page 2 |
| Main idea + technical method + results | Pages 3–4 |
| Innovation (if any) | Page 5 |
| Competitive advantage(s) | Page 5 |
| Robustness of evidence | Page 6 |
| Feasibility (costs, liquidity, capacity, capital) | Page 6–7 |
| Anticipate Q&A | Page 7 |
| Summary preferably first | Page 1 |
| Formulas explained | Pages 3–4 |
| Reproducible / ≥5 decimals | Page 1 footer + appendix CSV cites |

---

## Page 1 — Summary & ask (assignment: objective + first-page summary)

**Title:** Raising $10mm for a systematic long-only U.S. equity mandate — with an honest research conclusion

**Objective (one sentence):**  
This pitch seeks **$10 million of assets under management** to run a published, rules-based long-only process. It is **not** a request for start-up working capital.

**One-paragraph summary (all questions):**  
We studied whether adding **value** and **quality** to equity **momentum** (VQM) improves a monthly, sector-weight-matched stock book enough to justify extra data, complexity, and a management fee. After fixing accounting and data-handling bugs, corrected Yahoo-panel results show VQM after 5 bps/side CAGR **0.26712** vs SPY **0.20402**, universe-cap **0.22539**, and momentum-only **0.35640**. Momentum dominates the combination in-sample; quality lags. Data remain biased (current constituents, restated Yahoo fundamentals). **Decision: SIMPLIFY** — do not claim a paid stock-selection edge; pitch transparency and process, or a labelled factor-ETF sleeve as a *different* product.

**Headline numbers (design; after 5 bps/side unless noted; ≥5 decimals in tables):**

| Sleeve | CAGR | Ann. vol | Sharpe | Max DD | 1-way turnover |
|--------|------|----------|--------|--------|----------------|
| F VQM | 0.26712 | 0.18045 | 1.13333 | −0.22866 | 0.27630 |
| C Momentum-only | 0.35640 | 0.21179 | 1.31642 | −0.26359 | 0.27495 |
| A Universe cap-wt | 0.22539 | 0.15388 | 1.08206 | −0.19487 | 0.02971 |
| SPY (ER embedded) | 0.20402 | 0.15514 | 0.96085 | −0.18755 | — |
| F VQM after +75 bps fee | 0.25765 | 0.18044 | 1.09175 | −0.22944 | 0.27630 |

**Ask:** $10mm illustrative mandate to run **published rules** with full reporting — framed as a research-backed *process* pitch, not as proven alpha for sale.

**Footer:** Superseded pre-correction CAGRs (~43.5% / ~81.6% / ~14.7%) must not be cited. Reproduce: `pytest tests/`; `python scripts/run_decision_study.py`.

**Visual:** `growth_of_10000.png` (VQM vs momentum vs SPY).

---

## Page 2 — Landscape (assignment: available strategies in category)

**Title:** Where this sits vs indexing, single-factor ETFs, and multifactor products

**Bullets:**
- **Passive beta:** SPY/VTI — lowest-cost U.S. equity exposure; our primary market benchmark.
- **Single-factor ETFs:** VLUE (value), QUAL (quality), MTUM (momentum) — liquid, transparent, low fee; embed known premiums.
- **Multifactor / quant SMAs:** Many products already combine V+Q+M; we are **not inventing** the factors.
- **Our category:** Long-only, monthly-rebalanced, sector-aware stock selection among large liquid U.S. names — closer to a quantified SMA sleeve than to market-neutral / residual stat-arb.
- **Commonality:** All compete for the same equity risk premium; differences are rules, cost, capacity, and honesty of track record.
- **Our research question (not a marketing slogan):** Does V+Q add enough *beyond momentum and the eligible universe* to justify fundamentals data + fee?

**Visual:** Simple three-column landscape diagram (Index | Factor ETFs | Rules-based stock VQM).

**Speaker note:** Landscape is required; keep it short so method/results get time.

---

## Page 3 — Main idea & methodology (assignment: technical details + formulas)

**Title:** Frozen baseline — long-only VQM with sector weights matched at rebalance

**Idea in one line:** Select stocks with attractive within-sector value, quality, and momentum ranks; hold a long-only book whose sector weights match the eligible universe at each month-end rebalance.

**Formulas (must show):**
- Value: \(V = B / M\) (book equity / contemporaneous market cap)
- Quality (frozen Yahoo baseline): \(Q = \mathrm{NI}^{\mathrm{annual,\,vendor}} / \bar{B}\) (period-matched average book; **labelled annual**, not silent TTM)
- Momentum: \(M = P_{t-21}/P_{t-252} - 1\) (trading-session endpoints)
- Composite: equal-weight sector percentile ranks of \(V,Q,M\); select top ~20% within sector
- Portfolio return: \(R_p = \sum_i w_i r_i\) (beginning-of-period weights), then drift; trade at **next session close**
- Cost approx: \(\mathrm{cost} \approx (\mathrm{L1}/2) \times 2 \times \mathrm{bps}\) → labelled **proportional approximation**, not exact cash lots

**Implementation rules:**
- Universe intent: top 500 eligible by mcap; **this build** = current S&P research panel (bias disclosed)
- Filters: price ≥ $5; ADV requires **all 20** sessions; book > 0; usable (non–constant_latest) shares
- Execution: signal month-end close → trade next close
- Quality treatment reported each rebalance (annual weight ≈ 100% on Yahoo; TTM too thin)

**Visual:** Process flowchart (filters → ranks → select → sector targets → next-close trade).

**Cite:** `strategy_spec.md`, `baseline_freeze.json`.

---

## Page 4 — Investment results (assignment: characteristics of results)

**Title:** Corrected A–F comparison — what actually drove performance

**Separate return layers (say this out loud):**
1. Gross (0 trading cost)
2. After trading-cost approximation (5 bps/side)
3. After trading cost + 75 bps illustrative management fee
4. SPY: ETF expense ratio already in Adj Close — **do not subtract ER again**

**Key results (design, after 5 bps/side):**
- VQM beats SPY and universe-cap on this short biased sample (CAGR 0.26712 vs 0.20402 / 0.22539).
- **Momentum-only beats VQM** (0.35640 vs 0.26712); Sharpe 1.31642 vs 1.13333.
- Value-only ≈ mid (0.25009); quality-only **lags** (0.19360) and trails SPY on CAGR.
- Sector-equal universe (B) ≈ 0.21620 — within-sector equal-weighting alone does not explain VQM.
- Turnover: VQM ≈ 27.6%/month one-way ≈ momentum; universe-cap ≈ 3.0%.
- Concentration risk: calendar-year VQM−momentum spread largest in **2025** (−14.55% points) — single-year dominance risk.
- Previously examined 2026 slice: report only as inspected history, not validation.

**Decision line on this page:** Adding V+Q did **not** improve the book enough vs momentum (or vs complexity) on this evidence → **SIMPLIFY**.

**Visuals:** `AF_comparison_cumret.png` / `design_cumret.png`; table from `AF_comparison_summary.csv`.

**Optional inset:** Ex-post vol-matched diagnostic labelled **NOT EXECUTABLE** (`vol_match_diagnostic.json`).

---

## Page 5 — Innovation & competitive advantage (assignment: both; be honest)

**Title:** What is (and is not) innovative — and what advantage we can actually claim

**Innovation (if any) — honest answer:**
- **No new factor discovery.** Value, quality, and momentum are established.
- Process choices that are *transparent*, not novel: sector-weight matching at rebalance; session-based 12−1; next-close execution; explicit quality-mode labelling; halt-flagged missing returns.
- Research process innovation for the course: corrected portfolio accounting + controlled A–F horse race answering a precise economic question (fee/complexity justification), not curve-fitting for a pretty CAGR.

**Competitive advantages — only what evidence supports:**
- **Supported:** Clear rules; reproducible code; corrected math; explicit cost/fee layers; ADV-based $10mm sizing; full bias disclosure.
- **Not supported:** Durable alpha; capacity at large AUM; novelty vs multifactor ETFs; a fee that investors should pay *because* VQM beats momentum.
- **ETF proxy (different product):** Equal-weight VLUE/QUAL/MTUM monthly since ~2014 ≈ +0.31%/yr vs SPY after approx costs — crowded, cheap factors. Use only as landscape/context, **not** as stock-strategy track record.

**Speaker note:** Assignment asks for innovation/advantage; empty honesty scores better than invented edge.

---

## Page 6 — Robustness & feasibility (assignment: robustness + costs/liquidity/capacity)

**Title:** How fragile is the evidence — and can $10mm actually trade?

### Robustness
- **Calculation correctness:** Fixed (portfolio return before weight update; missing returns flagged; shares availability lag; no gap→annual NI; ADV full 20 obs; no pre-trade return accrual; tests in `tests/test_accounting.py`).
- **Dataset adequacy:** Still **inadequate** for a PIT stock claim — current constituents, restated Yahoo fundamentals, current sectors, short sample, annual quality fallback.
- Sensitivities: cost grid, selection %, rebalance frequency (`robustness_design.csv` if presented); excluding winners = sensitivity only, not redesign.
- Two judgments kept separate: *math correct?* vs *data adequate for the claim?*

### Feasibility ($10mm AUM)
- Assumed trading cost 5 bps/side (approximation); turnover ~28%/month implies material cost drag vs universe-cap.
- Illustrative fee 75 bps × $10mm = **$75,000/year** gross revenue ≠ standalone firm economics (we are **not** pitching working capital).
- Position vs ADV at $10mm: median position/ADV ≈ **0.000256**; p95 ≈ **0.00136**; max ≈ **0.0559** (`adv_position_sizing_10mm.csv`). Operational trading at $10mm looks feasible for large-caps; **separate** from whether the idea earns a fee.
- Capacity at scale: not demonstrated; needs participation analysis on better data.

**Visuals:** `vqm_drawdown.png`, `cost_sensitivity.png`; ADV summary callout.

---

## Page 7 — Anticipated Q&A and close (assignment: Q&A)

**Title:** Questions we expect — answered before you ask

| Likely question | Answer |
|-----------------|--------|
| Why not just buy MTUM / SPY? | On this sample momentum-only beat VQM; cheap ETFs often win on net-of-fee simplicity. We pitch rules + disclosure, not magic. |
| Why should I pay 75 bps? | **Current evidence does not clearly support it** for stock VQM vs momentum or universe benchmarks after costs. Fee is illustrative for the mandate math. |
| Is this out-of-sample? | Design ends 2025-12-31; 2026 was **previously examined** — not untouched validation. |
| Survivorship? | Yes — current S&P panel applied historically. Label remains biased exploratory. |
| Why did accounting change? | Old engine updated weights before computing \(R_p\) (50/50 ±10% wrongly gave +1%). Fixed; old ~43% CAGR retired. |
| Will factors keep working? | Unknown; factors crowd and can underperform for years. |
| When do you lose money? | Momentum crashes, value traps, quality failures; max DD VQM ≈ −22.9% after costs. |
| How much market risk? | Beta ≈ 1.08 vs SPY (VQM after costs). |
| Working capital? | Out of scope — pitch is **AUM only**. |
| What would change your mind? | Licensed PIT data (historical membership, as-reported fundamentals with availability dates, delistings) and the **same** A–F table still showing VQM additivity after costs. |

**Close / ask:**  
Seeking **$10mm** to run the published long-only rules with transparent reporting. Research decision: **SIMPLIFY** the investment claim — present an illustrative process study (or a separately labelled VLUE/QUAL/MTUM ETF sleeve), not a fee-justified multifactor alpha product on Yahoo evidence.

**Appendix cue (if asked):** Repo `equity_multifactor`; `reports/STRATEGY_DECISION.md`; high-precision CSVs under `outputs/tables/`.

---

## Speaker timing (≈10–12 min)

| Page | Minutes |
|------|---------|
| 1 Summary & ask | 1.5 |
| 2 Landscape | 1.0 |
| 3 Method | 2.0 |
| 4 Results / SIMPLIFY | 2.5 |
| 5 Innovation / advantage | 1.0 |
| 6 Robustness / feasibility | 2.0 |
| 7 Q&A + close | 1.5 |

---

## Do / don’t for the live deck

**Do**
- State objective = raise **$10mm AUM** on page 1
- Show formulas and next-close / \(R_p=\sum w r\) accounting
- Report gross / after-cost / after-fee distinctly
- Label data biases and SIMPLIFY decision
- Cite ≥5-decimal tables when numbers are challenged

**Don’t**
- Cite pre-correction ~43% / ~81% / ~14.7%
- Claim novelty, durable alpha, or demonstrated capacity
- Treat ETF proxy as the stock track record
- Treat 2026 as untouched OOS
- Redesign the strategy by dropping winners after seeing results
