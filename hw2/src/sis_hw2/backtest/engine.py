"""Backtest engine with correct beginning-of-period return accounting."""

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


def portfolio_return_and_drift(
    weights: pd.Series, asset_returns: pd.Series
) -> tuple[float, pd.Series]:
    """
    Correct self-financing drift.

    Given beginning-of-period weights w (sum to 1) and asset returns r:
      R_p = sum_i w_i * r_i
      w'_i = w_i * (1 + r_i) / (1 + R_p)

    Missing returns for held names are treated as NaN -> exclude from return
    contribution only if weight is zero; for positive weight, missing return
    is an error condition handled by caller (pass explicit values).
    """
    w = weights.astype(float).copy()
    r = asset_returns.reindex(w.index).astype(float)
    if w.sum() <= 0:
        return 0.0, w
    w = w / w.sum()
    # Held names with missing returns: do not silently zero — leave as NaN check
    if r.isna().any() and w[r.isna()].sum() > 1e-12:
        # Conservative: treat missing held return as 0 but flag in meta via caller
        r = r.fillna(0.0)
    else:
        r = r.fillna(0.0)
    port_r = float((w * r).sum())
    denom = 1.0 + port_r
    if abs(denom) < 1e-15:
        drifted = w.copy()
    else:
        drifted = w * (1.0 + r) / denom
    if drifted.sum() > 0:
        drifted = drifted / drifted.sum()
    return port_r, drifted


def _daily_returns_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    wide = prices.pivot(index="date", columns="ticker", values="adj_close").sort_index()
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
    """First trading session strictly after signal_dt."""
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
    execution: str = "next_close",
) -> BacktestResult:
    """
    Monthly (or quarterly) rebalance long-only backtest.

    Event sequence (execution='next_close'):
    1. Signals observed using information available as of month-end close T.
    2. Existing portfolio earns the next-session total return (T -> T+1).
    3. At T+1 close, rebalance from drifted weights to target weights.
    4. Transaction costs = sum(|Δw|) * (bps_per_side / 1e4) of post-return NAV,
       deducted by scaling NAV: net_factor = (1+R_p)*(1-cost)*(1-fee)-1.
    5. New weights begin earning returns the following session.

    Frictionless day (no trade):
      R_p = w · r
      w <- drift(w, r)
      day_ret = (1+R_p)*(1-fee_daily) - 1

    Turnover reporting:
      L1 = sum(|w_old - w_new|)
      one_way_turnover = L1 / 2
      traded_notional_frac = L1  (both sides charged at per-side bps)
    """
    rets = _daily_returns_matrix(prices)
    dates = rets.index
    signal_dates = _rebalance_dates(dates, first_rebalance, end, rebalance_freq)
    signal_dates = signal_dates[signal_dates >= pd.Timestamp(first_rebalance)]

    # Map execution date -> signal date
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
    turn_rows = []
    hold_rows = []
    cost_rate = cost_bps_per_side / 10_000.0
    fee_daily = (mgmt_fee_bps_annual / 10_000.0) / 252.0
    pending_targets: dict[pd.Timestamp, pd.Series] = {}

    # Precompute targets on signal dates
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
        )
        if universe_cap_weight:
            target = cap_weighted_universe(sig, n_universe)
        else:
            target = build_target_weights(
                sig, n_universe, selection_pct, composite_weights, single_factor
            )
        pending_targets[pd.Timestamp(sig_dt)] = target

    first_exec = min(exec_to_signal.keys()) if exec_to_signal else None

    for dt in dates:
        if dt < pd.Timestamp(start) or dt > pd.Timestamp(end):
            continue

        day_ret = 0.0
        port_r = 0.0

        if len(w):
            r = rets.loc[dt].reindex(w.index)
            port_r, w = portfolio_return_and_drift(w, r)
            day_ret = port_r
        else:
            port_r = 0.0
            day_ret = 0.0

        # Execute pending rebalance at this close if scheduled
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
            trade_cost = l1 * cost_rate  # per-side bps on each traded leg

            # Self-financing: costs scale NAV after portfolio return
            # net_growth = (1+R_p) * (1 - trade_cost) * (1 - fee_daily)
            growth = (1.0 + port_r) * (1.0 - trade_cost) * (1.0 - fee_daily)
            day_ret = growth - 1.0
            w = w_new[w_new > 1e-12].copy()
            if w.sum() > 0:
                w = w / w.sum()

            turn_rows.append(
                {
                    "date": dt,
                    "signal_date": sig_dt,
                    "turnover_one_way": one_way,
                    "traded_notional_l1": l1,
                    "trade_cost": trade_cost,
                    "n_holdings": int((w > 0).sum()),
                }
            )
            for t, wt in w.items():
                hold_rows.append(
                    {
                        "date": dt,
                        "signal_date": sig_dt,
                        "ticker": t,
                        "weight": float(wt),
                    }
                )
        else:
            if len(w) or (first_exec is not None and dt >= first_exec):
                # Apply fee even in cash (0 weight) only if invested; cash earns 0 - fee optional
                if len(w):
                    day_ret = (1.0 + port_r) * (1.0 - fee_daily) - 1.0
                else:
                    day_ret = 0.0

        # Record returns from first execution onward (when strategy is live)
        if first_exec is not None and dt >= first_exec:
            daily.append({"date": dt, "ret": day_ret})

    ret_s = (
        pd.DataFrame(daily).set_index("date")["ret"] if daily else pd.Series(dtype=float)
    )
    turn_s = (
        pd.DataFrame(turn_rows).set_index("date")["turnover_one_way"]
        if turn_rows
        else pd.Series(dtype=float)
    )
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
            "execution": execution,
            "accounting": "begin_weight_dot_return_then_drift",
            "cost_model": "NAV_scaled_by_(1-L1*bps_per_side)",
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
    """Labeled ETF proxy with the same return-accounting convention."""
    wide = etf_prices.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    rets = wide.pct_change()
    tickers = list(weights.keys())
    rets = rets[[t for t in tickers if t in rets.columns]].dropna(how="all")
    me = month_end_dates(rets.index)
    me = me[(me >= pd.Timestamp(start)) & (me <= pd.Timestamp(end))]

    target_w = pd.Series(weights, dtype=float)
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
    daily = []
    turns = []
    cost_rate = cost_bps_per_side / 10_000.0
    first_exec = min(exec_map.keys()) if exec_map else None

    for dt, row in rets.iterrows():
        if dt < pd.Timestamp(start) or dt > pd.Timestamp(end):
            continue
        port_r = 0.0
        if len(cur):
            r = row.reindex(cur.index)
            port_r, cur = portfolio_return_and_drift(cur, r)
        day_ret = port_r

        if dt in exec_map:
            # Initial entry: if empty, port_r=0 then trade into target (pay entry costs)
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

    ret_s = pd.DataFrame(daily).set_index("date")["ret"] if daily else pd.Series(dtype=float)
    turn_s = (
        pd.DataFrame(turns).set_index("date")["turnover_one_way"]
        if turns
        else pd.Series(dtype=float)
    )
    return BacktestResult(
        name=name,
        returns=ret_s,
        turnover=turn_s,
        meta={
            "proxy": True,
            "weights": weights,
            "execution": execution,
            "accounting": "begin_weight_dot_return_then_drift",
            "note": "ETF ER already in Adj Close; do not subtract ER again",
        },
    )
