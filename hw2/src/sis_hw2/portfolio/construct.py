"""Portfolio construction: sector-weight matched to eligible universe at rebalance."""

from __future__ import annotations

import numpy as np
import pandas as pd

from sis_hw2.signals.factors import composite_score


def select_universe_top_n(signals: pd.DataFrame, n: int = 500) -> pd.DataFrame:
    if "in_universe" in signals.columns and signals["in_universe"].any():
        return signals.loc[signals["in_universe"]].copy()
    col = "eligible" if "eligible" in signals.columns else "filter_ok"
    elig = signals.loc[signals[col]].copy()
    return elig.sort_values("market_cap", ascending=False).head(n)


def select_top_pct_within_sector(
    elig: pd.DataFrame, score: pd.Series, pct: float = 0.20
) -> pd.Index:
    """
    Select ceil(n_sector * pct) names per sector (min 1 if sector non-empty).
    Tie-break: higher score, then higher market_cap, then ticker A→Z.
    """
    chosen: list = []
    tmp = elig.copy()
    tmp["score"] = score.reindex(tmp.index)
    tmp = tmp.dropna(subset=["score"])
    tmp["ticker_key"] = tmp.index.astype(str)
    for _, g in tmp.groupby("sector", sort=True):
        k = max(1, int(np.ceil(len(g) * pct)))
        ordered = g.sort_values(
            ["score", "market_cap", "ticker_key"], ascending=[False, False, True]
        )
        chosen.extend(ordered.head(k).index.tolist())
    return pd.Index(chosen)


def sector_benchmark_weights(elig: pd.DataFrame) -> pd.Series:
    sec_cap = elig.groupby("sector")["market_cap"].sum()
    return (sec_cap / sec_cap.sum()).rename("sector_weight")


def build_target_weights(
    signals: pd.DataFrame,
    n_universe: int = 500,
    selection_pct: float = 0.20,
    composite_weights: list[float] | None = None,
    single_factor: str | None = None,
) -> pd.Series:
    """
    Sector weights match eligible-universe cap sector weights at rebalance;
    equal-weight selected names within each sector.

    Not continuous market neutrality or SPY-sector neutrality between rebalances.
    """
    composite_weights = composite_weights or [1 / 3, 1 / 3, 1 / 3]
    elig = select_universe_top_n(signals, n_universe)
    if elig.empty:
        return pd.Series(dtype=float)

    if single_factor == "value":
        score = elig["rank_value"]
    elif single_factor == "quality":
        score = elig["rank_quality"]
    elif single_factor == "momentum":
        score = elig["rank_momentum"]
    else:
        ranks = elig[["rank_value", "rank_quality", "rank_momentum"]]
        score = composite_score(ranks, composite_weights)

    picks = select_top_pct_within_sector(elig, score, selection_pct)
    port = elig.loc[picks]
    if port.empty:
        return pd.Series(dtype=float)

    sec_w = sector_benchmark_weights(elig)
    weights = {}
    for sec, g in port.groupby("sector"):
        sw = float(sec_w.get(sec, 0.0))
        if sw <= 0 or len(g) == 0:
            continue
        w_each = sw / len(g)
        for t in g.index:
            weights[t] = w_each
    w = pd.Series(weights, dtype=float)
    if w.sum() > 0:
        w = w / w.sum()
    return w.rename("weight")


def cap_weighted_universe(signals: pd.DataFrame, n_universe: int = 500) -> pd.Series:
    elig = select_universe_top_n(signals, n_universe)
    if elig.empty:
        return pd.Series(dtype=float)
    w = elig["market_cap"] / elig["market_cap"].sum()
    return w.rename("weight")
