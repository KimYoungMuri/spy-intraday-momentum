"""Universe construction: research ticker panel (not historical S&P 500)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from sis_hw2.utils.config import project_root, load_config, ensure_dirs

UA = {
    "User-Agent": "sis-hw2-research/0.1 (academic coursework; contact: student)",
}


def fetch_wikipedia_table(url: str, match: str | None = None) -> pd.DataFrame:
    headers = {"User-Agent": UA["User-Agent"]}
    # pandas read_html may need lxml; pass headers via requests
    html = requests.get(url, headers=headers, timeout=60).text
    tables = pd.read_html(html)
    if match is None:
        return tables[0]
    for t in tables:
        cols = " ".join(map(str, t.columns)).lower()
        if match.lower() in cols:
            return t
    return tables[0]


def get_sp500_tickers() -> pd.DataFrame:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = fetch_wikipedia_table(url, match="Symbol")
    # normalize columns
    colmap = {}
    for c in df.columns:
        cl = str(c).lower()
        if "symbol" in cl:
            colmap[c] = "ticker"
        elif "security" in cl or "company" in cl:
            colmap[c] = "name"
        elif "gics sector" in cl:
            colmap[c] = "sector"
        elif "gics sub" in cl:
            colmap[c] = "industry"
        elif "date added" in cl:
            colmap[c] = "date_added"
        elif "cik" in cl:
            colmap[c] = "cik"
    df = df.rename(columns=colmap)
    df["ticker"] = df["ticker"].astype(str).str.replace(".", "-", regex=False)
    df["source"] = "wikipedia_sp500_current"
    return df[["ticker", "name", "sector", "industry"]].drop_duplicates("ticker")


def get_sp400_tickers() -> pd.DataFrame:
    """Optional mid-cap expansion; fail soft if Wikipedia structure changes."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
    try:
        df = fetch_wikipedia_table(url, match="Symbol")
    except Exception:
        return pd.DataFrame(columns=["ticker", "name", "sector", "industry", "source"])
    colmap = {}
    for c in df.columns:
        cl = str(c).lower()
        if "symbol" in cl or cl == "ticker":
            colmap[c] = "ticker"
        elif "security" in cl or "company" in cl:
            colmap[c] = "name"
        elif "gics sector" in cl or cl == "sector":
            colmap[c] = "sector"
        elif "gics sub" in cl or "industry" in cl:
            colmap[c] = "industry"
    df = df.rename(columns=colmap)
    if "ticker" not in df.columns:
        return pd.DataFrame(columns=["ticker", "name", "sector", "industry", "source"])
    df["ticker"] = df["ticker"].astype(str).str.replace(".", "-", regex=False)
    for col in ["name", "sector", "industry"]:
        if col not in df.columns:
            df[col] = "Unknown"
    df["source"] = "wikipedia_sp400_current"
    return df[["ticker", "name", "sector", "industry", "source"]].drop_duplicates("ticker")


def build_research_panel(include_midcap: bool = True) -> pd.DataFrame:
    """
    Build the *research ticker panel*.

    CRITICAL DISCLOSURE:
    - Constituents are taken from *current* lists (retrieval date recorded).
    - This is NOT the historical S&P 500 and embeds survivorship / membership bias.
    - At each rebalance we still select the top N by contemporaneous market cap
      among this panel only — a restricted eligible universe, not CRSP top-500.
    """
    # Prefer GitHub datasets mirror (more automation-friendly than Wikipedia)
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        df = pd.read_csv(url)
        colmap = {
            "Symbol": "ticker",
            "Security": "name",
            "GICS Sector": "sector",
            "GICS Sub-Industry": "industry",
        }
        df = df.rename(columns=colmap)
        df["ticker"] = df["ticker"].astype(str).str.replace(".", "-", regex=False)
        df["source"] = "github_datasets_sp500_current"
        sp500 = df[["ticker", "name", "sector", "industry", "source"]].drop_duplicates("ticker")
    except Exception:
        sp500 = get_sp500_tickers()
    frames = [sp500]
    if include_midcap:
        sp400 = get_sp400_tickers()
        if len(sp400):
            frames.append(sp400)
    panel = pd.concat(frames, ignore_index=True)
    panel = panel.drop_duplicates("ticker", keep="first").reset_index(drop=True)
    panel["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    return panel


def save_universe(panel: pd.DataFrame | None = None, refresh: bool = False) -> Path:
    ensure_dirs()
    cfg = load_config()
    root = project_root()
    raw = root / cfg["paths"]["raw"]
    out = raw / "research_ticker_panel.csv"
    if out.exists() and panel is None and not refresh:
        return out
    if panel is None:
        panel = build_research_panel(False)  # S&P500-panel only for tractability
    panel.to_csv(out, index=False)
    meta = {
        "n_tickers": int(len(panel)),
        "retrieved_at_utc": str(panel["retrieved_at_utc"].iloc[0]),
        "sources": sorted(panel["source"].dropna().unique().tolist())
        if "source" in panel.columns
        else ["github_datasets_sp500_current"],
        "warning": (
            "Current constituents used as research panel only. "
            "Not historical S&P 500. Survivorship and membership bias present."
        ),
    }
    (raw / "universe_meta.json").write_text(json.dumps(meta, indent=2))
    # keep sector map in sync
    if "sector" in panel.columns:
        panel[["ticker", "sector"]].assign(sector_source="panel_current").to_csv(
            raw / "sector_map.csv", index=False
        )
    return out


if __name__ == "__main__":
    p = save_universe()
    print(f"Saved universe panel to {p}")
