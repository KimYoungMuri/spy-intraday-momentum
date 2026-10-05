"""Signal construction: value, quality, momentum and sector percentile ranks."""

from __future__ import annotations

import numpy as np
import pandas as pd


def month_end_dates(dates: pd.Series | pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.to_datetime(pd.Index(dates)).normalize()
    return pd.DatetimeIndex(sorted(s.to_series().groupby(s.to_period("M")).max().values))


def _trading_calendar(prices: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(pd.to_datetime(prices["date"]).unique())).normalize()


def momentum_12_1(adj: pd.DataFrame, asof: pd.Timestamp, calendar: pd.DatetimeIndex | None = None) -> pd.Series:
    """
    12–1 momentum using trading-session endpoints on the shared calendar.

    End price: last adj_close on/before the session that is 21 trading days before asof.
    Start price: last adj_close on/before the session that is 252 trading days before asof.
    mom = P_end / P_start - 1
    """
    if calendar is None:
        calendar = _trading_calendar(adj)
    cal = calendar[calendar <= asof]
    if len(cal) < 253:
        return pd.Series(dtype=float, name="momentum")
    # locate asof in calendar
    pos = int(np.searchsorted(cal.values, np.datetime64(asof), side="right") - 1)
    if pos < 252:
        return pd.Series(dtype=float, name="momentum")
    end_dt = pd.Timestamp(cal[pos - 21])
    start_dt = pd.Timestamp(cal[pos - 252])

    wide = adj.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    # as-of prices
    def _px_on_or_before(dt):
        sub = wide.loc[:dt]
        if sub.empty:
            return pd.Series(dtype=float)
        return sub.ffill().iloc[-1]

    p1 = _px_on_or_before(end_dt)
    p0 = _px_on_or_before(start_dt)
    mom = p1 / p0 - 1.0
    mom[(p0 <= 0) | p0.isna() | p1.isna()] = np.nan
    return mom.rename("momentum")


def trailing_net_income(fund_q: pd.DataFrame, asof: pd.Timestamp, lag_days: int) -> pd.Series:
    """
    Trailing twelve-month net income from four consecutive quarterly observations.

    Requires four non-null quarterly NI values with quarter-like gaps.
    Returns NaN when quarterly TTM is unavailable (use annual_net_income separately).
    """
    f = fund_q.dropna(subset=["period_end"]).copy()
    f["available"] = f["period_end"] + pd.Timedelta(days=lag_days)
    f = f[f["available"] <= asof]
    out = {}
    for ticker, g in f.groupby("ticker"):
        g = g.sort_values("period_end")
        freq = g["statement_freq"].astype(str).str.lower() if "statement_freq" in g.columns else pd.Series("", index=g.index)
        gq = g[freq.isin(["quarterly", "q"])]
        if len(gq) < 4:
            out[ticker] = np.nan
            continue
        last4 = gq.tail(4)
        ni = last4["net_income_q"]
        if ni.notna().sum() < 4:
            out[ticker] = np.nan
            continue
        gaps = last4["period_end"].diff().dt.days.dropna()
        if len(gaps) and not ((gaps >= 60) & (gaps <= 140)).all():
            out[ticker] = np.nan
            continue
        out[ticker] = float(ni.sum())
    return pd.Series(out, name="ni_ttm")


def annual_net_income(fund_q: pd.DataFrame, asof: pd.Timestamp, lag_days: int) -> pd.Series:
    """Latest annual net income available by asof — labelled annual fallback, not TTM."""
    f = fund_q.dropna(subset=["period_end"]).copy()
    f["available"] = f["period_end"] + pd.Timedelta(days=lag_days)
    f = f[f["available"] <= asof]
    out = {}
    for ticker, g in f.groupby("ticker"):
        g = g.sort_values("period_end")
        freq = g["statement_freq"].astype(str).str.lower() if "statement_freq" in g.columns else pd.Series("", index=g.index)
        ga = g[freq.isin(["annual", "a", "yearly"])]
        # Also accept rows with ~365d spacing if freq missing
        if ga.empty:
            gaps = g["period_end"].diff().dt.days
            ga = g[gaps.isna() | (gaps > 200)]
        ni = ga["net_income_q"].dropna() if len(ga) else g["net_income_q"].dropna()
        # Prefer values that look annual in magnitude only if freq says annual
        if len(ga) and ga["net_income_q"].notna().any():
            out[ticker] = float(ga["net_income_q"].dropna().iloc[-1])
        else:
            out[ticker] = np.nan
    return pd.Series(out, name="ni_annual")


def latest_book_equity(fund_q: pd.DataFrame, asof: pd.Timestamp, lag_days: int) -> pd.Series:
    """Most recent book equity with availability = period_end + lag <= asof."""
    f = fund_q.dropna(subset=["period_end"]).copy()
    f["available"] = f["period_end"] + pd.Timedelta(days=lag_days)
    f = f[f["available"] <= asof]
    out = {}
    for ticker, g in f.groupby("ticker"):
        g = g.sort_values("period_end")
        be = g["book_equity"].dropna()
        out[ticker] = float(be.iloc[-1]) if len(be) else np.nan
    return pd.Series(out, name="book_equity")


def average_book_equity(fund_q: pd.DataFrame, asof: pd.Timestamp, lag_days: int) -> pd.Series:
    """
    Average of beginning and ending book equity over the TTM window when possible:
    mean of book equity 4 quarters ago and latest; else latest only.
    """
    f = fund_q.dropna(subset=["period_end", "book_equity"]).copy()
    f["available"] = f["period_end"] + pd.Timedelta(days=lag_days)
    f = f[f["available"] <= asof]
    out = {}
    for ticker, g in f.groupby("ticker"):
        g = g.sort_values("period_end")
        be = g["book_equity"].dropna()
        if len(be) >= 5:
            # approx start-of-TTM and end
            out[ticker] = float((be.iloc[-5] + be.iloc[-1]) / 2.0)
        elif len(be) >= 2:
            out[ticker] = float((be.iloc[0] + be.iloc[-1]) / 2.0)
        elif len(be) == 1:
            out[ticker] = float(be.iloc[-1])
        else:
            out[ticker] = np.nan
    return pd.Series(out, name="book_equity_avg")


def market_caps_on(prices: pd.DataFrame, shares: pd.DataFrame | None, asof: pd.Timestamp) -> pd.Series:
    """Market cap ≈ unadjusted close * shares outstanding as of asof (no future shares)."""
    px = prices[prices["date"] <= asof].copy()
    last_px = px.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    price = last_px["close"].astype(float)
    if shares is None or shares.empty:
        return (price * np.nan).rename("market_cap")
    sh = shares[shares["date"] <= asof].sort_values("date").groupby("ticker").tail(1)
    sh = sh.set_index("ticker")["shares"].astype(float)
    return (price * sh).rename("market_cap")


def adv_20_sessions(prices: pd.DataFrame, asof: pd.Timestamp, calendar: pd.DatetimeIndex) -> pd.Series:
    """Average dollar volume over exactly the preceding 20 trading sessions ending at asof."""
    cal = calendar[calendar <= asof]
    if len(cal) < 20:
        return pd.Series(dtype=float, name="adv_20d")
    window_dates = set(cal[-20:])
    w = prices[prices["date"].isin(window_dates)].copy()
    w["dv"] = w["close"].astype(float) * w["volume"].astype(float)
    # Require observations on the window; mean of available sessions
    return w.groupby("ticker")["dv"].mean().rename("adv_20d")


def percentile_rank_within_sector(values: pd.Series, sectors: pd.Series, ascending: bool = True) -> pd.Series:
    """Higher percentile = more attractive when ascending=True for the raw signal."""
    df = pd.DataFrame({"v": values, "sector": sectors}).dropna()
    ranks = []
    for _, g in df.groupby("sector"):
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
    n_universe: int = 500,
) -> pd.DataFrame:
    """
    Cross-section at asof.

    Eligibility uses unadjusted close and 20-session ADV.
    Ranks are computed **after** selecting the top-n_universe by market cap
    among filter-passing names (not on the broader panel).
    """
    calendar = _trading_calendar(prices)
    asof = pd.Timestamp(asof).normalize()

    px_hist = prices[prices["date"] <= asof]
    last = px_hist.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    adv = adv_20_sessions(prices, asof, calendar)

    mcap = market_caps_on(prices, shares, asof)
    be = latest_book_equity(fund_q, asof, lag_days)
    be_avg = average_book_equity(fund_q, asof, lag_days)
    ni_ttm = trailing_net_income(fund_q, asof, lag_days)
    ni_ann = annual_net_income(fund_q, asof, lag_days)
    mom = momentum_12_1(prices, asof, calendar)

    sec = sector_map.set_index("ticker")["sector"]
    df = pd.DataFrame(
        {
            "market_cap": mcap,
            "book_equity": be,
            "book_equity_avg": be_avg,
            "ni_ttm": ni_ttm,
            "ni_annual": ni_ann,
            "close": last["close"],
            "adv_20d": adv,
            "momentum": mom,
            "sector": sec,
        }
    )
    df["value_bm"] = df["book_equity"] / df["market_cap"]
    denom = df["book_equity_avg"].fillna(df["book_equity"])
    # Prefer true quarterly TTM; else labelled annual NI / book (NOT called TTM)
    df["quality_source"] = np.where(df["ni_ttm"].notna(), "ttm_4q", np.where(df["ni_annual"].notna(), "annual", "missing"))
    df["ni_for_quality"] = df["ni_ttm"].fillna(df["ni_annual"])
    df["quality_roe"] = df["ni_for_quality"] / denom

    filter_ok = (
        last["close"].ge(min_price).reindex(df.index).fillna(False)
        & adv.ge(min_adv).reindex(df.index).fillna(False)
        & df["book_equity"].gt(0)
        & df["market_cap"].gt(0)
        & df["value_bm"].notna()
        & df["quality_roe"].notna()
        & df["momentum"].notna()
        & df["sector"].notna()
    )
    df["filter_ok"] = filter_ok

    # Top-N by mcap among filter-ok, then rank within that set
    candidates = df[df["filter_ok"]].sort_values("market_cap", ascending=False).head(n_universe)
    df["in_universe"] = False
    df.loc[candidates.index, "in_universe"] = True
    df["eligible"] = df["in_universe"]  # eligible for ranking/selection = top-N universe

    df["rank_value"] = np.nan
    df["rank_quality"] = np.nan
    df["rank_momentum"] = np.nan
    if len(candidates):
        df.loc[candidates.index, "rank_value"] = percentile_rank_within_sector(
            candidates["value_bm"], candidates["sector"], ascending=True
        )
        df.loc[candidates.index, "rank_quality"] = percentile_rank_within_sector(
            candidates["quality_roe"], candidates["sector"], ascending=True
        )
        df.loc[candidates.index, "rank_momentum"] = percentile_rank_within_sector(
            candidates["momentum"], candidates["sector"], ascending=True
        )
    df["asof"] = asof
    return df
