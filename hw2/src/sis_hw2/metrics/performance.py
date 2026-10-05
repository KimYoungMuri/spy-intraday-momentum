"""Performance metrics with formulas matching the write-up."""

from __future__ import annotations

import numpy as np
import pandas as pd


def cumulative_returns(r: pd.Series) -> pd.Series:
    return (1 + r.fillna(0)).cumprod() - 1


def cagr(r: pd.Series, periods_per_year: float = 252.0) -> float:
    if r.empty:
        return np.nan
    wealth = (1 + r.fillna(0)).prod()
    years = len(r) / periods_per_year
    if years <= 0 or wealth <= 0:
        return np.nan
    return float(wealth ** (1 / years) - 1)


def ann_vol(r: pd.Series, periods_per_year: float = 252.0) -> float:
    if r.dropna().empty:
        return np.nan
    return float(r.std(ddof=1) * np.sqrt(periods_per_year))


def sharpe(r: pd.Series, rf_daily: pd.Series | float = 0.0, periods_per_year: float = 252.0) -> float:
    if isinstance(rf_daily, pd.Series):
        excess = r.subtract(rf_daily.reindex(r.index).ffill().fillna(0), fill_value=0)
    else:
        excess = r - rf_daily
    vol = ann_vol(excess, periods_per_year)
    if vol == 0 or np.isnan(vol):
        return np.nan
    return float(excess.mean() * periods_per_year / vol)


def max_drawdown(r: pd.Series) -> float:
    """Drawdown vs initial NAV=1 (peak starts at 1 before any returns)."""
    if r.empty:
        return np.nan
    w = (1 + r.fillna(0)).cumprod()
    wealth = pd.concat([pd.Series([1.0]), w], ignore_index=True)
    peak = wealth.cummax()
    dd = wealth / peak - 1
    return float(dd.min())


def tracking_error(r: pd.Series, b: pd.Series, periods_per_year: float = 252.0) -> float:
    aligned = pd.concat([r, b], axis=1, join="inner").dropna()
    if aligned.empty:
        return np.nan
    active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    return float(active.std(ddof=1) * np.sqrt(periods_per_year))


def information_ratio(r: pd.Series, b: pd.Series, periods_per_year: float = 252.0) -> float:
    aligned = pd.concat([r, b], axis=1, join="inner").dropna()
    if aligned.empty:
        return np.nan
    active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    te = active.std(ddof=1) * np.sqrt(periods_per_year)
    if te == 0 or np.isnan(te):
        return np.nan
    return float(active.mean() * periods_per_year / te)


def beta(r: pd.Series, b: pd.Series) -> float:
    aligned = pd.concat([r, b], axis=1, join="inner").dropna()
    if len(aligned) < 5:
        return np.nan
    cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
    if cov[1, 1] == 0:
        return np.nan
    return float(cov[0, 1] / cov[1, 1])


def annual_returns(r: pd.Series) -> pd.Series:
    if r.empty:
        return pd.Series(dtype=float)
    wealth = (1 + r.fillna(0))
    return wealth.groupby(r.index.year).prod() - 1


def summarize(r: pd.Series, benchmark: pd.Series | None = None, rf: pd.Series | float = 0.0) -> dict:
    out = {
        "cagr": cagr(r),
        "ann_vol": ann_vol(r),
        "sharpe": sharpe(r, rf),
        "max_drawdown": max_drawdown(r),
        "n_obs": int(r.dropna().shape[0]),
        "total_return": float((1 + r.fillna(0)).prod() - 1) if len(r) else np.nan,
    }
    if benchmark is not None:
        out["beta"] = beta(r, benchmark)
        out["tracking_error"] = tracking_error(r, benchmark)
        out["information_ratio"] = information_ratio(r, benchmark)
        out["active_cagr"] = cagr(r) - cagr(benchmark.reindex(r.index).fillna(0))
    return out


def format_summary_table(summaries: dict[str, dict]) -> pd.DataFrame:
    df = pd.DataFrame(summaries).T
    return df
