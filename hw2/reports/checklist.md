# Assignment Requirements Checklist — HW2

| # | Requirement | Deliverable | Status |
|---|-------------|-------------|--------|
| A | Identify pitch objective clearly | `strategy_spec.md`, Slide 1, `executive_summary.md` | Done — raise $10mm AUM |
| B | Landscape / category context | `slide_writeup.md` Slide 2 | Done |
| C | Main idea + technical details (method + results) | Spec + code + Slides 3–6 + tables | Done (real numbers) |
| D | Innovation (if any) — honest | Slide 9 | Done — not claiming factor discovery |
| E | Competitive advantages | Slide 9 | Done |
| F | Robustness of evidence | Slide 7; `robustness_design.csv` | Done |
| G | Feasibility (costs, liquidity, capacity, capital) | Slide 8; turnover/cost figures | Done |
| H | Anticipate audience Q&A | Slide 10 | Done |
| I | Summary of answers on first page | `executive_summary.md` | Done |
| J | ≥5 decimal places where appropriate | `outputs/tables/*.csv` | Done |
| K | Show/explain main formulas | Spec + slide write-up appendix | Done |
| L | Clean, reproducible submission | `README.md`, `scripts/run_research.py` | Done |
| M | Real data explained | `data_inventory.md` / `.json` | Done |
| N | Map research plan §§1–7 | This checklist + folder tree | Done |

## User research-plan mapping

| Section | Mapping |
|---------|---------|
| 1 Objective & strategy | `strategy_spec.md`, `config.yaml` |
| 2 Real data audit | `data_inventory.md`, `data/raw/` |
| 3 Implement & run | `src/sis_hw2/`, `scripts/run_research.py`, `outputs/` |
| 4 Robustness & feasibility | `robustness_design.csv`; Slides 7–8 |
| 5 Competitive landscape | Slides 2 & 9 |
| 6 Slide write-up | `reports/slide_writeup.md` |
| 7 Deliverables & verification | this checklist; executive summary |

## Executed vs proposed future work

| Item | Executed? |
|------|-----------|
| Public Yahoo/FRED/GitHub pull | Yes |
| Stock-level VQM backtest (short Yahoo window) | Yes — terminal 149529 |
| Labelled ETF proxy long horizon | Yes |
| Point-in-time Compustat/CRSP | **No** — not supplied |
| Observed TCA | **No** — estimated bps |
| Full re-download after tz fix | **Not required** — recovery used `--skip-download` |

## Verification (non-degenerate)

| Check | Result |
|-------|--------|
| VQM design CAGR ≠ 0 | 0.43457765 |
| SPY design CAGR ≠ 0 | 0.20933880 |
| Ignore zero-metric run 696600 | Yes |
| Figures present | 8 PNGs under `outputs/figures/` |
| Slide write-up with real numbers | `reports/slide_writeup.md` |
