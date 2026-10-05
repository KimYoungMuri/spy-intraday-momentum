"""Backtest engine with explicit missing-data and approximate cost accounting."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from sis_hw2.portfolio.construct import (
    build_target_weights,
    cap_weighted_universe,
    sector_equal_universe,
)
from sis_hw2.signals.factors import build_signals_for_date, month_end_dates


@dataclass
class BacktestResult:
    name: str
    returns: pd.Series
    weights_history: list[dict] = field(default_factory=list)
    turnover: pd.Series = field(default_factory=pd.Series)
    holdings_log: pd.DataFrame = field(default_factory=pd.DataFrame)
    missing_return_weight: pd.Series = field(default_factory=pd.Series)
    meta: dict = field(default_factory=dict)


def portfolio_return_and_drift(
    weights: pd.Series,
    asset_returns: pd.Series,
    missing_policy: str = "halt_zero_flagged",
) -> tuple[float, pd.Series, float]:
    """
    Beginning-of-period weights w, asset returns r:
      R_p = sum w_i * r_i
      w'_i = w_i * (1+r_i) / (1+R_p)

    Missing held returns (NaN with w>0):
      halt_zero_flagged — that name contributes 0 return for the day (halt-like),
      weight is flagged and still drifts with r=0; NOT a silent fill of prices.
    Returns (port_r, drifted_weights, missing_weight_fraction).
    """
    w = weights.astype(float).copy()
    if w.sum() <= 0:
        return 0.0, w, 0.0
    w = w / w.sum()
    r = asset_returns.reindex(w.index).astype(float)
    missing_mask = r.isna() & (w > 1e-12)
    missing_w = float(w[missing_mask].sum())
    if missing_policy == "halt_zero_flagged":
        r = r.copy()
        r.loc[missing_mask] = 0.0
        r = r.fillna(0.0)  # zero-weight names only
    else:
        raise ValueError(missing_policy)
    port_r = float((w * r).sum())
    denom = 1.0 + port_r
    if abs(denom) < 1e-15:
        drifted = w.copy()
    else:
        drifted = w * (1.0 + r) / denom
    if drifted.sum() > 0:
        drifted = drifted / drifted.sum()
    return port_r, drifted, missing_w


def _daily_returns_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Explicit: no fill of missing prices before pct_change."""
    wide = prices.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    # pandas>=2.1: fill_method default removed; be explicit
    try:
        return wide.pct_change(fill_method=None)
    except TypeError:
        return wide.pct_change()


def _rebalance_dates(
    price_dates: pd.DatetimeIndex, start: str, end: str, freq: str = "M"
) -> pd.DatetimeIndex:
    me = month_end_dates(price_dates)
    me = me[(me >= pd.Timestamp(start)) & (me <= pd.Timestamp(end))]
    if freq.upper().startswith("Q"):
        s = pd.Series(me, index=me)
        me = pd.DatetimeIndex(s.groupby(me.to_period("Q")).max().values)
    return me


