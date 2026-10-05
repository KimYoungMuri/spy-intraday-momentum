# Research Log — Corrections

## Superseded results
Pre-correction commit `d51066f` outputs are unverified due to return-accounting bug. See `outputs/SUPERSEDED_UNVERIFIED_README.md` and `backups/pre_correction_d51066f/`.

**Do not cite:** ~43.5% stock CAGR, ~81.6% holdout CAGR, ~14.7% ETF-proxy CAGR.

## Change log

### 1. Return-accounting corrections
- Fixed `portfolio_return_and_drift`: \(R_p=w\cdot r\) then drift.
- Applied to stock backtest and ETF proxy.
- Regression: 50/50 ±10% → 0% return, 55%/45% weights (`tests/test_accounting.py`).

### 2. Signal-definition corrections
- ADV: exactly 20 trading sessions.
- Momentum: 21 and 252 **trading** sessions.
- Ranks after top-N universe selection.
- TTM requires 4 quarterly observations; annual NI fallback **labelled** (Yahoo sparse quarters).
- Quality denominator: average book when available.

### 3. Execution changes
- Signals at month-end close; trades at **next session close**.
- Costs on L1 traded notional; NAV scaled self-financing.
- Fee applied as daily scale factor separately.

### 4. Data-source changes
- No Sharadar purchase; rerun on **same cached Yahoo** inputs to isolate implementation effects.
- Shares: historical preferred; constant-latest only if no history (coverage reports 0 constant fallbacks after rebuild).
- FRED DGS3MO retained with yield→daily conversion disclosure.

## Predeclared robustness (executed)
Signal weights nearby; selection 10/20/30%; monthly vs quarterly; costs 5/10/15/25 bps; lags 45/60/90. See `outputs/tables/robustness_design.csv`.

## Corrected headline (design window)
VQM after 5 bps/side CAGR **25.47%** vs SPY **20.40%** (2023-07-03→2025-12-31). ETF proxy long-horizon CAGR **14.43%** vs SPY **14.13%**.
