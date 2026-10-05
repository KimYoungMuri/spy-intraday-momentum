# B9339 Homework 2 — Investor Pitch Research

Systematic long-only U.S. equity strategy combining **value**, **quality**, and **momentum** (VQM), prepared as an illustrative pitch to raise **$10 million** in assets under management.

**Course:** B9339 Systematic Investment Strategies (Fall 2026)  
**Due:** Monday, October 5, 2026, 5:00pm EST  
**Objective of pitch:** Raise assets to manage (not working capital for a firm startup).

## Important disclosures (read first)

- The equity universe is the **top 500 eligible names by market cap among a research ticker panel** derived from *current* Wikipedia S&P 500 constituents. This is **not** the historical S&P 500.
- Fundamentals come from Yahoo Finance and are typically **restated**. A reporting lag is applied; restatement bias remains.
- Sector labels are **current** GICS classifications applied historically.
- Delisted-name coverage is incomplete in Yahoo data → **survivorship bias**.
- An **ETF factor proxy** study is included and clearly labelled; it is **not** the stock-selection track record.

## Setup

```bash
cd hw2
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -e .
```

## Reproduce

```bash
# Full download + backtest (prices, fundamentals, ETF proxy, robustness)
python scripts/run_research.py

# Or stepwise:
python -c "from sis_hw2.data.universe import save_universe; save_universe()"
python -c "from sis_hw2.data.download import run_download; run_download()"
python -c "from sis_hw2.data.process import run_process; run_process()"
python scripts/run_research.py --skip-download
```

## Deliverables

| Path | Contents |
|------|----------|
| `reports/executive_summary.md` | Answer summary |
| `reports/strategy_spec.md` | Final strategy specification |
| `reports/data_inventory.md` | Data dictionary / source log |
| `reports/research_log.md` | Assumptions, variants tested |
| `reports/slide_writeup.md` | 10-slide investor pitch write-up |
| `reports/checklist.md` | Assignment requirement → deliverable map |
| `outputs/tables/` | Performance tables (5+ decimals) |
| `outputs/figures/` | Charts |
| `config.yaml` | Baseline rules |

## Strategy snapshot

- Universe: top 500 eligible by market cap (tradability filters)
- Signals: B/M, ROE, 12-1 momentum; sector percentile ranks; equal-weight composite
- Selection: top ~20% within each sector
- Weights: sector weights = eligible-universe cap weights; equal-weight within sector
- Rebalance: monthly; long-only; no leverage
