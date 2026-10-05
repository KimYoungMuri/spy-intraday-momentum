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
    """
    Latest *vendor-labelled* annual net income available by asof.
    Does not reclassify quarterly rows as annual via gap heuristics.
    """
    f = fund_q.dropna(subset=["period_end"]).copy()
    f["available"] = f["period_end"] + pd.Timedelta(days=lag_days)
    f = f[f["available"] <= asof]
    out = {}
    for ticker, g in f.groupby("ticker"):
        g = g.sort_values("period_end")
        freq = g["statement_freq"].astype(str).str.lower() if "statement_freq" in g.columns else pd.Series("", index=g.index)
        ga = g[freq.isin(["annual", "a", "yearly"])]
        ni = ga["net_income_q"].dropna()
        out[ticker] = float(ni.iloc[-1]) if len(ni) else np.nan
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


def average_book_equity_for_income_window(
    fund_q: pd.DataFrame,
    asof: pd.Timestamp,
    lag_days: int,
    income_start: pd.Series,
    income_end: pd.Series,
) -> pd.Series:
    """
    Period-matched average book equity:
    mean of book equity available at/just before income_start and at/just before income_end.
    Falls back to latest available book if window endpoints missing.
    """
    f = fund_q.dropna(subset=["period_end", "book_equity"]).copy()
    f["available"] = f["period_end"] + pd.Timedelta(days=lag_days)
    f = f[f["available"] <= asof]
    out = {}
    for ticker, g in f.groupby("ticker"):
        g = g.sort_values(["available", "period_end"])
        be_end = g["book_equity"].dropna()
        if be_end.empty:
            out[ticker] = np.nan
            continue
        end_cut = income_end.get(ticker, pd.NaT) if income_end is not None else pd.NaT
        start_cut = income_start.get(ticker, pd.NaT) if income_start is not None else pd.NaT
        g_end = g
        if pd.notna(end_cut):
            g_end = g[g["period_end"] <= pd.Timestamp(end_cut)]
        g_start = g
        if pd.notna(start_cut):
            g_start = g[g["period_end"] <= pd.Timestamp(start_cut)]
        b1 = g_end["book_equity"].dropna()
        b0 = g_start["book_equity"].dropna()
        if len(b1) and len(b0):
            out[ticker] = float((b0.iloc[-1] + b1.iloc[-1]) / 2.0)
        elif len(b1):
            out[ticker] = float(b1.iloc[-1])
        else:
            out[ticker] = np.nan
    return pd.Series(out, name="book_equity_avg")


def income_window_endpoints(
    fund_q: pd.DataFrame, asof: pd.Timestamp, lag_days: int, mode: str
) -> tuple[pd.Series, pd.Series]:
    """Return (period_end_start, period_end_end) for the income measure used."""
    f = fund_q.dropna(subset=["period_end"]).copy()
    f["available"] = f["period_end"] + pd.Timedelta(days=lag_days)
    f = f[f["available"] <= asof]
    starts, ends = {}, {}
    for ticker, g in f.groupby("ticker"):
        g = g.sort_values("period_end")
        freq = g["statement_freq"].astype(str).str.lower() if "statement_freq" in g.columns else pd.Series("", index=g.index)
        if mode == "ttm_4q":
            gq = g[freq.isin(["quarterly", "q"])]
            if len(gq) >= 4 and gq["net_income_q"].tail(4).notna().all():
                last4 = gq.tail(4)
                starts[ticker] = last4["period_end"].iloc[0]
                ends[ticker] = last4["period_end"].iloc[-1]
        else:  # annual
            ga = g[freq.isin(["annual", "a", "yearly"])]
            ni = ga.dropna(subset=["net_income_q"])
            if len(ni):
                ends[ticker] = ni["period_end"].iloc[-1]
                starts[ticker] = ni["period_end"].iloc[-1]
    return pd.Series(starts, name="inc_start"), pd.Series(ends, name="inc_end")


def market_caps_on(
    prices: pd.DataFrame, shares: pd.DataFrame | None, asof: pd.Timestamp
) -> tuple[pd.Series, pd.Series]:
    """Market cap ≈ unadjusted close * shares with date<=asof. Returns (mcap, shares_source)."""
    px = prices[prices["date"] <= asof].copy()
    last_px = px.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    price = last_px["close"].astype(float)
    if shares is None or shares.empty:
        return (price * np.nan).rename("market_cap"), pd.Series(dtype=str)
    sh = shares[shares["date"] <= asof].sort_values("date").groupby("ticker").tail(1)
    src = sh.set_index("ticker")["source"] if "source" in sh.columns else pd.Series("unknown", index=sh["ticker"])
    shv = sh.set_index("ticker")["shares"].astype(float)
    # Exclude constant_latest from baseline mcap (mark missing so name fails eligibility)
    ok = ~src.astype(str).eq("constant_latest") if len(src) else shv.notna()
    mcap = (price * shv.where(ok)).rename("market_cap")
    return mcap, src.reindex(mcap.index).rename("shares_source")


