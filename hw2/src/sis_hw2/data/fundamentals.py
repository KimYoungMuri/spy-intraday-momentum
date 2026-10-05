"""Parallel-friendly fundamentals download (restated Yahoo data + lag)."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import yfinance as yf
from tqdm import tqdm


def _safe_get(df: pd.DataFrame, keys: list[str]):
    if df is None or df.empty:
        return None
    for k in keys:
        matches = [i for i in df.index if k.lower() in str(i).lower()]
        if matches:
            return df.loc[matches[0]]
    return None


def fetch_one(ticker: str) -> tuple[list[dict], pd.DataFrame | None]:
    rows = []
    shares_df = None
    try:
        tk = yf.Ticker(ticker)
        bs = tk.quarterly_balance_sheet
        fin = tk.quarterly_financials
        if (bs is None or bs.empty) and (fin is None or fin.empty):
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
            [
                "Net Income",
                "Net Income Common Stockholders",
                "Net Income Including Noncontrolling Interests",
            ],
        )
        share_line = _safe_get(bs, ["Share Issued", "Ordinary Shares Number", "Common Stock Shares Outstanding"])
        dates = set()
        if equity is not None:
            dates |= set(equity.index)
        if ni is not None:
            dates |= set(ni.index)
        for d in sorted(dates):
            rows.append({
                "ticker": ticker,
                "period_end": pd.Timestamp(d).tz_localize(None),
                "book_equity": float(equity[d]) if equity is not None and d in equity.index and pd.notna(equity[d]) else np.nan,
                "net_income_q": float(ni[d]) if ni is not None and d in ni.index and pd.notna(ni[d]) else np.nan,
                "shares_bs": float(share_line[d]) if share_line is not None and d in share_line.index and pd.notna(share_line[d]) else np.nan,
                "_meta": False,
            })
        info = {}
        try:
            info = tk.info or {}
        except Exception:
            info = {}
        rows.append({
            "ticker": ticker,
            "period_end": pd.NaT,
            "book_equity": np.nan,
            "net_income_q": np.nan,
            "shares_bs": np.nan,
            "sector_yahoo": info.get("sector"),
            "industry_yahoo": info.get("industry"),
            "shares_latest": info.get("sharesOutstanding"),
            "_meta": True,
        })
        try:
            sh = tk.get_shares_full(start="2010-01-01")
            if sh is not None and len(sh):
                shares_df = sh.reset_index()
                shares_df.columns = ["date", "shares"]
                shares_df["ticker"] = ticker
        except Exception:
            shares_df = None
        # Also synthesize shares from BS if needed
        if share_line is not None:
            tmp = share_line.dropna().reset_index()
            tmp.columns = ["date", "shares"]
            tmp["ticker"] = ticker
            from sis_hw2.utils.dates import to_naive_timestamp
            tmp["date"] = to_naive_timestamp(tmp["date"])
            if shares_df is not None and len(shares_df):
                shares_df = shares_df.copy()
                shares_df["date"] = to_naive_timestamp(shares_df["date"])
                shares_df = pd.concat([shares_df, tmp], ignore_index=True)
            else:
                shares_df = tmp
    except Exception as e:
        rows.append({"ticker": ticker, "error": str(e), "_meta": True})
    return rows, shares_df


def download_fundamentals_parallel(tickers: list[str], max_workers: int = 8) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_rows = []
    share_frames = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fetch_one, t): t for t in tickers}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="fundamentals"):
            rows, sh = fut.result()
            all_rows.extend(rows)
            if sh is not None and len(sh):
                share_frames.append(sh)
            time.sleep(0.01)
    fund = pd.DataFrame(all_rows)
    shares = pd.concat(share_frames, ignore_index=True) if share_frames else pd.DataFrame(columns=["date", "shares", "ticker"])
    return fund, shares
