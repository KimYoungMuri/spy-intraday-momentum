# B9339 Systematic Investment Strategies — Homework Assignment #1

**Course:** B9339, Professor Achilles Venetoulias, Fall 2026  
**Due:** Tuesday, September 22, 2026, 5:00pm EST  
**Group members:** _[fill in ≤3 names]_  
**AI coding platform:** Cursor (Python). Brief prepared with ChatGPT from the homework/paper (ChatGPT model unknown).  
**Paper:** Zarattini, Aziz, Barbon (this version 22 Sep 2025), *Beat the Market…*  
**Data:** Instructor Bloomberg file `hw1.spy.20250313-20251201.intra-30m.xlsx`  
**Results timestamp:** from `outputs/tables/results_payload.json` after `python scripts/run_analysis.py`

---

## Summary of answers (Step 3 deliverables)

1. **AI development.** We used Cursor to generate a from-scratch Python replicator of the paper’s three nested variants (opposite-band stop; current-band+VWAP stop; +volatility sizing). Authors’ code was not used. Independent reference arithmetic and 14/14 unit tests passed; real sessions 2025-07-03 and 2025-10-10 matched production bands/VWAP/sizing exactly. Main limitations: no true open in the workbook (open-proxy adaptation) and inferred bar-start timestamps.

2. **Findings.** On the common window **2025-04-02 → 2025-12-01** (168 sessions after 14-day band warm-up), net of paper costs ($0.0035+$0.001/share): **A +3.594%** (Sharpe **0.82958**), **B +4.459%** (Sharpe **0.93934**), **C +11.057%** (Sharpe **1.09023**). Matched **SPY buy-and-hold on the supplied price series** returned **+21.928%** (Sharpe **1.49478**). Tighter stops and vol-sizing improved the active book relative to A, but did not beat buy-and-hold in this strong SPY sample. Half-days flatten correctly at 13:00. Delay-fill and higher slippage materially reduce C’s edge.

3. **Strategy assessment.** The idea—trade only after unusually large same-clock moves from the open, with dynamic stops and vol targeting—is economically coherent as a time-series momentum / imbalance-persistence hypothesis and is laptop-computable, but live operation needs reliable clocks, shorting, fills, and risk controls. It is most plausible in persistent intraday-trend regimes and most fragile in chop/whipsaw, coarse sampling, and high costs. Eight months cannot establish investor suitability.

4. **Paper critique.** The sequential A→B→C design is clear and useful. The headline **19.6% / Sharpe 1.33** figures are historical backtest references for 2007–early 2024, not targets for our sample. Average-absolute-move bands are heuristics, not significance tests; VWAP/execution and cost realism remain central; pattern/weekday/RSI analyses face multiple-testing and proxy issues. We would demand stricter fill/state conventions, uncertainty, and OOS protocol.

---

## 1. AI development and accuracy (Step 3.1)

### 1.1 Platform choice

We chose **Cursor** because this homework requires reading long PDFs, generating inspectable code, editing after failed tests, and running backtests in one workspace. We chose **Python** for Excel ingestion (`pandas`/`openpyxl`), explicit vector/table transforms, `pytest`, and matplotlib figures. These are workflow reasons, not a claim of global superiority over Matlab/R/Excel.

The long implementation brief in this chat was prepared with **ChatGPT** from the homework and paper; that brief is an input, not the coding platform. ChatGPT’s model id was not recorded.

### 1.2 What we replicated and omitted

**Replicated (core):**

- Time-of-day **Noise Area** from 14-day average absolute open-to-endpoint moves, with overnight gap adjustment via \(\max(O,C_{d-1})\) / \(\min(O,C_{d-1})\) (paper §3).
- Semi-hourly decisions; flatten by session close (13:00 on half-days).
- **Variant A:** opposite-band exit/reversal; 1× BOD equity.
- **Variant B:** stop at \(\max(U,\mathrm{VWAP})\) / \(\min(L,\mathrm{VWAP})\); 1×.
- **Variant C:** B + daily vol targeting \(\sigma_{\mathrm{target}}=2\%\), leverage cap 4× (paper eqs. for shares).
- Costs: $0.0035 commission + $0.001 slippage per share per side.
- SPY buy-and-hold benchmark on matched dates.

**Omitted from core (with reasons):**

| Thread | Reason |
|--------|--------|
| Daily candlestick patterns (NR4, etc.) | 30-minute endpoints do not reconstruct true daily high/low |
| Dealer gamma / options | Not in workbook; requires options exposure assumptions |
| VIX regime / cross-asset | VIX and other markets not supplied |
| Exhaustive weekday filters | ~168 days → weak subgroup power (optional appendix skipped) |
| Authors’ public Matlab/Python | Forbidden as primary replicator; not needed after independent checks |

