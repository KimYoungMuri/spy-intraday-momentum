# Appendix — Research notes (not for main slides)

Keep this material out of the investor-facing pitch. Use only if asked about reproducibility or methodology history.

## Superseded / invalid figures (do not cite in pitch)

- Pre-correction stock CAGR ~43.5%; holdout ~81.6%; ETF-proxy ~14.7%.
- Cause: portfolio weights were updated with same-day returns **before** computing \(R_p\). Fixed formula: \(R_p=\sum w_i r_i\) then drift.

## Correctness work (prerequisite, not a selling point)

- Missing held returns halt-zero-flagged; explicit `pct_change` missing handling; BS shares on availability date; `constant_latest` excluded from mcap; no gap→annual income; date-matched average book; ADV requires 20 obs; no return before first execution; cost labelled proportional approximation.
- Tests: `pytest tests/test_accounting.py`
- Reproduce: `python scripts/run_decision_study.py` (cached raw under `data/raw/`)

## High-precision design-window metrics

See `outputs/tables/AF_comparison_summary.csv` (≥5 decimal digits). Readable % on main slides.

## Turnover definition

- One-way turnover = \(0.5 \times \sum_i |w_{i,t}-w_{i,t-}|\).
- Main-slide VQM figure **25.5%** = average across **29** month-end rebalances **excluding** initial portfolio formation.
- **27.6%** includes initial book build (full deployment treated as turnover).

## Liquidity: position vs trade participation @ $10mm

Source: `outputs/tables/adv_trade_capacity_stats.json`, `adv_trade_sizing_10mm.csv`

| Metric | Median | p95 | Max |
|--------|--------|-----|-----|
| Position / ADV | 0.026% | 0.14% | 5.59% |
| Rebalance trade / ADV (ex-initial) | 0.001% | 0.055% | 5.59% |

## ETF blend (comparator only — not the product)

Equal-weight VLUE/QUAL/MTUM monthly, after approx 5 bps/side, long horizon: CAGR ≈ 14.43% vs SPY ≈ 14.13% (active ≈ +0.31%/yr). Different investable portfolio; not a substitute track record for stock VQM.

## Complementarity evidence files

- `outputs/tables/holdings_overlap_summary.csv`
- `outputs/tables/portfolio_signal_exposures_avg.csv`
- `outputs/tables/sleeve_active_return_corr.csv`
- `outputs/tables/complementarity_evidence.json`
- `outputs/figures/holdings_overlap_VQM_Mom.png`
- `outputs/figures/portfolio_characteristic_exposures.png`
- `outputs/figures/sleeve_active_corr.png`

## Language constraints for the pitch

- Say **profitability proxy**, not balance-sheet strength.
- Say **lower observed volatility and maximum drawdown**, not “momentum crash diversification.”
- Say we **balance** valuation, profitability, and momentum — not that every holding passes three tests.
- Sector controls do **not** uniquely distinguish VQM from momentum (same design in A–F).
- Fee concern **once**: rationale ≠ automatic 75 bps justification.

## Decision memo

`reports/STRATEGY_DECISION.md` — keep VQM; conditional $10mm stock-mandate ask; fee/deployability not established.
