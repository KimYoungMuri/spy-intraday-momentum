# Verification report

Generated: 2026-09-22 (AI-executed).

## Automated tests

Command: `python -m pytest tests/ -q`

Result: **14 passed, 0 failed**.

Coverage includes: hand-worked bands (gap-up/gap-down), cumulative→interval + VWAP, A/B/C state transitions, zero-vol sizing, share floor and 4× cap, round-trip costs, half-day flatten, no-lookahead alteration test, sizing independence from same-day close, signal fill equals signal-bar price.

Independent arithmetic lives in `sis_hw1/reference_checks.py` (not a wrapper of production band code).

## Real-data session traces (AI recalculation)

| Session | Role | Band/VWAP vs reference | Overnight flat | Notes |
|---------|------|------------------------|----------------|-------|
| 2025-07-03 | Half-day | Exact match (0 diff) all clocks | Yes (pos=0) | Entered long 11:00, flattened 13:00; no afternoon trades |
| 2025-11-28 | Half-day | (trace exported) | Yes | No trades |
| 2025-10-10 | Strong short day | Exact match | Yes | Short 603 @ 668.725, flat @ 653.020; sizing σ and 4× shares match reference |

## Tolerances

- Feature equality checks: absolute difference ≤ 1e-12 (observed 0).
- Close series audit: \|intraday 16:00 − daily close\| ≤ 0.0003 on all 182 days.

## Unresolved / not claimed

- Headline paper metrics (19.6% IRR, Sharpe 1.33 over 2007–2024) are **not** expected to match this 2025 sample.
- True 09:30 opens are unavailable; results are a disclosed open-proxy adaptation.
- Timestamp bar-start convention is inferred, not vendor-certified.
- Authors' public code was not used for verification in this project.
