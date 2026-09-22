# Experiment and correction log (revised)

Platform: **Cursor** (model **unknown**).  
Brief / revision guidance prepared with **ChatGPT** (model **unknown**).  
Python 3.13.3 in `.venv`.  
Final results timestamp: **2026-09-22T15:53:32**.

## Chronology (actual)

1. Copied homework PDF, paper PDF, and workbook into `data/raw/` unchanged.
2. Re-verified ChatGPT-supplied workbook audit in code (`data.py`).
3. Implemented A/B/C backtester, tests, analysis runner.
4. First pytest: 13/14 — **test assertion typo** on half-day test (not a strategy bug). Fixed → 14/14.
5. Rewrote delay-fill path for clarity before relying on delay sensitivities (no saved before/after metric pair for a buggy delay run).
6. Independent band/VWAP/sizing checks on real sessions; empirical pipeline.
7. Draft report contained hit-ratio direction error and other narrative issues.
8. Revision: backup → fix MDD definition (no numeric change here) → add P&L tests → correct report → regenerate outputs/PDF. Tests **17/17**.

## Honest limitations on “iteration history”

- We did **not** invent failed prompts.
- Delay rewrite: clarification of implementation risk, not a demonstrated empirical bug with before/after Sharpe.
- Half-day “fix”: test-only.
- Pre-revision artifacts: `backups/pre_revision_20260922/`.
