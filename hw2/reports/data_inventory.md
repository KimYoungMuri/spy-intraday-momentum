# Data Inventory and Dictionary — HW2

**Retrieval date (UTC):** see `data/raw/download_inventory.json` and `data/raw/universe_meta.json`  
**Assignment data cutoff:** 2026-10-05  
**Policy:** No purchased/subscription databases. Public APIs only. No fabricated series.

## Sources

| Provider | Dataset | URL | Frequency | Fields used | Notes |
|----------|---------|-----|-----------|-------------|-------|
| GitHub `datasets/s-and-p-500-companies` | Current S&P 500 constituents | https://github.com/datasets/s-and-p-500-companies | Snapshot | ticker, name, GICS sector/industry | **Not** historical membership. Survivorship/membership bias. |
| Yahoo Finance (`yfinance`) | Daily OHLCV + Adj Close | https://finance.yahoo.com/ | Daily | open, high, low, close, adj_close, volume | Adj Close used for total returns (splits + dividends). |
| Yahoo Finance (`yfinance`) | Quarterly financials / balance sheet | https://finance.yahoo.com/ | Quarterly | book equity, net income; shares when available | **Restated** values. 60-day lag applied in code; not as-filed PIT. |
| Yahoo Finance (`yfinance`) | Shares outstanding | `get_shares_full` / BS share lines / `info.sharesOutstanding` | Irregular | shares | Fallback to constant latest shares when history missing. |
| Yahoo Finance (`yfinance`) | ETF Adj Close (SPY, VLUE, QUAL, MTUM, VTV, SPHQ, PDP) | https://finance.yahoo.com/ | Daily | adj_close | Benchmarks and **labelled** factor-ETF proxy. |
| FRED | DGS3MO 3-month Treasury yield | https://fred.stlouisfed.org/series/DGS3MO | Daily | yield_pct → rf_daily ≈ y/100/252 | Risk-free for Sharpe. |

## Local paths

| Path | Contents |
|------|----------|
| `data/raw/research_ticker_panel.csv` | Research universe panel |
| `data/raw/sector_map.csv` | Sector labels |
| `data/raw/prices_daily.pkl` | Stock prices |
| `data/raw/etf_prices.pkl` | ETF prices |
| `data/raw/risk_free.pkl` | Risk-free series |
| `data/raw/fundamentals_raw.pkl` | Raw fundamentals (+ meta rows) |
| `data/raw/shares/` | Per-ticker shares CSVs |
| `data/processed/*.pkl` | Analysis-ready tables |
| `reports/data_inventory.json` | Machine-readable inventory written at download |

## Transformations

1. **Total return:** \(r_{t} = \mathrm{AdjClose}_t / \mathrm{AdjClose}_{t-1} - 1\) (Yahoo dividend/split convention; do not also add cash dividends).
2. **Market cap:** \(\mathrm{MCap}_t \approx \mathrm{Close}_t \times \mathrm{Shares}_t\).
3. **Book/market:** \(B/M = \mathrm{BookEquity} / \mathrm{MCap}\) after lag.
4. **ROE:** \(\mathrm{ROE} = \mathrm{NI}^{TTM} / \mathrm{BookEquity}\) (TTM = sum of available last ≤4 quarters).
5. **Momentum 12–1:** \(\mathrm{Mom} = \mathrm{AdjClose}_{t-21d} / \mathrm{AdjClose}_{t-365d} - 1\).
6. **Availability lag:** fundamental period-end + 60 calendar days ≤ signal date.
7. **Sector ranks:** percentile rank within sector among eligible names; higher = more attractive.

## Coverage and exclusions

- Exclude nonpositive book equity.
- Exclude missing required signals.
- Price filter ≥ $5; 20-day ADV ≥ $1,000,000.
- Delisted names largely absent from Yahoo panel → **survivorship bias**.
- Yahoo statement `period_end` in processed data runs **2021-10-31 → 2026-08-31** (annual + quarterly); no 10-year fundamental history. Stock backtest design uses **`first_rebalance=2023-06-30`** (see `config.yaml`) — not a 2014 stock sample.

## Licensing / reproducibility

- Yahoo Finance and FRED: free for research use subject to provider terms; not redistributed as a commercial data product.
- GitHub constituents CSV: open data.
- Reproduce with `python scripts/run_research.py` (network required for fresh download).

## Critical honesty constraints

- Do **not** call the panel the historical S&P 500.
- Do **not** claim point-in-time fundamentals.
- Do **not** present the ETF proxy as the stock-selection track record.
