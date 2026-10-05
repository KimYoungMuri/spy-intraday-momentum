# Experiment and correction log

Platform: Cursor (AI coding assistant). Model name/version: **unknown** (not displayed in this session).  
Initial assignment prompt prepared with ChatGPT from the homework PDF and paper; ChatGPT model: **unknown / not recorded**.  
Coding/replication platform for implementation: Cursor.  
Date: 2026-09-22.  
Python: 3.13.3 (`/Users/youngkim/cursorprojects/systematic_investment_strategies/.venv`).

## Chronology

1. **Ingest inputs.** Copied `hw1.pdf`, paper PDF, and workbook into `data/raw/` unchanged. Workspace was empty beforehand.

2. **Data audit (re-verification of ChatGPT-supplied Section 4A).** Implemented `sis_hw1.data.audit_and_clean`. Confirmed: 182 sessions (2025-03-13–2025-12-01); AV.Clean 2544 rows; half-days have 12 labels with stale post-13:00 rows; 1181 within-session volume decreases; seven volume-reconciliation fails matching the supplied table; close diffs ≤ $0.0003; 15:30=16:00 on 121/182 days.

3. **Design choices locked.** Bar-start+30m availability; open_proxy = first regular endpoint; first entry at next endpoint; interval volumes not differenced; half-days flatten at 13:00; B/C entry requires price beyond stop threshold.

4. **Implementation.** Features → state machine A/B/C → backtest ledger → metrics → `scripts/run_analysis.py`.

5. **Tests.** First pytest run: 13/14 passed; half-day test had a broken `assert all(... if False else True)` typo. Fixed; **14/14 passed**.

6. **Independent real-session arithmetic.** Compared `reference_checks` bands/VWAP/sizing to production for 2025-07-03 and 2025-10-10: **exact match (diff 0)**. Half-day last position 0; no post-13:00 trades.

7. **Empirical run.** Core A/B/C + SPY_BH and predeclared sensitivity grid completed; outputs under `outputs/`.

8. **Write-up.** Draft report assembled from saved executed results only.

## Corrections (actual)

| Issue | Observation | Fix | Evidence |
|------|-------------|-----|----------|
| Half-day unit test assertion | `TypeError: 'bool' object is not iterable` | Rewrote assertion to max(available_at) ≤ 13:00 | pytest 14 passed |
| Delay-mode fill logic | Initial draft mixed pending/queue unclearly | Rewrote `backtest.py` delay path with explicit pending fill then queue | delay sensitivity runs |
| Git provenance commit | Environment blocked `git init` | File snapshot at `logs/snapshots/final_src/` instead | snapshot present |

## What was not done / not claimed

- Authors' Matlab/Python code was **not** downloaded or used.
- No second AI reviewed the code in this session.
- Student did not personally re-check arithmetic in this chat; AI-performed checks are labeled as such.
- No live brokerage connection or trades.