### 1.3 Main formulas (as implemented)

For each prior session \(d-i\) and availability clock \(h\):

\[
a_{d-i,h}=\left|\frac{P_{d-i,h}}{O_{d-i}}-1\right],\quad
m_{d,h}=\frac1{14}\sum_{i=1}^{14}a_{d-i,h}
\]

\[
U_{d,h}=\max(O_d,C_{d-1})(1+\mathrm{VM}\,m_{d,h}),\quad
L_{d,h}=\min(O_d,C_{d-1})(1-\mathrm{VM}\,m_{d,h})
\]

with default \(\mathrm{VM}=1\). Here \(m\) is an **average absolute move**, not a standard deviation.

**Workbook adaptation:** \(O_d\) is the first regular endpoint price (`open_proxy`), known at 10:00 under our timing assumption—not a verified 09:30 open. First ordinary entry is therefore at the next endpoint (typically 10:30 availability). Gap adjustment then spans overnight **plus** the first half-hour.

**VWAP proxy** (interval volumes \(v_j\), endpoint prices \(P_j\)):

\[
\mathrm{VWAP}^{proxy}_{d,h}=\frac{\sum_{j\le h}P_{d,j}v_{d,j}}{\sum_{j\le h}v_{d,j}}
\]

**Sizing (C):** \(\sigma_d=\mathrm{stdev}\{r_{d-14},\ldots,r_{d-1}\}\) (sample, `ddof=1`),  
\(\mathrm{exposure}_d=\min(4,0.02/\sigma_d)\),  
\(\mathrm{shares}_d=\lfloor E_{d-1}\cdot\mathrm{exposure}_d/O_d\rfloor\). For A/B, exposure\(=1\).

**B/C operational entry:** long only if \(P>\max(U,\mathrm{VWAP})\); short only if \(P<\min(L,\mathrm{VWAP})\); else flat. This avoids same-bar entry/instant-stop loops and is labeled as our reading of the combined entry/stop prose.

**Execution:** observe endpoint → idealized fill at that endpoint → earn only later price changes. Costs deducted explicitly (\(0.0045\times\) shares traded); reversals trade \(2Q\).

### 1.4 Iterations and accuracy

See `logs/experiment_log.md`. Material fixes: half-day test assertion; clarified delay-fill state machine. Final verification: **14/14 pytest**; independent `reference_checks` vs production on 2025-07-03 and 2025-10-10: **zero numerical difference** for bands, VWAP, and C share count. AI performed these checks; the student should spot-check the exported traces before submission.

What AI did well: translating paper formulas into a testable state machine; systematic audit scaffolding. What still needs human review: economic interpretation, course linkages, group identity fields, and whether instructor intends a different timestamp/open convention.

---

## 2. Data and findings (Step 3.2)

### 2.1 Data provenance and audit

Three sheets: `AV.Clean` (main intraday), `BBRG.Intraday` (raw compare), `BBRG.Daily` (closes/volumes from 2025-02-20). Intraday coverage **2025-03-13–2025-12-01** (182 sessions)—we **include December 1** despite the assignment’s approximate “March–November” wording, and also report a through-November sensitivity.

**Volume:** `Volume, AV` **decreases within sessions** (1,181 decreases)—treated as **per-interval**, not cumulative. Do not difference. Closing 16:00 rows often look like reconciliation residuals; excluded from trading-time VWAP. Seven dates fail full-day volume reconciliation (see `data/processed/audit_report.json`); prices retained.

**Half-days 2025-07-03 and 2025-11-28:** labels continue after 13:00 with repeated prices and zero afternoon volumes; 16:00 holds a large residual. **Removed from tradable/band history**; flatten once at 13:00.

**Opens:** no Open field anywhere. Main run uses open-proxy adaptation (above).

**Closes:** intraday 16:00 vs daily close within $0.0003 on all days (73 exact). Daily series used for prior close and \(\sigma_d\).

### 2.2 Evaluation window

- Band warm-up: 14 prior **intraday** sessions → first eligible date **2025-04-02**.
- Daily \(\sigma\) warm-up: daily sheet prehistory from 2025-02-20 supplies 14 prior returns by the first intraday date.
- Core sample: **168** sessions, 2025-04-02 through 2025-12-01.
- Initial equity: $100,000. Risk-free = 0.

### 2.3 Core results (net of baseline costs)

Figures: `outputs/figures/normalized_wealth.png`, `drawdown_C.png`, `monthly_C.png`, `leverage_C.png`. Machine-readable: `outputs/tables/core_summary.csv` (5-dp display: `core_summary_display5.csv`).

