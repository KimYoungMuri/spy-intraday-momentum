#!/usr/bin/env python3
"""Enrich fundamentals with Yahoo annual statements (longer than quarterly-only)."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from tqdm import tqdm

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sis_hw2.utils.io import load_frame, save_frame
from sis_hw2.utils.dates import to_naive_timestamp, to_naive_scalar
from sis_hw2.utils.config import project_root


def _safe_get(df: pd.DataFrame, keys: list[str]):
    if df is None or df.empty:
        return None
    for k in keys:
        matches = [i for i in df.index if k.lower() in str(i).lower()]
        if matches:
            return df.loc[matches[0]]
    return None


def fetch_annual(ticker: str) -> list[dict]:
    rows = []
    try:
        tk = yf.Ticker(ticker)
        bs = tk.balance_sheet
        fin = tk.financials
        equity = _safe_get(bs, ["Stockholders Equity", "Common Stock Equity", "Total Stockholder Equity"])
        ni = _safe_get(fin, ["Net Income", "Net Income Common Stockholders"])
        shares = _safe_get(bs, ["Share Issued", "Ordinary Shares Number", "Common Stock Shares Outstanding"])
        dates = set()
        if equity is not None:
            dates |= set(equity.index)
        if ni is not None:
            dates |= set(ni.index)
        for d in sorted(dates):
            rows.append({
                "ticker": ticker,
                "period_end": to_naive_scalar(d),
                "book_equity": float(equity[d]) if equity is not None and d in equity.index and pd.notna(equity[d]) else np.nan,
                "net_income_q": float(ni[d]) if ni is not None and d in ni.index and pd.notna(ni[d]) else np.nan,
                "shares_bs": float(shares[d]) if shares is not None and d in shares.index and pd.notna(shares[d]) else np.nan,
                "_meta": False,
                "statement_freq": "A",
            })
    except Exception as e:
        rows.append({"ticker": ticker, "error": str(e), "_meta": True, "statement_freq": "A"})
    return rows


def main():
    root = project_root()
    raw = root / "data" / "raw"
    existing = load_frame(raw / "fundamentals_raw.pkl")
    if "statement_freq" not in existing.columns:
        existing["statement_freq"] = np.where(existing.get("_meta", False) == True, "META", "Q")
    tickers = pd.read_csv(raw / "research_ticker_panel.csv")["ticker"].astype(str).tolist()
    rows = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_annual, t): t for t in tickers}
        for fut in tqdm(as_completed(futs), total=len(futs), desc="annual_fundamentals"):
            rows.extend(fut.result())
            time.sleep(0.01)
    annual = pd.DataFrame(rows)
    # Keep meta from existing; merge non-meta annual + quarterly
    meta = existing[existing["_meta"] == True].copy()
    q = existing[existing["_meta"] != True].copy()
    a = annual[annual.get("_meta", False) != True].copy() if "_meta" in annual.columns else annual
    if "statement_freq" not in q.columns:
        q["statement_freq"] = "Q"
    merged = pd.concat([q, a, meta], ignore_index=True)
    # de-dup on ticker/period_end preferring quarterly
    nonmeta = merged[merged["_meta"] != True].copy()
    nonmeta["period_end"] = to_naive_timestamp(nonmeta["period_end"])
    nonmeta["_pref"] = nonmeta["statement_freq"].map({"Q": 0, "A": 1}).fillna(1)
    nonmeta = nonmeta.sort_values(["ticker", "period_end", "_pref"]).drop_duplicates(["ticker", "period_end"], keep="first")
    nonmeta = nonmeta.drop(columns=["_pref"], errors="ignore")
    out = pd.concat([nonmeta, meta], ignore_index=True)
    save_frame(out, raw / "fundamentals_raw.pkl")
    print("saved", out.shape, "period range", nonmeta["period_end"].min(), nonmeta["period_end"].max(),
          "tickers", nonmeta["ticker"].nunique())


if __name__ == "__main__":
    main()