def _next_session(dates: pd.DatetimeIndex, signal_dt: pd.Timestamp) -> pd.Timestamp | None:
    later = dates[dates > signal_dt]
    if len(later) == 0:
        return None
    return pd.Timestamp(later[0])


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
    universe_sector_equal: bool = False,
    execution: str = "next_close",
    quality_mode: str = "annual_labelled",
) -> BacktestResult:
    """
    Event sequence (execution='next_close'):
    1. Signals at month-end close T.
    2. Existing book earns return through next session close T+1.
    3. Rebalance at T+1 close.
    4. Cost model is a PROPORTIONAL APPROXIMATION:
         trade_cost ≈ L1 * (bps_per_side/1e4)
         net_growth ≈ (1+R_p)*(1-trade_cost)*(1-fee_daily) - 1
       Not exact self-financing cash accounting with discrete share lots.

    Returns are recorded only from the first execution close onward
    (no strategy NAV before initial close fill).
    """
    rets = _daily_returns_matrix(prices)
    dates = rets.index
    signal_dates = _rebalance_dates(dates, first_rebalance, end, rebalance_freq)
    signal_dates = signal_dates[signal_dates >= pd.Timestamp(first_rebalance)]

    exec_to_signal: dict[pd.Timestamp, pd.Timestamp] = {}
    for sig_dt in signal_dates:
        if execution == "same_close":
            exec_to_signal[pd.Timestamp(sig_dt)] = pd.Timestamp(sig_dt)
        else:
            nxt = _next_session(dates, pd.Timestamp(sig_dt))
            if nxt is not None and nxt <= pd.Timestamp(end):
                exec_to_signal[nxt] = pd.Timestamp(sig_dt)

    w = pd.Series(dtype=float)
    daily = []
    miss_rows = []
    turn_rows = []
    hold_rows = []
    cost_rate = cost_bps_per_side / 10_000.0
    fee_daily = (mgmt_fee_bps_annual / 10_000.0) / 252.0
    pending_targets: dict[pd.Timestamp, pd.Series] = {}
    pending_meta: dict[pd.Timestamp, dict] = {}

    for sig_dt in signal_dates:
        sig = build_signals_for_date(
            sig_dt,
            prices,
            fund_q,
            sector_map,
            shares,
            lag_days=lag_days,
            min_price=min_price,
            min_adv=min_adv,
            n_universe=n_universe,
            quality_mode=quality_mode,
        )
        if universe_cap_weight:
            target = cap_weighted_universe(sig, n_universe)
        elif universe_sector_equal:
            target = sector_equal_universe(sig, n_universe)
        else:
            target = build_target_weights(
                sig, n_universe, selection_pct, composite_weights, single_factor
            )
        pending_targets[pd.Timestamp(sig_dt)] = target
        # treatment mix among selected (or universe)
        if len(target):
            sub = sig.reindex(target.index)
            qs = sub["quality_source"] if "quality_source" in sub.columns else pd.Series(dtype=str)
            pending_meta[pd.Timestamp(sig_dt)] = {
                "n_holdings": int((target > 0).sum()),
                "quality_ttm_weight": float(target[qs.eq("ttm_4q")].sum()) if len(qs) else 0.0,
                "quality_annual_weight": float(target[qs.eq("annual")].sum()) if len(qs) else 0.0,
                "quality_missing_weight": float(target[qs.eq("missing")].sum()) if len(qs) else 0.0,
                "shares_usable_weight": float(
                    target[
                        ~sub["shares_source"]
                        .astype(str)
                        .isin(["constant_latest", "nan", "None"])
                    ].sum()
                )
                if "shares_source" in sub.columns
                else np.nan,
                "shares_constant_weight": float(
                    target[sub["shares_source"].astype(str).eq("constant_latest")].sum()
                )
                if "shares_source" in sub.columns
                else np.nan,
            }
        else:
            pending_meta[pd.Timestamp(sig_dt)] = {
                "n_holdings": 0,
                "quality_ttm_weight": 0.0,
                "quality_annual_weight": 0.0,
                "quality_missing_weight": 0.0,
            }

    first_exec = min(exec_to_signal.keys()) if exec_to_signal else None

    for dt in dates:
        if dt < pd.Timestamp(start) or dt > pd.Timestamp(end):
            continue

        port_r = 0.0
        missing_w = 0.0
        if len(w):
            r = rets.loc[dt].reindex(w.index)
            port_r, w, missing_w = portfolio_return_and_drift(w, r)
        day_ret = port_r

        if dt in exec_to_signal:
            sig_dt = exec_to_signal[dt]
            target = pending_targets.get(sig_dt, pd.Series(dtype=float))
            all_idx = sorted(set(w.index) | set(target.index))
            w_old = w.reindex(all_idx).fillna(0.0)
            if w_old.sum() > 0:
                w_old = w_old / w_old.sum()
            w_new = target.reindex(all_idx).fillna(0.0)
            if w_new.sum() > 0:
                w_new = w_new / w_new.sum()

            l1 = float((w_old - w_new).abs().sum())
            one_way = l1 / 2.0
            # PROPORTIONAL cost approximation (not exact discrete cash ledger)
            trade_cost = l1 * cost_rate
            growth = (1.0 + port_r) * (1.0 - trade_cost) * (1.0 - fee_daily)
            day_ret = growth - 1.0
            w = w_new[w_new > 1e-12].copy()
            if w.sum() > 0:
                w = w / w.sum()

            meta = pending_meta.get(sig_dt, {})
            turn_rows.append(
                {
                    "date": dt,
                    "signal_date": sig_dt,
                    "turnover_one_way": one_way,
                    "traded_notional_l1": l1,
                    "trade_cost_approx": trade_cost,
                    **meta,
                }
            )
            for t, wt in w.items():
                hold_rows.append(
                    {"date": dt, "signal_date": sig_dt, "ticker": t, "weight": float(wt)}
                )
        else:
            if len(w):
                day_ret = (1.0 + port_r) * (1.0 - fee_daily) - 1.0

        # Record only after initial close execution (strategy is live)
        if first_exec is not None and dt >= first_exec:
            daily.append({"date": dt, "ret": day_ret})
            miss_rows.append({"date": dt, "missing_return_weight": missing_w})

    ret_s = pd.DataFrame(daily).set_index("date")["ret"] if daily else pd.Series(dtype=float)
    miss_s = (
        pd.DataFrame(miss_rows).set_index("date")["missing_return_weight"]
        if miss_rows
        else pd.Series(dtype=float)
    )
    turn_s = (
        pd.DataFrame(turn_rows).set_index("date")["turnover_one_way"]
        if turn_rows
        else pd.Series(dtype=float)
    )
    holds = pd.DataFrame(hold_rows)
    turn_detail = pd.DataFrame(turn_rows)
    return BacktestResult(
        name=name,
        returns=ret_s,
        turnover=turn_s,
        holdings_log=holds,
        missing_return_weight=miss_s,
        meta={
            "cost_bps_per_side": cost_bps_per_side,
            "mgmt_fee_bps_annual": mgmt_fee_bps_annual,
            "selection_pct": selection_pct,
            "lag_days": lag_days,
            "rebalance_freq": rebalance_freq,
            "n_universe": n_universe,
            "single_factor": single_factor,
            "universe_cap_weight": universe_cap_weight,
            "universe_sector_equal": universe_sector_equal,
            "execution": execution,
            "quality_mode": quality_mode,
            "accounting": "begin_weight_dot_return_then_drift",
            "cost_model": "PROPORTIONAL_APPROXIMATION_(1+Rp)*(1-L1*bps)*(1-fee)-1",
            "missing_return_policy": "halt_zero_flagged",
            "first_execution": str(first_exec.date()) if first_exec is not None else None,
            "turnover_detail": turn_detail,
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
    execution: str = "next_close",
) -> BacktestResult:
    wide = etf_prices.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    try:
        rets = wide.pct_change(fill_method=None)
    except TypeError:
        rets = wide.pct_change()
    tickers = [t for t in weights if t in rets.columns]
    rets = rets[tickers].dropna(how="all")
    me = month_end_dates(rets.index)
    me = me[(me >= pd.Timestamp(start)) & (me <= pd.Timestamp(end))]
    target_w = pd.Series({t: weights[t] for t in tickers}, dtype=float)
    target_w = target_w / target_w.sum()

    exec_map: dict[pd.Timestamp, pd.Timestamp] = {}
    for sig in me:
        if execution == "same_close":
            exec_map[pd.Timestamp(sig)] = pd.Timestamp(sig)
        else:
            later = rets.index[rets.index > sig]
            if len(later):
                exec_map[pd.Timestamp(later[0])] = pd.Timestamp(sig)

    cur = pd.Series(dtype=float)
    daily, turns, miss = [], [], []
    cost_rate = cost_bps_per_side / 10_000.0
    first_exec = min(exec_map.keys()) if exec_map else None

    for dt, row in rets.iterrows():
        if dt < pd.Timestamp(start) or dt > pd.Timestamp(end):
            continue
        port_r, missing_w = 0.0, 0.0
        if len(cur):
            port_r, cur, missing_w = portfolio_return_and_drift(cur, row.reindex(cur.index))
        day_ret = port_r
        if dt in exec_map:
            all_idx = sorted(set(cur.index) | set(target_w.index))
            old = cur.reindex(all_idx).fillna(0.0)
            if old.sum() > 0:
                old = old / old.sum()
            new = target_w.reindex(all_idx).fillna(0.0)
            new = new / new.sum()
            l1 = float((old - new).abs().sum())
            trade_cost = l1 * cost_rate
            day_ret = (1.0 + port_r) * (1.0 - trade_cost) - 1.0
            cur = new[new > 1e-12].copy()
            turns.append({"date": dt, "turnover_one_way": l1 / 2.0, "traded_notional_l1": l1})
        if first_exec is not None and dt >= first_exec:
            daily.append({"date": dt, "ret": day_ret})
            miss.append({"date": dt, "missing_return_weight": missing_w})

    ret_s = pd.DataFrame(daily).set_index("date")["ret"] if daily else pd.Series(dtype=float)
    turn_s = (
        pd.DataFrame(turns).set_index("date")["turnover_one_way"] if turns else pd.Series(dtype=float)
    )
    miss_s = (
        pd.DataFrame(miss).set_index("date")["missing_return_weight"] if miss else pd.Series(dtype=float)
    )
    return BacktestResult(
        name=name,
        returns=ret_s,
        turnover=turn_s,
        missing_return_weight=miss_s,
        meta={
            "proxy": True,
            "weights": weights,
            "execution": execution,
            "cost_model": "PROPORTIONAL_APPROXIMATION",
            "note": "ETF ER already in Adj Close; do not subtract ER again",
            "first_execution": str(first_exec.date()) if first_exec is not None else None,
        },
    )