| Strategy | End equity | Total return | Ann. geom. \((E_T/E_0)^{252/N}-1\) | Ann. vol | Sharpe | Max DD | Hit day frac. | Trade events |
|----------|------------|--------------|--------------------------------------|----------|--------|--------|---------------|--------------|
| A | 103594.04020 | 0.03594 | 0.05439 | 0.06649 | 0.82958 | −0.05060 | 0.32143 | 187 |
| B | 104459.05340 | 0.04459 | 0.06763 | 0.07241 | 0.93934 | −0.02836 | 0.27381 | 270 |
| C | 111056.56150 | 0.11057 | 0.17035 | 0.15490 | 1.09023 | −0.04818 | 0.27381 | 270 |
| SPY_BH | 121927.53580 | 0.21928 | 0.34633 | 0.21409 | 1.49478 | −0.12034 | 0.58929 | 0 |

Notes: Sharpe uses \(\sqrt{252}\cdot\mathrm{mean}(r)/\mathrm{stdev}(r)\) with \(r_f=0\). Winning-day fraction denominators include flat days. Trade hit ratios (completed trades) are lower than day hit ratios for B/C (~0.43 in production trade stats)—consistent with tighter stops raising turnover and false breakouts.

**Regression (strategy daily returns on SPY daily returns, HAC maxlag=5):**  
C: \(\hat\alpha_{\mathrm{daily}}=0.00070\) (ann. \(252\times\alpha=0.17573\)), \(\hat\beta=-0.02140\), \(R^2=0.00088\). Near-zero beta ≠ riskless; one-factor alpha ≠ structural alpha.  
A shows negative beta (≈−0.13) in this sample—consistent with short-side participation on down days, not a hedge guarantee.

**Bootstrap (block length 5, 1000 resamples, seed 42):** C Sharpe point 1.09023; 95% CI approximately **[−1.30, 2.74]**—wide; eight months is noisy.

**Through November (C):** total return ≈ **0.11711** (see `c_through_november.csv`)—December 1 is not driving the sign of results.

### 2.4 Robustness (predeclared; report all tested)

Matched lookback start for lb∈{10,14,20}: longer bands (20) looked somewhat better for C on this sample (total 0.08830 vs 0.06449 at lb14 on the **matched** shorter window)—**exploratory**, not a reason to change the headline lb=14.

VM∈{0.75,1.00,1.50}: VM=1.5 raised C total return to 0.15242 and Sharpe to 1.58046 here. We **do not** promote VM=1.5 as validated; the paper itself notes VM≈1.5 can look better in-sample while using VM=1 for simplicity.

Exposure caps for C: **1×** total 0.05371 / Sharpe 1.18263 / MDD −0.01810; **2×** 0.07738 / 1.13056 / −0.03136; **4×** 0.11057 / 1.09023 / −0.04818. Lower caps cut drawdown and can raise Sharpe while cutting total return—our modest “improvement” experiment favors **risk control via 2×**, not return maximization.

Slippage stress (commission fixed): C remains positive at $0.005 and $0.01/share slippage but Sharpe falls (1.090→1.046→0.992).

**Delay-one-bar fills:** C total return falls to **0.03902**, Sharpe **0.54637**—severe stress; shows dependence on idealized endpoint fills.

**Band-only exits (no VWAP):** C ≈ 0.11019 / 1.08663—almost identical to VWAP version here, so the approximate VWAP is **not** the main driver of this sample’s P&L (diagnostic only).

### 2.5 Relation of data to replication choices

Coarse 30-minute endpoints force open-proxy, VWAP-proxy, and idealized fills—the same features that make the homework feasible also prevent claiming exact live replicability or pattern studies. The short, generally rising 2025 SPY path favors buy-and-hold versus an often-flat intraday book (~45% days untraded). Differences vs the paper’s 2007–2024 headline are **expected** and not evidence the code is wrong.

---

## 3. Strategy assessment (Step 3.3)

**Economic hypothesis.** Large moves from the open at a given clock relative to the recent same-clock average may indicate persistent order-flow imbalance or slow incorporation of information (time-series momentum). Bands are a **heuristic noise region**, not a direct imbalance meter.

**What A vs B vs C do.** A rides until the opposite band (few exits, reversal risk). B truncates losses earlier using current band and VWAP, raising turnover and whipsaws (more trades: 270 vs 187). C scales share count to recent daily volatility, stabilizing risk across regimes but introducing leverage after quiet periods and larger $P&L swings.

**Attractiveness / investors.** Interesting as a transparent intraday TS-momentum lab case for investors who can short SPY, pay institutional-like costs, and supervise automation. **Not** established as attractive for discretionary retail from eight months of results—especially when SPY_BH won this window.

**Laptop implementation?** Computation: yes. Reliable live trading: needs synchronized clock/calendar (half-days!), quality data, broker API, locate/hard-to-borrow handling, disconnect recovery, kill switches—not built here and not attempted.

