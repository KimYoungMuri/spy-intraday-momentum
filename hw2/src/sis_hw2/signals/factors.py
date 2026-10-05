"""Signal construction: value, quality, momentum and sector percentile ranks."""

from __future__ import annotations

import numpy as np
import pandas as pd


def month_end_dates(dates: pd.Series | pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.to_datetime(pd.Index(dates)).normalize()
    return pd.DatetimeIndex(sorted(s.to_series().groupby(s.to_period("M")).max().values))


def total_return(adj_close: pd.Series) -> pd.Series:
    return adj_close.pct_change()


def momentum_12_1(adj: pd.DataFrame, asof: pd.Timestamp) -> pd.Series:
    """
    Cumulative total return from t-12 months to t-1 month using Adj Close.

    mom_i = adj_{t-21} / adj_{t-252} - 1   (approx trading days)
    Requires both endpoints available.
    """
    # Use calendar offsets on available dates per ticker
    out = {}
    for ticker, g in adj.groupby("ticker"):
        g = g.sort_values("date").set_index("date")["adj_close"]
        # endpoint: last available on/before asof - 21 calendar days (~1m)
        end_cut = asof - pd.Timedelta(days=21)
        start_cut = asof - pd.Timedelta(days=365)
        g_end = g.loc[:end_cut]
        g_start = g.loc[:start_cut]
        if len(g_end) < 5 or len(g_start) < 5:
            out[ticker] = np.nan
            continue
        p1 = g_end.iloc[-1]
        # start: closest observation on/before start_cut, prefer ~12m before end
        p0 = g_start.iloc[-1]
        if p0 <= 0 or pd.isna(p0) or pd.isna(p1):
            out[ticker] = np.nan
        else:
            out[ticker] = p1 / p0 - 1.0
    return pd.Series(out, name="momentum")


def trailing_net_income(fund_q: pd.DataFrame, asof: pd.Timestamp, lag_days: int) -> pd.Series:
    """
    Trailing net income available by asof after lag.
    - If recent observations look quarterly (median gap <= 200d): sum up to 4.
    - If annual-spaced: use the latest single annual NI (do not sum 4 annuals).
    """
    f = fund_q.dropna(subset=["period_end"]).copy()
    f["available"] = f["period_end"] + pd.Timedelta(days=lag_days)
    f = f[f["available"] <= asof]
    out = {}
    for ticker, g in f.groupby("ticker"):
        g = g.sort_values("period_end")
        last = g.tail(4)
        ni = last["net_income_q"].dropna()
        if ni.empty:
            out[ticker] = np.nan
            continue
        gaps = last["period_end"].diff().dt.days.dropna()
        if len(gaps) and float(gaps.median()) > 200:
            out[ticker] = float(ni.iloc[-1])
        else:
            out[ticker] = float(ni.sum()) if len(ni) >= 1 else np.nan
    return pd.Series(out, name="ni_ttm")


def latest_book_equity(fund_q: pd.DataFrame, asof: pd.Timestamp, lag_days: int) -> pd.Series:
    f = fund_q.dropna(subset=["period_end"]).copy()
    f["available"] = f["period_end"] + pd.Timedelta(days=lag_days)
    f = f[f["available"] <= asof]
    out = {}
    for ticker, g in f.groupby("ticker"):
        g = g.sort_values("period_end")
        be = g["book_equity"].dropna()
        out[ticker] = be.iloc[-1] if len(be) else np.nan
    return pd.Series(out, name="book_equity")


def market_caps_on(prices: pd.DataFrame, shares: pd.DataFrame | None, asof: pd.Timestamp) -> pd.Series:
    """
    Market cap ≈ close * shares outstanding.
    If historical shares missing, forward-fill last known shares (disclosed approximation).
    """
    px = prices[prices["date"] <= asof].copy()
    last_px = px.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    price = last_px["close"].astype(float)
    if shares is None or shares.empty:
        return price * np.nan
    sh = shares[shares["date"] <= asof].sort_values("date").groupby("ticker").tail(1)
    sh = sh.set_index("ticker")["shares"].astype(float)
    return (price * sh).rename("market_cap")


def percentile_rank_within_sector(values: pd.Series, sectors: pd.Series, ascending: bool) -> pd.Series:
    """
    Higher rank = more attractive.
    ascending=True means higher raw value is better (quality, momentum).
    ascending=False means lower raw value is better — but for B/M, higher is cheaper/better,
    so ascending=True for value as B/M.
    """
    df = pd.DataFrame({"v": values, "sector": sectors}).dropna()
    ranks = []
    for sec, g in df.groupby("sector"):
        # percentile rank in [0,1]
        r = g["v"].rank(method="average", ascending=ascending, pct=True)
        ranks.append(r)
    if not ranks:
        return pd.Series(dtype=float, name="rank")
    return pd.concat(ranks).reindex(values.index)


def composite_score(ranks: pd.DataFrame, weights: list[float]) -> pd.Series:
    w = np.array(weights, dtype=float)
    w = w / w.sum()
    cols = ranks.columns.tolist()
    return (ranks[cols] * w).sum(axis=1, min_count=len(cols))


def build_signals_for_date(
    asof: pd.Timestamp,
    prices: pd.DataFrame,
    fund_q: pd.DataFrame,
    sector_map: pd.DataFrame,
    shares: pd.DataFrame | None,
    lag_days: int = 60,
    min_price: float = 5.0,
    min_adv: float = 1_000_000.0,
) -> pd.DataFrame:
    """Return cross-section of signals and eligibility flags at asof."""
    # eligibility window
    window = prices[(prices["date"] > asof - pd.Timedelta(days=40)) & (prices["date"] <= asof)]
    last = window.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    adv = (
        window.assign(dv=lambda x: x["close"] * x["volume"])
        .groupby("ticker")["dv"]
        .mean()
    )
    eligible_price = last["close"] >= min_price
    eligible_adv = adv >= min_adv

    mcap = market_caps_on(prices, shares, asof)
    be = latest_book_equity(fund_q, asof, lag_days)
    ni = trailing_net_income(fund_q, asof, lag_days)
    mom = momentum_12_1(prices, asof)

    sec = sector_map.set_index("ticker")["sector"]
    df = pd.DataFrame({
        "market_cap": mcap,
        "book_equity": be,
        "ni_ttm": ni,
        "close": last["close"],
        "adv_20d": adv,
        "momentum": mom,
        "sector": sec,
    })
    df["value_bm"] = df["book_equity"] / df["market_cap"]
    df["quality_roe"] = df["ni_ttm"] / df["book_equity"]
    df["eligible"] = (
        eligible_price.reindex(df.index).fillna(False)
        & eligible_adv.reindex(df.index).fillna(False)
        & df["book_equity"].gt(0)
        & df["market_cap"].gt(0)
        & df["value_bm"].notna()
        & df["quality_roe"].notna()
        & df["momentum"].notna()
        & df["sector"].notna()
    )
    # ranks among eligible only
    elig = df["eligible"]
    df["rank_value"] = np.nan
    df["rank_quality"] = np.nan
    df["rank_momentum"] = np.nan
    if elig.any():
        df.loc[elig, "rank_value"] = percentile_rank_within_sector(
            df.loc[elig, "value_bm"], df.loc[elig, "sector"], ascending=True
        )
        df.loc[elig, "rank_quality"] = percentile_rank_within_sector(
            df.loc[elig, "quality_roe"], df.loc[elig, "sector"], ascending=True
        )
        df.loc[elig, "rank_momentum"] = percentile_rank_within_sector(
            df.loc[elig, "momentum"], df.loc[elig, "sector"], ascending=True
        )
    df["asof"] = asof
    return df
