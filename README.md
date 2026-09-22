# README — B9339 Homework 1

Replication of Zarattini, Aziz, and Barbon (2025) intraday SPY momentum on instructor Bloomberg 30-minute data.

**Student:** Young Kim. AI coding: Cursor. Brief/review assistance: ChatGPT (models unknown).

## Setup and reproduce

```bash
cd systematic_investment_strategies
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -e .
```

Required input (do not modify):

`data/raw/hw1.spy.20250313-20251201.intra-30m.xlsx`

```bash
python -m pytest tests/ -q
python scripts/run_analysis.py
```

## Submission documents

- `reports/HW1_report.md` — primary write-up
- `reports/HW1_report.pdf` — rendered PDF
- `reports/HW1_report.html` — HTML companion
- `docs/compliance_checklist.md`
- `logs/prompts/` — extracted user prompts
- `logs/verification_report.md`
- `outputs/` — tables, figures, ledgers, traces
- `backups/pre_revision_20260922/` — pre-revision snapshot

## Main adaptations

No true open in workbook (open-proxy); inferred bar-start timestamps; interval volumes; half-day post-13:00 rows excluded from trading/history.