**Critical conditions.** Trend persistence within the day; tight spreads/liquidity; timely execution; cost control; sane leverage after low-\(\sigma\) windows; clean timestamps.

**Better/worse regimes.** Better when imbalance persists (paper’s high-VIX narrative is a hypothesis we could not test without VIX). Worse in mean-reverting chop, news reversals between 30-minute prints, and quiet markets with high leverage.

**Course concepts.** Links (mark for confirmation against actual lectures/readings): time-series vs cross-sectional momentum; volatility scaling; stop-loss / exit design; transaction costs; alpha–beta decomposition; backtest bias (fill assumptions, research design, short sample). _Student: replace with course-specific citations._

**Other markets.** Hours, auctions, tick size, shorting, participant mix, and hedging flows differ—transfer is an empirical question, not a corollary of SPY results (paper’s own multi-asset FAQ is suggestive, not our test).

**Underemphasized risks.** Stops only every 30 minutes; gaps between observations; leverage after calm periods; false breakouts; data/timestamp errors; short constraints; capacity/impact; model-selection bias; overnight market risk for an investor who holds other equity overnight even if *this* book flats.

**Improvements.** Demonstrated: lower leverage cap (2×) improves MDD/Sharpe tradeoff here. Implementation hygiene (lagged features, interval volume, half-day handling, delay stress) are correctness, not alpha. Untested ideas: true opens, finer VWAP, session filters—disclose costs of each.

---

## 4. Critical review of the paper (Step 3.4)

The paper is **interesting and useful** pedagogically: a clear signal, sequential improvement path (opposite band → band+VWAP → vol sizing), and frank FAQ material. **Realism** is mixed—transparent about commissions, but idealized timing and a small April 2024 slippage experiment (plus later I-Star appendix) do not certify costs for all eras/AUM.

Headline **1,985% / 19.6% / Sharpe 1.33** (Table 3 / abstract) are **historical reference** results for ~2007–early 2024 under their stack—not forecasts and not comparable one-for-one to our 2025 instructor sample.

**Leverage and benchmarks.** Dynamic sizing drives much of the jump from B to C in the paper; comparing leveraged active returns to 1× buy-and-hold needs that caveat. We treat our SPY_BH as **price-series** return until adjustment/dividends are verified—do not assert total-return equivalence.

**Noise Area.** Average absolute move ≠ statistical significance band or proven “equilibrium.”

**Execution / VWAP.** Semi-hourly decisions reduce noise but leave intrabar path risk. Our sample’s near-equality of band-only vs VWAP exits shows results can be insensitive to the VWAP proxy—or that both are coarse.

**Patterns / weekdays / VIX.** Multiple overlapping conditionings invite selection bias; significant mean≠0 is not pairwise superiority. Table 6 vs prose on Monday should be read carefully against the paper’s own 10% t-threshold (Monday t≈1.84 is borderline under their bolding rule).

**RSI regression.** RSI is a **price proxy**, not measured dealer gamma; correlation≠causation.

**Parameters.** Few parameters help interpretability but do not eliminate research-design / publication-selection risk. Post-publication updates (FAQ Q24) are informative yet are still authors’ backtests, not independently audited live returns.

**How we would present it.** Explicit fill and state tables; consistent sample windows for every table; uncertainty (bootstrap/DM tests); economic cost schedules; chronological OOS protocol; sharper boundary between mechanism stories and evidence.

---

## Student confirmation checklist

- [ ] Group member names / contributions  
- [ ] Confirm course lecture/paper links in §3  
- [ ] Confirm you accept open-proxy + bar-start timing (or obtain instructor clarification / true opens)  
- [ ] Spot-check `outputs/traces/` for 2025-07-03 and 2025-10-10  
- [ ] Export PDF from `reports/HW1_report.md` if required (e.g. print-to-PDF from a Markdown viewer)  
- [ ] Personal judgments on “would you trade this?” after reading results  

---

## Appendix A — How to reproduce

```bash
source .venv/bin/activate
python -m pytest tests/ -q
python scripts/run_analysis.py
```

## Appendix B — Key file map

| Path | Role |
|------|------|
| `config.yaml` | Parameters |
| `src/sis_hw1/data.py` | Audit/clean |
| `src/sis_hw1/features.py` | Bands, VWAP, σ |
| `src/sis_hw1/strategy.py` | State machine |
| `src/sis_hw1/backtest.py` | Ledger |
| `src/sis_hw1/reference_checks.py` | Independent arithmetic |
| `logs/verification_report.md` | Pass/fail evidence |
| `outputs/tables/core_summary_display5.csv` | Main numbers @ 5 dp |

## Appendix C — Prompt transcript location

See `logs/prompt_record.md` and `logs/experiment_log.md`. Full initial ChatGPT-assisted brief is the long user message in the Cursor session dated 2026-09-22.
