"""Download market, fundamental, benchmark, and risk-free data."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from tqdm import tqdm

from sis_hw2.utils.io import save_frame, load_frame
from sis_hw2.utils.config import load_config, project_root, ensure_dirs
from sis_hw2.utils.dates import to_naive_timestamp, to_naive_scalar


def _root_paths():
    cfg = load_config()
    root = project_root()
    ensure_dirs(cfg)
    return cfg, root, root / cfg["paths"]["raw"], root / cfg["paths"]["processed"]


def download_prices(tickers: list[str], start: str, end: str, chunk: int = 50) -> pd.DataFrame:
    """Download adjusted OHLCV; Adj Close used for total-return calculations."""
    frames = []
    tickers = sorted(set(tickers))
    for i in tqdm(range(0, len(tickers), chunk), desc="prices"):
        batch = tickers[i : i + chunk]
        data = yf.download(
            batch,
            start=start,
            end=end,
            auto_adjust=False,
            progress=False,
            threads=True,
        )
        if data is None or data.empty:
            continue
        # yfinance returns MultiIndex columns as (Price, Ticker)
        if isinstance(data.columns, pd.MultiIndex):
            # stack tickers into long format
            flat = data.copy()
            flat.columns = [f"{a}|{b}" for a, b in flat.columns]
            flat = flat.reset_index()
            date_col = "Date" if "Date" in flat.columns else flat.columns[0]
            long = flat.melt(id_vars=[date_col], var_name="field_ticker", value_name="value")
            long[["field", "ticker"]] = long["field_ticker"].str.split("|", n=1, expand=True)
            piv = long.pivot_table(index=[date_col, "ticker"], columns="field", values="value", aggfunc="first")
            piv = piv.reset_index().rename(columns={
                date_col: "date",
                "Adj Close": "adj_close",
                "Close": "close",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Volume": "volume",
            })
            frames.append(piv)
        else:
            t = batch[0]
            tmp = data.reset_index().rename(columns={
                "Date": "date", "Adj Close": "adj_close", "Close": "close",
                "Open": "open", "High": "high", "Low": "low", "Volume": "volume",
            })
            tmp["ticker"] = t
            frames.append(tmp)
        time.sleep(0.2)
    if not frames:
        return pd.DataFrame()
    px = pd.concat(frames, ignore_index=True)
    px["date"] = to_naive_timestamp(px["date"])
    keep = ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]
    px = px[[c for c in keep if c in px.columns]]
    # If Adj Close missing (auto-adjust), fall back to Close
    if "adj_close" not in px.columns and "close" in px.columns:
        px["adj_close"] = px["close"]
    px = px.dropna(subset=["adj_close"]).sort_values(["ticker", "date"])
    return px


def download_etf_benchmarks(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    data = yf.download(tickers, start=start, end=end, auto_adjust=False, progress=False)
    if data is None or data.empty:
        return pd.DataFrame(columns=["date", "ticker", "adj_close"])
    if isinstance(data.columns, pd.MultiIndex):
        # (Price, Ticker)
        if "Adj Close" in data.columns.get_level_values(0):
            adj = data["Adj Close"].copy()
        else:
            adj = data["Close"].copy()
    else:
        col = "Adj Close" if "Adj Close" in data.columns else "Close"
        adj = data[[col]].copy()
        adj.columns = [tickers[0]]
    adj = adj.reset_index()
    date_col = "Date" if "Date" in adj.columns else adj.columns[0]
    adj = adj.rename(columns={date_col: "date"})
    adj["date"] = to_naive_timestamp(adj["date"])
    long = adj.melt(id_vars="date", var_name="ticker", value_name="adj_close").dropna()
    return long.sort_values(["ticker", "date"])


def download_fred_rf(series: str = "DGS3MO", start: str = "2010-01-01") -> pd.DataFrame:
    """3-month Treasury yield from FRED via pandas_datareader; fallback to CSV."""
    try:
        import pandas_datareader.data as web
        rf = web.DataReader(series, "fred", start=start)
        rf = rf.reset_index().rename(columns={"DATE": "date", series: "yield_pct"})
    except Exception:
        # Fallback: Yahoo ^IRX (13-week T-bill discount)
        t = yf.download("^IRX", start=start, progress=False)
        t = t.reset_index()
        date_col = "Date" if "Date" in t.columns else t.columns[0]
        close_col = "Adj Close" if "Adj Close" in t.columns else "Close"
        rf = t[[date_col, close_col]].rename(columns={date_col: "date", close_col: "yield_pct"})
        series = "^IRX"
    rf["date"] = to_naive_timestamp(rf["date"])
    rf["source"] = series
    # Convert annualized % yield to daily simple rf approx
    rf["rf_daily"] = (rf["yield_pct"] / 100.0) / 252.0
    return rf.dropna()


def _safe_get(df: pd.DataFrame, keys: list[str]) -> pd.Series | None:
    if df is None or df.empty:
        return None
    idx = df.index.astype(str)
    for k in keys:
        matches = [i for i in df.index if k.lower() in str(i).lower()]
        if matches:
            return df.loc[matches[0]]
    return None


def download_fundamentals(tickers: list[str], sleep: float = 0.15) -> pd.DataFrame:
    """
    Pull quarterly balance sheet / income statement via yfinance.

    DISCLOSURE: Yahoo fundamentals are typically restated values, not original
    as-reported point-in-time filings. We apply a calendar lag to approximate
    public availability, but restatement bias remains.
    """
    rows = []
    for t in tqdm(tickers, desc="fundamentals"):
        try:
            tk = yf.Ticker(t)
            bs = tk.quarterly_balance_sheet
            fin = tk.quarterly_financials
            if (bs is None or bs.empty) and (fin is None or fin.empty):
                # try annual as sparse fallback
                bs = tk.balance_sheet
                fin = tk.financials
            equity = _safe_get(
                bs,
                [
                    "Stockholders Equity",
                    "Common Stock Equity",
                    "Total Stockholder Equity",
                    "Total Equity Gross Minority Interest",
                ],
            )
            ni = _safe_get(
                fin,
                ["Net Income", "Net Income Common Stockholders", "Net Income Including Noncontrolling Interests"],
            )
            # shares for market cap approximation
            shares = None
            try:
                sh = tk.get_shares_full(start="2010-01-01")
                if sh is not None and len(sh):
                    shares = sh
            except Exception:
                shares = None

            dates = set()
            if equity is not None:
                dates |= set(equity.index)
            if ni is not None:
                dates |= set(ni.index)
            for d in sorted(dates):
                row = {
                    "ticker": t,
                    "period_end": to_naive_scalar(d),
                    "book_equity": float(equity[d]) if equity is not None and d in equity.index and pd.notna(equity[d]) else np.nan,
                    "net_income_q": float(ni[d]) if ni is not None and d in ni.index and pd.notna(ni[d]) else np.nan,
                }
                rows.append(row)

            # cache latest sector if available
            try:
                info = tk.info or {}
            except Exception:
                info = {}
            rows.append({
                "ticker": t,
                "period_end": pd.NaT,
                "book_equity": np.nan,
                "net_income_q": np.nan,
                "sector_yahoo": info.get("sector"),
                "industry_yahoo": info.get("industry"),
                "shares_latest": info.get("sharesOutstanding"),
                "_meta": True,
            })
            # store shares series separately via side file later
            if shares is not None:
                sh_df = shares.reset_index()
                sh_df.columns = ["date", "shares"]
                sh_df["ticker"] = t
                sh_path = _root_paths()[2] / "shares"
                sh_path.mkdir(exist_ok=True)
                sh_df.to_csv(sh_path / f"{t}.csv", index=False)
        except Exception as e:
            rows.append({"ticker": t, "error": str(e), "_meta": True})
        time.sleep(sleep)
    fund = pd.DataFrame(rows)
    return fund


def download_sector_map(panel: pd.DataFrame) -> pd.DataFrame:
    """Prefer Wikipedia GICS sector when available; else Yahoo."""
    out = panel[["ticker"]].copy()
    if "sector" in panel.columns:
        out["sector"] = panel["sector"]
    else:
        out["sector"] = "Unknown"
    out["sector_source"] = "wikipedia_current"
    return out


def run_download(panel_path: Path | None = None) -> dict:
    cfg, root, raw, processed = _root_paths()
    if panel_path is None:
        panel_path = raw / "research_ticker_panel.csv"
    if not panel_path.exists():
        from sis_hw2.data.universe import save_universe
        save_universe()
    panel = pd.read_csv(panel_path)
    tickers = panel["ticker"].astype(str).tolist()
    start, end = cfg["sample"]["price_start"], cfg["sample"]["price_end"]

    inventory = {
        "retrieval_date_utc": datetime.now(timezone.utc).isoformat(),
        "assignment_cutoff": cfg["project"]["assignment_cutoff"],
        "sources": [],
    }

    # Prices
    px = download_prices(tickers, start, end)
    px_path = raw / "prices_daily.pkl"
    save_frame(px, px_path)
    inventory["sources"].append({
        "provider": "Yahoo Finance via yfinance",
        "dataset": "daily OHLCV + Adj Close",
        "url": "https://finance.yahoo.com/",
        "fields": list(px.columns),
        "sample_period": f"{start} to {end}",
        "n_rows": int(len(px)),
        "n_tickers": int(px["ticker"].nunique()) if len(px) else 0,
        "adjustment": "Adj Close incorporates splits and dividend reinvestment (Yahoo convention)",
        "path": str(px_path.relative_to(root)),
    })

    # Benchmarks / factor ETFs
    etfs = [cfg["benchmarks"]["primary_etf"]] + list(cfg["benchmarks"]["factor_etfs"])
    etf = download_etf_benchmarks(etfs, start, end)
    etf_path = raw / "etf_prices.pkl"
    save_frame(etf, etf_path)
    inventory["sources"].append({
        "provider": "Yahoo Finance via yfinance",
        "dataset": "ETF Adj Close (SPY, factor ETFs)",
        "url": "https://finance.yahoo.com/",
        "tickers": etfs,
        "path": str(etf_path.relative_to(root)),
        "n_rows": int(len(etf)),
    })

    # Risk-free
    rf = download_fred_rf(cfg["benchmarks"]["risk_free"], start=start)
    rf_path = raw / "risk_free.pkl"
    save_frame(rf, rf_path)
    inventory["sources"].append({
        "provider": "FRED (or Yahoo ^IRX fallback)",
        "dataset": cfg["benchmarks"]["risk_free"],
        "url": "https://fred.stlouisfed.org/",
        "units": "percent annualized -> daily/252",
        "path": str(rf_path.relative_to(root)),
        "n_rows": int(len(rf)),
    })

    # Fundamentals (parallel) — Yahoo restated data + lag later
    from sis_hw2.data.fundamentals import download_fundamentals_parallel
    fund, shares_all = download_fundamentals_parallel(tickers, max_workers=8)
    fund_path = raw / "fundamentals_raw.pkl"
    save_frame(fund, fund_path)
    sh_dir = raw / "shares"
    sh_dir.mkdir(exist_ok=True)
    if len(shares_all):
        shares_all = shares_all.copy()
        shares_all["date"] = to_naive_timestamp(shares_all["date"])
        save_frame(shares_all, raw / "shares_all.pkl")
        for t, g in shares_all.groupby("ticker"):
            g.to_csv(sh_dir / f"{t}.csv", index=False)
    inventory["sources"].append({
        "provider": "Yahoo Finance via yfinance",
        "dataset": "quarterly balance sheet / income statement",
        "url": "https://finance.yahoo.com/",
        "point_in_time": False,
        "restated": True,
        "lag_applied_later_days": cfg["signals"]["fundamental_lag_days"],
        "path": str(fund_path.relative_to(root)),
        "n_rows": int(len(fund)),
        "warning": "Fundamentals are restated; lag approximates availability but does not restore as-filed values.",
    })

    # Sector map
    sectors = download_sector_map(panel)
    sec_path = raw / "sector_map.csv"
    sectors.to_csv(sec_path, index=False)
    inventory["sources"].append({
        "provider": "Wikipedia GICS (current)",
        "dataset": "sector classifications",
        "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "path": str(sec_path.relative_to(root)),
        "warning": "Current sector labels applied historically — retroactive classification bias.",
    })

    inv_path = root / cfg["paths"]["reports"] / "data_inventory.json"
    inv_path.parent.mkdir(parents=True, exist_ok=True)
    inv_path.write_text(json.dumps(inventory, indent=2))
    (raw / "download_inventory.json").write_text(json.dumps(inventory, indent=2))
    return inventory


if __name__ == "__main__":
    inv = run_download()
    print(json.dumps(inv, indent=2)[:2000])