def adv_20_sessions(prices: pd.DataFrame, asof: pd.Timestamp, calendar: pd.DatetimeIndex) -> pd.Series:
    """ADV over preceding 20 trading sessions; requires all 20 observations."""
    cal = calendar[calendar <= asof]
    if len(cal) < 20:
        return pd.Series(dtype=float, name="adv_20d")
    window_dates = list(cal[-20:])
    w = prices[prices["date"].isin(window_dates)].copy()
    w["dv"] = w["close"].astype(float) * w["volume"].astype(float)
    counts = w.groupby("ticker")["dv"].count()
    means = w.groupby("ticker")["dv"].mean()
    means = means.where(counts >= 20)
    return means.rename("adv_20d")


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
    quality_mode: str = "annual_labelled",
) -> pd.DataFrame:
    """
    Cross-section at asof.

    quality_mode:
      - 'ttm_4q': require valid 4-quarter TTM (exclude names without it)
      - 'annual_labelled': require vendor-labelled annual NI (Yahoo exploratory baseline)
      - 'mixed_reported': prefer TTM else annual; exposes quality_source weights (not frozen baseline)
    """
    calendar = _trading_calendar(prices)
    asof = pd.Timestamp(asof).normalize()

    px_hist = prices[prices["date"] <= asof]
    last = px_hist.sort_values("date").groupby("ticker").tail(1).set_index("ticker")
    adv = adv_20_sessions(prices, asof, calendar)

    mcap, shares_source = market_caps_on(prices, shares, asof)
    be = latest_book_equity(fund_q, asof, lag_days)
    ni_ttm = trailing_net_income(fund_q, asof, lag_days)
    ni_ann = annual_net_income(fund_q, asof, lag_days)

    if quality_mode == "ttm_4q":
        start_ep, end_ep = income_window_endpoints(fund_q, asof, lag_days, "ttm_4q")
        ni = ni_ttm
        qsrc = np.where(ni_ttm.notna(), "ttm_4q", "missing")
    elif quality_mode == "annual_labelled":
        start_ep, end_ep = income_window_endpoints(fund_q, asof, lag_days, "annual")
        ni = ni_ann
        qsrc = np.where(ni_ann.notna(), "annual", "missing")
    else:
        start_ep, end_ep = income_window_endpoints(fund_q, asof, lag_days, "ttm_4q")
        # for mixed, book window uses TTM endpoints when present else annual
        ni = ni_ttm.fillna(ni_ann)
        qsrc = np.where(ni_ttm.notna(), "ttm_4q", np.where(ni_ann.notna(), "annual", "missing"))
        # rebuild endpoints for annual names
        s2, e2 = income_window_endpoints(fund_q, asof, lag_days, "annual")
        start_ep = start_ep.combine_first(s2)
        end_ep = end_ep.combine_first(e2)

    be_avg = average_book_equity_for_income_window(fund_q, asof, lag_days, start_ep, end_ep)
    mom = momentum_12_1(prices, asof, calendar)

    sec = sector_map.set_index("ticker")["sector"]
    df = pd.DataFrame(
        {
            "market_cap": mcap,
            "book_equity": be,
            "book_equity_avg": be_avg,
            "ni_ttm": ni_ttm,
            "ni_annual": ni_ann,
            "ni_for_quality": ni,
            "close": last["close"],
            "adv_20d": adv,
            "momentum": mom,
            "sector": sec,
            "shares_source": shares_source,
        }
    )
    df["quality_source"] = pd.Series(qsrc, index=ni.index).reindex(df.index).fillna("missing")
    df["value_bm"] = df["book_equity"] / df["market_cap"]
    denom = df["book_equity_avg"].fillna(df["book_equity"])
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
        & df["quality_source"].ne("missing")
    )
    # For single-factor momentum/value, quality may be optional — handled by caller via ranks
    if quality_mode in ("ttm_4q", "annual_labelled", "mixed_reported"):
        pass
    df["filter_ok"] = filter_ok

    candidates = df[df["filter_ok"]].sort_values("market_cap", ascending=False).head(n_universe)
    df["in_universe"] = False
    df.loc[candidates.index, "in_universe"] = True
    df["eligible"] = df["in_universe"]

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
    df["quality_mode"] = quality_mode
    return df
