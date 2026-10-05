# Investor Pitch — 7 Slides (complementarity framing)

**Proposition:** A systematic large-cap equity mandate that balances **valuation**, **profitability**, and **price momentum**, while controlling sector allocations relative to its eligible universe.

**Ask:** illustrative $10mm AUM, conditional on stronger validation — not claimed ready to deploy.  
**Hypothesis:** complementarity — combining different information may reduce dependence on any single selection criterion.

**Chart footnote:** *Exploratory backtest: current constituents and restated fundamentals; survivorship and look-ahead risks.*  
**Appendix:** `reports/appendix_research_notes.md` · high-precision tables in `outputs/tables/`

---

## Slide 1 — Investor need and conditional $10mm ask

**Title:** Systematic large-cap selection balancing three stock-selection criteria

**Bullets:**
- **Need:** systematic stock selection that does **not** make one characteristic the sole driver — while staying fully invested in equities.
- **Product:** long-only U.S. large caps; balance valuation, profitability, and momentum within sector; sector weights matched to the eligible universe at rebalance.
- **Objective:** raise **assets** ($10mm illustrative) — not working capital.
- **Ask:** $10mm **conditional** on point-in-time data validation and operational readiness.
- **Status:** design is defined; readiness to deploy is **not** established on current exploratory evidence.

**Visual:** short process strip (signals → composite → sector-matched book).

---

## Slide 2 — Why combine? Complementarity

**Title:** Different information — intended to reduce style dependence

**Bullets:**
- **Value** (\(B/M\)): valuation information (Fama–French tradition).
- **Profitability proxy** (annual NI / average book): part of the broader “quality” idea — **not** full balance-sheet strength / leverage / safety screens.
- **Momentum** (12−1 sessions): price continuation with known cyclicality.
- **Rationale to investigate:** *Value and Momentum Everywhere* (Asness, Moskowitz & Pedersen, 2013) documents diversification benefits from combining value and momentum across markets — a reason to study combinations beyond whichever factor won a short sample. It does **not** validate this long-only ranking formula. ([AQR](https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere))
- Adding signals ≠ parking cash: value/profitability change **which businesses** you own.
- Composite \(S=(V+Q+M)/3\) balances overall scores; names need not pass three separate hurdles.
- Equal weights: transparent starting point — **not** fit to this sample.
- **Landscape:** SPY; iShares VLUE / QUAL / MTUM at 0.15% ER (fact sheets, mid-2026).

---

## Slide 3 — Implementation rules

**Title:** How the mandate is built

**Bullets:**
- Filters: ~top 500 mcap; price ≥ $5; full 20-session ADV ≥ $1mm; positive book.
- Ranks within sector → equal-weight composite → top ~20% / sector.
- Sector weights = eligible-universe **cap** weights **at rebalance** (also used by single-factor comparators — not unique to VQM).
- Execution: month-end signal → **next session close**.
- Analysis costs: 5 bps/side proportional approximation; 75 bps fee only on after-fee lines.

**Visual:** methodology flowchart.

---

## Slide 4 — Sample evidence: risk–return trade-offs

**Note:** After estimated trading costs of 5 bps per side; before management fees.

**Title:** What the exploratory window illustrates (Jul 2023 – Dec 2025)

| Portfolio | CAGR | Vol | Sharpe | Max DD |
|-----------|------|-----|--------|--------|
| VQM | 26.71% | 18.04% | 1.13 | −22.87% |
| Momentum-only | 35.64% | 21.18% | 1.32 | −26.36% |
| Universe cap-weight | 22.54% | 15.39% | 1.08 | −19.49% |
| SPY | 20.40% | 15.51% | 0.96 | −18.76% |

**Bullets:**
- Vs momentum: **lower observed volatility and maximum drawdown**; lower return and Sharpe.
- Vs universe-cap: higher return; higher vol and deeper drawdown; modest Sharpe lift.
- Accepting lower return in a momentum-led period to avoid a single selection criterion is a legitimate preference — whether **this** book delivers the intended diversification is a separate empirical question (next slide).
- Turnover ≈ **25.5%/month** one-way **excluding** initial formation.

**Chart:** `outputs/figures/AF_comparison_cumret.png` or `growth_of_10000.png`  
**Unresolved:** Does the trade-off persist across environments, and does it justify cost?

---

## Slide 5 — Do the holdings and exposures actually differ?

**Title:** Complementarity checks — overlap, exposures, active correlations

**Holdings overlap (30 rebalances, average):**
- VQM vs Momentum: Jaccard **42%** of names; weight overlap **60%** → partially distinct book.
- Momentum vs Value: weight overlap **10%** → largely different businesses.
- Value vs Quality: weight overlap **~1%**.

**Exposures (portfolio-weighted avg sector percentile ranks):**
- VQM ≈ value **0.50** / profitability **0.64** / momentum **0.80** — momentum-tilted with additional profitability exposure; not “every name scores high on all three.”

**Active-return correlations (vs SPY):**
- Value–Momentum ≈ **0.01**; Quality–Momentum ≈ **0.18**; VQM–Momentum ≈ **0.74**.

**Charts:**  
`holdings_overlap_VQM_Mom.png` · `portfolio_characteristic_exposures.png` · `sleeve_active_corr.png`

**Takeaway:** Single sleeves are not the same active bet; the composite still leans on momentum in this sample. Evidence is supportive of *investigating* complementarity — not proof it is delivered for a fee.

---

## Slide 6 — Limitations and $10mm economics

**Title:** What remains open — and can $10mm trade?

**Limitations (one block):**
- Short sample; current constituents; restated fundamentals; current sectors.
- Profitability proxy ≠ comprehensive quality.
- Lower vol/DD vs momentum is an observed sample feature — **not** an isolated momentum-crash experiment.
- 2026 previously examined; cost model is an approximation.

**Fee (once):** A rationale for VQM does **not** automatically justify **75 bps**. After-fee Sharpe (~1.09) ≈ universe-cap (~1.08) here.

**Liquidity @ $10mm:**
- Position/ADV: median **0.026%**, max **5.59%**
- Rebalance trade/ADV (ex-initial): median **0.001%**, max **5.59%**

**Chart:** `vqm_drawdown.png`

---

## Slide 7 — Questions, milestones, closing ask

**Title:** Conditional allocation to the stock mandate

**Q&A:**
- *What am I funding?* Stock-level VQM — not an ETF substitute, not working capital.
- *Why not just momentum?* Preference against single-criterion selection can be rational even when momentum won this window; implementation evidence is partial.
- *Ready?* Not on current evidence.
- *Sector edge vs momentum sleeve?* Both use the same sector-control design in our tests.

**Milestones before any live $10mm:** PIT membership + as-reported fundamentals; rebuild; re-run A–F **and** overlap/exposure tests; TCA pack.

**Close:** Keep VQM as the product. Seek illustrative **$10mm**, **conditional** on milestones. The case is diversification of investment criteria under uncertainty; this backtest neither proves it nor warrants abandoning it for its recent winner.
