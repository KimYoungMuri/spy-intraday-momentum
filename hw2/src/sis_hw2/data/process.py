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

    Priority:
    1. Historical share observations from data/raw/shares_all.pkl or shares/*.csv
       (date <= asof when used — no future backfill in the signal layer).
    2. Balance-sheet share counts by period_end (treated as available with same lag
       elsewhere; here dated at period_end for as-of merge).
    3. ONLY if no history: constant latest sharesOutstanding, flagged in coverage.

    Never apply a future share count to an earlier date when history exists.
    """
    frames = []
    shares_all = raw / "shares_all.pkl"
    if shares_all.exists():
        try:
            df = load_frame(shares_all)
            df["date"] = to_naive_timestamp(df["date"])
            frames.append(df[["date", "ticker", "shares"]].dropna())
        except Exception:
            pass
    sh_dir = raw / "shares"
    if sh_dir.exists():
        for p in sh_dir.glob("*.csv"):
            try:
                df = pd.read_csv(p)
                if "date" not in df.columns or "shares" not in df.columns:
                    continue
                df["date"] = to_naive_timestamp(df["date"])
                if "ticker" not in df.columns:
                    df["ticker"] = p.stem
                frames.append(df[["date", "ticker", "shares"]].dropna())
            except Exception:
                continue

    # BS share lines dated at period_end
    if "shares_bs" in fund.columns:
        bs = fund.dropna(subset=["shares_bs", "period_end"]).copy()
        if len(bs):
            bs = bs.assign(
                date=to_naive_timestamp(bs["period_end"]),
                shares=bs["shares_bs"].astype(float),
            )[["date", "ticker", "shares"]]
            frames.append(bs)

    hist = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "ticker", "shares"])
    if len(hist):
        hist["ticker"] = hist["ticker"].astype(str)
        hist = hist.dropna(subset=["shares", "date"])
        hist = hist.sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"], keep="last")

    have = set(hist["ticker"].unique()) if len(hist) else set()
    meta = fund[fund["_meta"] == True].copy() if "_meta" in fund.columns else pd.DataFrame()
    constants = {}
    if len(meta) and "shares_latest" in meta.columns:
        for _, row in meta.dropna(subset=["shares_latest"]).iterrows():
            constants[str(row["ticker"])] = float(row["shares_latest"])

    # Constant fallback only for tickers lacking any history
    dates = to_naive_timestamp(prices["date"]).drop_duplicates().sort_values()
    d0, d1 = dates.min(), dates.max()
    fill_rows = []
    for t, sh in constants.items():
        if t in have:
            continue
        fill_rows.append({"date": d0, "ticker": t, "shares": sh, "source": "constant_latest"})
        fill_rows.append({"date": d1, "ticker": t, "shares": sh, "source": "constant_latest"})
    if fill_rows:
        hist = pd.concat([hist.assign(source="historical"), pd.DataFrame(fill_rows)], ignore_index=True)
    elif len(hist) and "source" not in hist.columns:
        hist["source"] = "historical"

    hist["date"] = to_naive_timestamp(hist["date"])
    return hist.dropna(subset=["shares"]).sort_values(["ticker", "date"])


def process_fundamentals(fund: pd.DataFrame) -> pd.DataFrame:
    f = fund.copy()
    if "_meta" in f.columns:
        f = f[f["_meta"] != True]
    f = f.dropna(subset=["period_end"], how="any")
    f["period_end"] = to_naive_timestamp(f["period_end"])
    # Preserve vendor statement_freq when present (A/Q/annual/quarterly)
    if "statement_freq" not in f.columns:
        f["statement_freq"] = np.nan
    mapped = f["statement_freq"].astype(str).str.upper()
    f.loc[mapped.isin(["A", "ANNUAL", "YEARLY"]), "statement_freq"] = "annual"
    f.loc[mapped.isin(["Q", "QUARTERLY"]), "statement_freq"] = "quarterly"
    # Infer only where still unknown/nan/meta
    rows = []
    for ticker, g in f.groupby("ticker"):
        g = g.sort_values("period_end").copy()
        gaps = g["period_end"].diff().dt.days
        freqs = []
        for i, (freq, gap) in enumerate(zip(g["statement_freq"], gaps)):
            fl = str(freq).lower() if pd.notna(freq) else ""
            if fl in ("annual", "quarterly"):
                freqs.append(fl)
            elif i == 0:
                freqs.append("unknown")
            elif pd.isna(gap):
                freqs.append("unknown")
            elif 60 <= gap <= 140:
                freqs.append("quarterly")
            elif gap > 200:
                freqs.append("annual")
            else:
                freqs.append("unknown")
        g["statement_freq"] = freqs
        rows.append(g)
    f = pd.concat(rows, ignore_index=True) if rows else f
    keep = [
        c
        for c in ["ticker", "period_end", "book_equity", "net_income_q", "shares_bs", "statement_freq"]
        if c in f.columns
    ]
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

    n_const = int((shares.get("source", pd.Series(dtype=str)) == "constant_latest").sum() // 2) if len(shares) else 0
    coverage = {
        "n_price_tickers": int(prices["ticker"].nunique()),
        "price_start": str(prices["date"].min().date()),
        "price_end": str(prices["date"].max().date()),
        "n_fund_tickers": int(fund_q["ticker"].nunique()),
        "n_shares_tickers": int(shares["ticker"].nunique()) if len(shares) else 0,
        "n_shares_constant_fallback_tickers": n_const,
        "n_sectors": int(sec["sector"].nunique()),
        "pct_tickers_with_fundamentals": float(
            fund_q["ticker"].nunique() / max(prices["ticker"].nunique(), 1)
        ),
        "shares_policy": "historical_preferred_constant_latest_fallback",
        "sector_policy": "current_labels_applied_historically",
        "label": "BIASED_EXPLORATORY_YAHOO_CURRENT_CONSTITUENT_PANEL",
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
