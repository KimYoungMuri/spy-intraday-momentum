"""Backtest engine with drift, costs, and fees."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from sis_hw2.portfolio.construct import build_target_weights, cap_weighted_universe
from sis_hw2.signals.factors import build_signals_for_date, month_end_dates


@dataclass
class BacktestResult:
    name: str
    returns: pd.Series
    weights_history: list[dict] = field(default_factory=list)
    turnover: pd.Series = field(default_factory=pd.Series)
    holdings_log: pd.DataFrame = field(default_factory=pd.DataFrame)
    meta: dict = field(default_factory=dict)


def _daily_returns_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    wide = prices.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    return wide.pct_change()


def _rebalance_dates(price_dates: pd.DatetimeIndex, start: str, end: str, freq: str = "M") -> pd.DatetimeIndex:
    me = month_end_dates(price_dates)
    me = me[(me >= pd.Timestamp(start)) & (me <= pd.Timestamp(end))]
    if freq.upper().startswith("Q"):
        # last month-end of each quarter
        s = pd.Series(me, index=me)
        me = pd.DatetimeIndex(s.groupby(me.to_period("Q")).max().values)
    return me


def run_backtest(
    name: str,
    prices: pd.DataFrame,
    fund_q: pd.DataFrame,
    sector_map: pd.DataFrame,
    shares: pd.DataFrame | None,
    start: str,
    end: str,
    first_rebalance: str,
    n_universe: int = 500,
    selection_pct: float = 0.20,
    composite_weights: list[float] | None = None,
    single_factor: str | None = None,
    lag_days: int = 60,
    cost_bps_per_side: float = 5.0,
    mgmt_fee_bps_annual: float = 0.0,
    rebalance_freq: str = "M",
    min_price: float = 5.0,
    min_adv: float = 1_000_000.0,
    universe_cap_weight: bool = False,
) -> BacktestResult:
    """
    Monthly (or quarterly) rebalance long-only backtest.

    Timing:
    - Signals formed using data available as of rebalance date close.
    - Trades assumed at rebalance close; returns accrue from next day.
    - Between rebalances, weights drift with relative price moves.
    - Transaction cost charged on turnover: cost = turnover * bps_per_side/1e4
      (one-way; buys+sells both charged — i.e. sum(|Δw|)*bps/1e4).
    """
    rets = _daily_returns_matrix(prices)
    dates = rets.index
    reb_dates = _rebalance_dates(dates, first_rebalance, end, rebalance_freq)
    reb_dates = reb_dates[reb_dates >= pd.Timestamp(first_rebalance)]

    w = pd.Series(dtype=float)
    daily = []
    turn_rows = []
    hold_rows = []
    cost_rate = cost_bps_per_side / 10_000.0
    fee_daily = (mgmt_fee_bps_annual / 10_000.0) / 252.0

    reb_set = set(reb_dates)
    pending_cost = 0.0

    for i, dt in enumerate(dates):
        if dt < pd.Timestamp(start) or dt > pd.Timestamp(end):
            continue
        # Apply pending trade cost on rebalance day (end of day)
        day_ret = 0.0
        if len(w):
            r = rets.loc[dt].reindex(w.index).fillna(0.0)
            # drift
            w = w * (1.0 + r)
            if w.sum() > 0:
                port_r = float((w / w.sum() * r).sum())
                w = w / w.sum()
            else:
                port_r = 0.0
            day_ret = port_r
        else:
            day_ret = 0.0

        if dt in reb_set:
            sig = build_signals_for_date(
                dt, prices, fund_q, sector_map, shares,
                lag_days=lag_days, min_price=min_price, min_adv=min_adv,
            )
            if universe_cap_weight:
                target = cap_weighted_universe(sig, n_universe)
            else:
                target = build_target_weights(
                    sig, n_universe, selection_pct, composite_weights, single_factor
                )
            # Align
            all_idx = sorted(set(w.index) | set(target.index))
            w_old = w.reindex(all_idx).fillna(0.0)
            w_new = target.reindex(all_idx).fillna(0.0)
            turnover = float((w_old - w_new).abs().sum())  # one-way sum of absolute weight changes
            # Standard: 0.5 * L1 is two-way normalized; we report L1/2 as one-way turnover
            one_way_turnover = turnover / 2.0
            trade_cost = turnover * cost_rate  # charge both sides at per-side bps
            day_ret = day_ret - trade_cost - fee_daily
            w = w_new[w_new > 0].copy()
            turn_rows.append({"date": dt, "turnover_one_way": one_way_turnover, "trade_cost": trade_cost, "n_holdings": int((w > 0).sum())})
            for t, wt in w.items():
                hold_rows.append({"date": dt, "ticker": t, "weight": float(wt)})
        else:
            if len(w):
                day_ret = day_ret - fee_daily

        if dt >= pd.Timestamp(first_rebalance):
            daily.append({"date": dt, "ret": day_ret})

    ret_s = pd.DataFrame(daily).set_index("date")["ret"] if daily else pd.Series(dtype=float)
    turn_s = pd.DataFrame(turn_rows).set_index("date")["turnover_one_way"] if turn_rows else pd.Series(dtype=float)
    holds = pd.DataFrame(hold_rows)
    return BacktestResult(
        name=name,
        returns=ret_s,
        turnover=turn_s,
        holdings_log=holds,
        meta={
            "cost_bps_per_side": cost_bps_per_side,
            "mgmt_fee_bps_annual": mgmt_fee_bps_annual,
            "selection_pct": selection_pct,
            "lag_days": lag_days,
            "rebalance_freq": rebalance_freq,
            "n_universe": n_universe,
            "single_factor": single_factor,
            "universe_cap_weight": universe_cap_weight,
        },
    )


def portfolio_from_etf_weights(
    etf_prices: pd.DataFrame,
    weights: dict[str, float],
    start: str,
    end: str,
    cost_bps_per_side: float = 0.0,
    rebalance: str = "M",
    name: str = "etf_proxy",
) -> BacktestResult:
    """Labeled ETF proxy: monthly rebalanced mix of factor ETFs."""
    wide = etf_prices.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    rets = wide.pct_change()
    tickers = list(weights.keys())
    rets = rets[tickers].dropna(how="all")
    me = month_end_dates(rets.index)
    me = me[(me >= pd.Timestamp(start)) & (me <= pd.Timestamp(end))]
    w = pd.Series(weights, dtype=float)
    w = w / w.sum()
    daily = []
    turns = []
    cost_rate = cost_bps_per_side / 10_000.0
    reb = set(me)
    cur = None
    for dt, row in rets.iterrows():
        if dt < pd.Timestamp(start) or dt > pd.Timestamp(end):
            continue
        if cur is None:
            if dt in reb or dt >= me.min():
                cur = w.copy()
            else:
                continue
        r = row.reindex(cur.index).fillna(0.0)
        cur = cur * (1 + r)
        port_r = float((cur / cur.sum() * r).sum())
        cur = cur / cur.sum()
        if dt in reb:
            target = w.reindex(cur.index).fillna(0.0)
            # also include target tickers
            all_idx = sorted(set(cur.index) | set(w.index))
            old = cur.reindex(all_idx).fillna(0.0)
            new = w.reindex(all_idx).fillna(0.0)
            turnover = float((old - new).abs().sum())
            port_r -= turnover * cost_rate
            cur = w.copy()
            turns.append({"date": dt, "turnover_one_way": turnover / 2.0})
        daily.append({"date": dt, "ret": port_r})
    ret_s = pd.DataFrame(daily).set_index("date")["ret"]
    turn_s = pd.DataFrame(turns).set_index("date")["turnover_one_way"] if turns else pd.Series(dtype=float)
    return BacktestResult(name=name, returns=ret_s, turnover=turn_s, meta={"proxy": True, "weights": weights})
