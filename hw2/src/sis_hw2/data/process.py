"""Process raw downloads into analysis-ready tables."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from sis_hw2.utils.io import save_frame, load_frame
from sis_hw2.utils.config import load_config, project_root, ensure_dirs
from sis_hw2.utils.dates import to_naive_timestamp


def load_raw():
    cfg = load_config()
    root = project_root()
    raw = root / cfg["paths"]["raw"]
    prices = load_frame(raw / "prices_daily.pkl")
    etf = load_frame(raw / "etf_prices.pkl")
    rf = load_frame(raw / "risk_free.pkl")
    fund = load_frame(raw / "fundamentals_raw.pkl")
    sectors = pd.read_csv(raw / "sector_map.csv")
    return cfg, root, prices, etf, rf, fund, sectors


def build_shares_panel(raw: Path, fund: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    Assemble shares outstanding for market-cap ranking.

    DISCLOSURE: Yahoo historical share series are sparse. Baseline uses each
    ticker's latest known sharesOutstanding (or BS share count) as a *constant*
    across the price calendar so MCap_t ≈ Close_t × Shares_const. This ranks
    large-caps reasonably within a mega-cap panel but is not point-in-time shares.
    """
    from sis_hw2.utils.dates import to_naive_timestamp

    meta = fund[fund["_meta"] == True].copy() if "_meta" in fund.columns else pd.DataFrame()
    constants: dict[str, float] = {}
    if len(meta) and "shares_latest" in meta.columns:
        for _, row in meta.dropna(subset=["shares_latest"]).iterrows():
            constants[str(row["ticker"])] = float(row["shares_latest"])
    # Fallback: last non-null shares_bs
    if "shares_bs" in fund.columns:
        bs = fund.dropna(subset=["shares_bs"]).sort_values("period_end")
        for t, g in bs.groupby("ticker"):
            t = str(t)
            if t not in constants:
                constants[t] = float(g["shares_bs"].iloc[-1])

    dates = to_naive_timestamp(prices["date"]).drop_duplicates().sort_values()
    d0, d1 = dates.min(), dates.max()
    rows = []
    for t, sh in constants.items():
        rows.append({"date": d0, "ticker": t, "shares": sh})
        rows.append({"date": d1, "ticker": t, "shares": sh})
    hist = pd.DataFrame(rows)
    if len(hist):
        hist["date"] = to_naive_timestamp(hist["date"])
    return hist.dropna(subset=["shares"]).sort_values(["ticker", "date"])


def process_fundamentals(fund: pd.DataFrame) -> pd.DataFrame:
    f = fund.copy()
    if "_meta" in f.columns:
        f = f[f["_meta"] != True]
    f = f.dropna(subset=["period_end"], how="any")
    f["period_end"] = to_naive_timestamp(f["period_end"])
    keep = [c for c in ["ticker", "period_end", "book_equity", "net_income_q", "shares_bs", "statement_freq"] if c in f.columns]
    f = f[keep].drop_duplicates(subset=["ticker", "period_end"], keep="first")
    return f.sort_values(["ticker", "period_end"])

def enrich_sectors(sectors: pd.DataFrame, fund: pd.DataFrame) -> pd.DataFrame:
    s = sectors.copy()
    if "_meta" in fund.columns and "sector_yahoo" in fund.columns:
        y = fund[fund["_meta"] == True][["ticker", "sector_yahoo"]].dropna()
        y = y.drop_duplicates("ticker")
        s = s.merge(y, on="ticker", how="left")
        s["sector"] = s["sector"].fillna(s["sector_yahoo"]).fillna("Unknown")
    s["sector"] = s["sector"].fillna("Unknown")
    return s[["ticker", "sector"]].drop_duplicates("ticker")


def run_process() -> dict:
    cfg, root, prices, etf, rf, fund, sectors = load_raw()
    processed = root / cfg["paths"]["processed"]
    ensure_dirs(cfg)
    raw = root / cfg["paths"]["raw"]

    prices["date"] = to_naive_timestamp(prices["date"])
    etf["date"] = to_naive_timestamp(etf["date"])
    rf["date"] = to_naive_timestamp(rf["date"])

    fund_q = process_fundamentals(fund)
    shares = build_shares_panel(raw, fund, prices)
    sec = enrich_sectors(sectors, fund)

    # Coverage stats
    coverage = {
        "n_price_tickers": int(prices["ticker"].nunique()),
        "price_start": str(prices["date"].min().date()),
        "price_end": str(prices["date"].max().date()),
        "n_fund_tickers": int(fund_q["ticker"].nunique()),
        "n_shares_tickers": int(shares["ticker"].nunique()) if len(shares) else 0,
        "n_sectors": int(sec["sector"].nunique()),
        "pct_tickers_with_fundamentals": float(
            fund_q["ticker"].nunique() / max(prices["ticker"].nunique(), 1)
        ),
    }

    save_frame(prices, processed / "prices.pkl")
    save_frame(etf, processed / "etf_prices.pkl")
    save_frame(rf, processed / "risk_free.pkl")
    save_frame(fund_q, processed / "fundamentals_q.pkl")
    save_frame(shares, processed / "shares.pkl")
    sec.to_csv(processed / "sectors.csv", index=False)
    (processed / "coverage.json").write_text(json.dumps(coverage, indent=2))
    return coverage


if __name__ == "__main__":
    print(json.dumps(run_process(), indent=2))
