# HW2 Investor Pitch — 7-Slide Outline (complementarity framing)

**Central proposition:**  
A systematic large-cap equity mandate that **balances valuation, profitability, and price momentum**, while controlling sector allocations relative to its eligible universe.

**Product throughout:** stock-level long-only **VQM**  
**Ask:** illustrative **$10mm** AUM, **conditional** on stronger data validation and operational readiness  
**Hypothesis:** combining different information may reduce dependence on any single selection criterion (**complementarity**)

**Research stance:** Keep VQM. The backtest is one piece of evidence evaluating a pre-existing rationale — not a contest that mechanically chooses the recent sample winner. The sample neither proves the diversification case nor gives enough reason to abandon it for momentum-only.

**Chart footnote (all stock-performance figures):**  
*Exploratory backtest: current constituents and restated fundamentals; survivorship and look-ahead risks.*

---

## Slide map

| # | Content | Plot / table |
|---|---------|--------------|
| 1 | Investor need + conditional ask | (process strip) |
| 2 | Why combine — complementarity rationale | landscape + Asness et al. cite |
| 3 | Implementation (composite, selection, sectors, execution) | methodology |
| 4 | Evidence — trade-offs vs alternatives | `AF_comparison_cumret.png` / `growth_of_10000.png` |
| 5 | Do holdings actually differ? | `holdings_overlap_VQM_Mom.png`, `portfolio_characteristic_exposures.png`, `sleeve_active_corr.png` |
| 6 | Limitations + implementation economics | `vqm_drawdown.png`; ADV table; **fee concern once** |
| 7 | Q&A, milestones, closing ask | — |

---

## Slide 1 — Investor need and conditional ask

**Title:** Balancing valuation, profitability, and momentum in large-cap stock selection

**Investor need:** An allocator wants **systematic stock selection without making one characteristic the sole driver** of the portfolio — while remaining fully invested in equities and keeping sector weights close to the eligible universe.

**Product:** Long-only U.S. large caps; equal-weight composite of value, profitability (quality proxy), and momentum ranks within sector; sector targets matched to eligible universe; monthly; next-close execution.

**Ask:** Illustrative **$10 million** AUM — **conditional** on point-in-time validation and operational readiness. Current research does **not** establish readiness to deploy.

---

## Slide 2 — Economic rationale (complementarity)

**Hypothesis:** Each signal contributes different information; combining them is intended to **reduce dependence on one investment style**.

**Literature support (rationale to investigate — not validation of this formula):**  
Asness, Moskowitz & Pedersen, *Value and Momentum Everywhere* (Journal of Finance, 2013) — documents diversification benefits from combining value and momentum across markets ([AQR](https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere)).

**Important distinctions:**
1. Adding signals ≠ simply cutting risk with cash. Value/profitability change **which businesses** you own while staying fully invested.
2. Our “quality” signal is a **profitability proxy** (annual NI / average book) — not comprehensive financial strength (no direct leverage/safety/payout screens). Broader quality research uses multiple characteristics (e.g., AQR quality literature).
3. Equal-weight composite \(S_i=(V_i+Q_i+M_i)/3\) rewards **overall** scores; a name can offset weak profitability with strong value and momentum. Say: *we balance valuation, profitability, and price momentum* — not “every holding is cheap, high-profitability, and trending.”

**Equal weights:** a simple, transparent starting choice that avoids fitting weights to this short sample — not claimed as optimal.

**Landscape (cited):** broad beta (SPY); iShares VLUE / QUAL / MTUM (0.15% ER, fact sheets mid-2026); multifactor products already exist.

---

## Slide 3 — Implementation

Universe filters; formulas \(V=B/M\), \(Q=\mathrm{NI}^{annual}/\bar{B}\) (profitability proxy), \(M=P_{t-21}/P_{t-252}-1\); sector ranks → composite → top ~20%/sector; sector weights = eligible-universe cap weights at rebalance; next-close execution.

**Note:** Sector controls apply to VQM **and** the single-factor comparators in our A–F study — they do **not** uniquely distinguish VQM from momentum-only.

---

## Slide 4 — Evidence: risk–return trade-offs (design window)

After ~5 bps/side approx costs:

| | CAGR | Vol | Sharpe | Max DD |
|--|------|-----|--------|--------|
| VQM | 26.71% | 18.04% | 1.13 | −22.87% |
| Momentum-only | 35.64% | 21.18% | 1.32 | −26.36% |
| Universe cap-wt | 22.54% | 15.39% | 1.08 | −19.49% |
| SPY | 20.40% | 15.51% | 0.96 | −18.76% |

**Reading:** VQM showed **lower observed volatility and maximum drawdown** than momentum-only, with lower return and Sharpe. Vs universe-cap: higher return with higher vol and deeper DD; modest Sharpe lift. An investor may accept lower returns in a momentum-led period to avoid making momentum the sole selection criterion — that preference is legitimate; whether *this* implementation delivers the desired diversification still needs evidence (Slide 5).

**Plot:** `AF_comparison_cumret.png` or `growth_of_10000.png`

**Unresolved question (carry to close):** Does this trade-off persist across environments — and does it justify cost?

---

## Slide 5 — Complementarity checks (holdings & exposures)

**Holdings overlap (avg across 30 rebalances):**

| Pair | Jaccard (names) | Weight overlap |
|------|-----------------|----------------|
| VQM vs Momentum | 42.3% | 59.7% |
| Momentum vs Value | 4.9% | 9.9% |
| Value vs Quality | 0.9% | 1.1% |

VQM is not identical to momentum (~40% of names differ; ~40% of weight is outside the momentum book). Value and momentum sleeves hold largely different businesses.

**Characteristic exposures (portfolio-weighted avg sector percentile ranks):**  
VQM ≈ value 0.50 / profitability 0.65 / momentum 0.80 — balanced but **momentum-tilted**; not “all three high for every name.”

**Active-return correlations (vs SPY residual):** Value–Momentum ≈ **0.01**; Quality–Momentum ≈ **0.18**; VQM–Momentum ≈ **0.74** (composite still inherits momentum). Suggests the single sleeves are not the same active bet; the composite still leans on momentum in this sample.

**Plots:** `holdings_overlap_VQM_Mom.png`, `portfolio_characteristic_exposures.png`, `sleeve_active_corr.png`

---

## Slide 6 — Limitations and implementation economics

**One limitations block:**
- Short sample; current constituents; restated fundamentals; current sectors; profitability proxy (not full quality)
- 2026 previously examined — not untouched validation
- Cost model = proportional approximation
- Lower vol/DD vs momentum is an **observed sample feature**, not an isolated “momentum crash” study (classic crash literature does not map 1:1 onto this long-only book)

**Fee (state once):** A rationale for VQM does **not** automatically justify charging **75 bps**. After-fee Sharpe (~1.09) is essentially flat vs universe-cap (~1.08) in this sample.

**$10mm sizing:** position/ADV median 0.026%, max 5.59%; rebalance trade/ADV median 0.001%, max 5.59%. Feasibility looks plausible, not proven.

**Plot:** `vqm_drawdown.png`

---

## Slide 7 — Q&A, milestones, close

**Funding:** stock-level VQM mandate (not ETF product; not working capital).  
**Keep VQM** because the case is diversification of **investment criteria under uncertainty** — not because it beat every sleeve in this window.  
**Milestones:** PIT data rebuild; same A–F + overlap/exposure tests; TCA pack.  
**Close:** illustrative $10mm, conditional on milestones.

---

## Appendix only

Superseded CAGRs, bug history, test commands → `appendix_research_notes.md`  
High-precision CSVs → `outputs/tables/`
