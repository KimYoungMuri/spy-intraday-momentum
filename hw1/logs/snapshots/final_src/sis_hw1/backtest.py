"""Backtest engine with explicit fill accounting and overnight flat constraint."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

import numpy as np
import pandas as pd

from sis_hw1.features import attach_bands_and_vwap, compute_daily_sigma, exposure_and_shares
from sis_hw1.strategy import Position, Variant, decide

FillMode = Literal["endpoint", "delay_one"]


@dataclass
class BacktestResult:
    variant: str
    daily: pd.DataFrame
    trades: pd.DataFrame
    bars: pd.DataFrame
    meta: dict[str, Any] = field(default_factory=dict)


def _target_shares(desired: Position, day_target_shares: int) -> int:
    if desired == Position.FLAT:
        return 0
    if desired == Position.LONG:
        return int(day_target_shares)
    return -int(day_target_shares)


def _apply_fill(
    *,
    cash: float,
    shares_held: int,
    new_shares: int,
    fill_price: float,
    commission: float,
    slippage: float,
    reason: str,
    session_date,
    available_at,
    variant: str,
    trade_rows: list,
) -> tuple[float, int, Position, float, float, int]:
    traded = abs(new_shares - shares_held)
    day_commission = 0.0
    day_slippage = 0.0
    n_trades = 0
    pos = Position.FLAT if shares_held == 0 else (
        Position.LONG if shares_held > 0 else Position.SHORT
    )
    if traded == 0:
        pos = Position.FLAT if new_shares == 0 else (
            Position.LONG if new_shares > 0 else Position.SHORT
        )
        return cash, shares_held, pos, day_commission, day_slippage, n_trades

    commission_paid = traded * commission
    slippage_paid = traded * slippage
    total_cost = commission_paid + slippage_paid
    cash = cash + (shares_held - new_shares) * fill_price - total_cost
    trade_rows.append({
        "session_date": session_date,
        "available_at": str(available_at),
        "variant": variant,
        "reason": reason,
        "fill_price": fill_price,
        "shares_from": shares_held,
        "shares_to": new_shares,
        "traded": traded,
        "commission": commission_paid,
        "slippage": slippage_paid,
        "cost": total_cost,
    })
    shares_held = new_shares
    pos = Position.FLAT if new_shares == 0 else (
        Position.LONG if new_shares > 0 else Position.SHORT
    )
    return cash, shares_held, pos, commission_paid, slippage_paid, 1


def run_backtest(
    clean: pd.DataFrame,
    daily: pd.DataFrame,
    variant: Variant,
    *,
    initial_equity: float = 100_000.0,
    band_lookback: int = 14,
    sizing_lookback: int = 14,
    vm: float = 1.0,
    vol_target: float = 0.02,
    max_leverage: float = 4.0,
    commission: float = 0.0035,
    slippage: float = 0.001,
    fill_mode: FillMode = "endpoint",
    use_vwap: bool = True,
    eval_start: date | None = None,
    eval_end: date | None = None,
) -> BacktestResult:
    feat = attach_bands_and_vwap(clean, daily, lookback=band_lookback, vm=vm)
    daily_s = compute_daily_sigma(daily, lookback=sizing_lookback)
    sigma_map = daily_s.set_index("session_date")["sigma"].to_dict()
    close_map = daily_s.set_index("session_date")["close"].to_dict()

    equity = float(initial_equity)
    cash = float(initial_equity)
    pos = Position.FLAT
    shares_held = 0

    bar_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    daily_rows: list[dict[str, Any]] = []

    sessions = sorted(feat["session_date"].unique())
    if eval_start:
        sessions = [s for s in sessions if s >= eval_start]
    if eval_end:
        sessions = [s for s in sessions if s <= eval_end]

    for d in sessions:
        g = feat[feat["session_date"] == d].sort_values("available_at").reset_index(drop=True)
        if g.empty:
            continue

        open_proxy = float(g["open_proxy"].iloc[0])
        close_px = float(g["session_close_price"].iloc[0])
        close_t = g["session_close_time"].iloc[0]
        sigma = sigma_map.get(d, np.nan)

        if variant in ("A", "B"):
            day_exposure, day_target_shares = exposure_and_shares(
                equity, open_proxy, sigma, fixed_exposure=1.0
            )
        else:
            day_exposure, day_target_shares = exposure_and_shares(
                equity, open_proxy, sigma, vol_target=vol_target, max_leverage=max_leverage
            )

        assert shares_held == 0 and pos == Position.FLAT

        eod_start = equity
        day_commission = 0.0
        day_slippage = 0.0
        day_trades = 0
        pending: Position | None = None

        for _, row in g.iterrows():
            price = float(row["price"])
            upper = float(row["upper"]) if pd.notna(row["upper"]) else np.nan
            lower = float(row["lower"]) if pd.notna(row["lower"]) else np.nan
            vwap = float(row["vwap"]) if pd.notna(row["vwap"]) else np.nan
            avail = row["available_at"]
            is_close_bar = bool(row["is_session_close_bar"]) or (avail == close_t)
            fill_price = close_px if is_close_bar else price
            reason = ""

            if fill_mode == "endpoint":
                if is_close_bar:
                    desired = Position.FLAT
                    reason = "session_close_flatten"
                else:
                    dec = decide(variant, pos, price, upper, lower, vwap, use_vwap=use_vwap)
                    desired = dec.target
                    reason = dec.reason
                new_shares = _target_shares(desired, day_target_shares)
                cash, shares_held, pos, c_paid, s_paid, nt = _apply_fill(
                    cash=cash, shares_held=shares_held, new_shares=new_shares,
                    fill_price=fill_price, commission=commission, slippage=slippage,
                    reason=reason, session_date=d, available_at=avail, variant=variant,
                    trade_rows=trade_rows,
                )
                day_commission += c_paid
                day_slippage += s_paid
                day_trades += nt
            else:
                # delay_one: fill pending from prior bar at this bar's price; queue new signal
                if pending is not None:
                    if is_close_bar:
                        desired = Position.FLAT
                        reason = "delay_cancel_and_flatten"
                        pending = None
                    else:
                        desired = pending
                        reason = "delay_fill_pending"
                        pending = None
                    new_shares = _target_shares(desired, day_target_shares)
                    cash, shares_held, pos, c_paid, s_paid, nt = _apply_fill(
                        cash=cash, shares_held=shares_held, new_shares=new_shares,
                        fill_price=fill_price, commission=commission, slippage=slippage,
                        reason=reason, session_date=d, available_at=avail, variant=variant,
                        trade_rows=trade_rows,
                    )
                    day_commission += c_paid
                    day_slippage += s_paid
                    day_trades += nt

                if is_close_bar:
                    if shares_held != 0:
                        cash, shares_held, pos, c_paid, s_paid, nt = _apply_fill(
                            cash=cash, shares_held=shares_held, new_shares=0,
                            fill_price=close_px, commission=commission, slippage=slippage,
                            reason="session_close_flatten", session_date=d,
                            available_at=avail, variant=variant, trade_rows=trade_rows,
                        )
                        day_commission += c_paid
                        day_slippage += s_paid
                        day_trades += nt
                    pending = None
                    reason = "session_close_flatten"
                else:
                    dec = decide(variant, pos, price, upper, lower, vwap, use_vwap=use_vwap)
                    pending = dec.target
                    if not reason:
                        reason = dec.reason + "_queued"

            mtm_equity = cash + shares_held * (close_px if is_close_bar else price)
            bar_rows.append({
                "session_date": d,
                "available_at": str(avail),
                "clock_label": str(row["clock_label"]),
                "price": price,
                "upper": upper,
                "lower": lower,
                "vwap": vwap,
                "position": int(pos),
                "shares": shares_held,
                "day_target_shares": day_target_shares,
                "day_exposure": day_exposure,
                "reason": reason,
                "equity_mtm": mtm_equity,
                "cash": cash,
                "variant": variant,
            })

        if shares_held != 0:
            cash, shares_held, pos, c_paid, s_paid, nt = _apply_fill(
                cash=cash, shares_held=shares_held, new_shares=0,
                fill_price=close_px, commission=commission, slippage=slippage,
                reason="force_close_safety", session_date=d, available_at=close_t,
                variant=variant, trade_rows=trade_rows,
            )
            day_commission += c_paid
            day_slippage += s_paid
            day_trades += nt

        equity = cash
        daily_rows.append({
            "session_date": d,
            "variant": variant,
            "equity_start": eod_start,
            "equity_end": equity,
            "daily_return": equity / eod_start - 1.0 if eod_start else 0.0,
            "open_proxy": open_proxy,
            "close": close_px,
            "spy_close": close_map.get(d, close_px),
            "sigma": sigma,
            "exposure": day_exposure,
            "target_shares": day_target_shares,
            "n_trades": day_trades,
            "commission": day_commission,
            "slippage": day_slippage,
            "cost": day_commission + day_slippage,
            "is_half_day": bool(g["is_half_day"].iloc[0]),
        })

    return BacktestResult(
        variant=variant,
        daily=pd.DataFrame(daily_rows),
        trades=pd.DataFrame(trade_rows),
        bars=pd.DataFrame(bar_rows),
        meta={
            "variant": variant,
            "initial_equity": initial_equity,
            "band_lookback": band_lookback,
            "sizing_lookback": sizing_lookback,
            "vm": vm,
            "vol_target": vol_target,
            "max_leverage": max_leverage,
            "commission": commission,
            "slippage": slippage,
            "fill_mode": fill_mode,
            "use_vwap": use_vwap,
            "n_sessions": len(daily_rows),
            "final_equity": float(equity),
        },
    )


def buy_and_hold_spy(
    daily: pd.DataFrame,
    eval_start: date,
    eval_end: date,
    initial_equity: float = 100_000.0,
) -> pd.DataFrame:
    """Close-to-close buy-and-hold on the supplied price series (adjustment basis unverified)."""
    d = daily.sort_values("session_date").copy()
    d = d[(d["session_date"] >= eval_start) & (d["session_date"] <= eval_end)].copy()
    if d.empty:
        return d

    first = d.iloc[0]
    entry = first["prior_close"] if pd.notna(first.get("prior_close", np.nan)) else first["close"]
    shares = int(np.floor(initial_equity / float(entry)))
    cash = initial_equity - shares * float(entry)

    rows = []
    for _, row in d.iterrows():
        eq = cash + shares * float(row["close"])
        rows.append({
            "session_date": row["session_date"],
            "variant": "SPY_BH",
            "equity_end": eq,
            "close": float(row["close"]),
            "shares": shares,
            "entry_price": float(entry),
        })
    out = pd.DataFrame(rows)
    out["equity_start"] = out["equity_end"].shift(1)
    out.loc[out.index[0], "equity_start"] = initial_equity
    out["daily_return"] = out["equity_end"] / out["equity_start"] - 1.0
    out["n_trades"] = 0
    out["commission"] = 0.0
    out["slippage"] = 0.0
    out["cost"] = 0.0
    return out
