"""Performance metrics and robustness helpers."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def summarize_equity(
    daily: pd.DataFrame,
    *,
    initial_equity: float,
    risk_free_daily: float = 0.0,
    trading_days_per_year: int = 252,
    label: str = "",
) -> dict[str, Any]:
    if daily is None or daily.empty:
        return {"label": label, "n_sessions": 0}

    eq = daily["equity_end"].to_numpy(dtype=float)
    rets = daily["daily_return"].to_numpy(dtype=float)
    n = len(rets)
    start = float(daily["equity_start"].iloc[0]) if "equity_start" in daily else initial_equity
    end = float(eq[-1])
    total_return = end / start - 1.0
    ann_geom = (end / start) ** (trading_days_per_year / n) - 1.0 if n > 0 and start > 0 else np.nan

    excess = rets - risk_free_daily
    mu = float(np.mean(rets))
    sig = float(np.std(rets, ddof=1)) if n > 1 else np.nan
    ann_vol = sig * np.sqrt(trading_days_per_year) if np.isfinite(sig) else np.nan
    sharpe = (
        np.sqrt(trading_days_per_year) * float(np.mean(excess)) / float(np.std(excess, ddof=1))
        if n > 1 and float(np.std(excess, ddof=1)) > 0
        else np.nan
    )

    # Drawdown
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    mdd = float(dd.min()) if len(dd) else np.nan
    mdd_i = int(dd.argmin()) if len(dd) else -1
    mdd_date = str(daily["session_date"].iloc[mdd_i]) if mdd_i >= 0 else None
    # peak date
    peak_i = int(np.argmax(eq[: mdd_i + 1])) if mdd_i >= 0 else -1
    peak_date = str(daily["session_date"].iloc[peak_i]) if peak_i >= 0 else None

    skew = float(pd.Series(rets).skew())  # pandas sample skewness
    best = float(np.max(rets)) if n else np.nan
    worst = float(np.min(rets)) if n else np.nan
    best_d = str(daily.loc[daily["daily_return"].idxmax(), "session_date"]) if n else None
    worst_d = str(daily.loc[daily["daily_return"].idxmin(), "session_date"]) if n else None

    win_days = int(np.sum(rets > 0))
    lose_days = int(np.sum(rets < 0))
    flat_days = int(np.sum(rets == 0))
    traded_days = int(np.sum(daily["n_trades"] > 0)) if "n_trades" in daily.columns else np.nan

    return {
        "label": label,
        "n_sessions": n,
        "start_date": str(daily["session_date"].iloc[0]),
        "end_date": str(daily["session_date"].iloc[-1]),
        "start_equity": start,
        "end_equity": end,
        "total_return": total_return,
        "ann_geom_return": ann_geom,
        "ann_geom_convention": f"(E_end/E_start)^(252/N)-1 with N={n}",
        "mean_daily_return": mu,
        "std_daily_return": sig,
        "ann_volatility": ann_vol,
        "sharpe": sharpe,
        "risk_free_daily": risk_free_daily,
        "max_drawdown": mdd,
        "mdd_peak_date": peak_date,
        "mdd_trough_date": mdd_date,
        "skewness": skew,
        "best_day": best,
        "best_day_date": best_d,
        "worst_day": worst,
        "worst_day_date": worst_d,
        "winning_day_fraction": win_days / n if n else np.nan,
        "winning_days": win_days,
        "losing_days": lose_days,
        "flat_days": flat_days,
        "fraction_days_traded": traded_days / n if n and traded_days == traded_days else np.nan,
        "total_commission": float(daily["commission"].sum()) if "commission" in daily else np.nan,
        "total_slippage": float(daily["slippage"].sum()) if "slippage" in daily else np.nan,
        "total_cost": float(daily["cost"].sum()) if "cost" in daily else np.nan,
    }


def trade_stats(trades: pd.DataFrame, bars: pd.DataFrame | None = None) -> dict[str, Any]:
    if trades is None or trades.empty:
        return {
            "n_trade_events": 0,
            "n_completed_roundtrips_est": 0,
            "avg_pnl_per_share": np.nan,
            "winning_trade_fraction": np.nan,
        }

    # Round-trip approximation: pair position open->flat or reverse as completed legs
    # Build from share changes
    t = trades.sort_values(["session_date", "available_at"]).copy()
    events = int(len(t))
    total_traded = float(t["traded"].sum())
    total_cost = float(t["cost"].sum())

    # Reconstruct signed PnL per completed trade via inventory method
    inventory = 0
    entry_price = 0.0
    completed = []
    for _, row in t.iterrows():
        new = int(row["shares_to"])
        old = int(row["shares_from"])
        px = float(row["fill_price"])
        # closing portion
        if old != 0 and np.sign(old) != np.sign(new):
            # close all old
            pnl_ps = (px - entry_price) * np.sign(old)
            completed.append({"pnl_per_share": pnl_ps, "shares": abs(old), "side": int(np.sign(old))})
            if new != 0:
                entry_price = px
            else:
                entry_price = 0.0
        elif old != 0 and new == 0:
            pnl_ps = (px - entry_price) * np.sign(old)
            completed.append({"pnl_per_share": pnl_ps, "shares": abs(old), "side": int(np.sign(old))})
            entry_price = 0.0
        elif old == 0 and new != 0:
            entry_price = px
        inventory = new

    if completed:
        cdf = pd.DataFrame(completed)
        wins = cdf[cdf["pnl_per_share"] > 0]
        losses = cdf[cdf["pnl_per_share"] < 0]
        avg_win = float(wins["pnl_per_share"].mean()) if len(wins) else np.nan
        avg_loss = float(losses["pnl_per_share"].mean()) if len(losses) else np.nan
        payoff = (avg_win / abs(avg_loss)) if np.isfinite(avg_win) and np.isfinite(avg_loss) and avg_loss != 0 else np.nan
        gross_profit = float((wins["pnl_per_share"] * wins["shares"]).sum()) if len(wins) else 0.0
        gross_loss = float((losses["pnl_per_share"] * losses["shares"]).sum()) if len(losses) else 0.0
        profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else np.nan
        # weighted avg pnl per share
        wavg = float((cdf["pnl_per_share"] * cdf["shares"]).sum() / cdf["shares"].sum())
        hit = float((cdf["pnl_per_share"] > 0).mean())
        long_pnl = float((cdf.loc[cdf["side"] > 0, "pnl_per_share"] * cdf.loc[cdf["side"] > 0, "shares"]).sum())
        short_pnl = float((cdf.loc[cdf["side"] < 0, "pnl_per_share"] * cdf.loc[cdf["side"] < 0, "shares"]).sum())
    else:
        wavg = hit = payoff = profit_factor = avg_win = avg_loss = long_pnl = short_pnl = np.nan

    return {
        "n_trade_events": events,
        "n_completed_trades": len(completed),
        "total_shares_traded": total_traded,
        "total_cost": total_cost,
        "avg_pnl_per_share_gross": wavg,
        "winning_trade_fraction": hit,
        "avg_win_per_share": avg_win,
        "avg_loss_per_share": avg_loss,
        "payoff_ratio": payoff,
        "profit_factor": profit_factor,
        "long_gross_pnl_dollars_approx": long_pnl,
        "short_gross_pnl_dollars_approx": short_pnl,
        "trades_per_day": events / t["session_date"].nunique() if t["session_date"].nunique() else np.nan,
    }


def regression_on_spy(
    strat_daily: pd.DataFrame,
    spy_daily: pd.DataFrame,
    trading_days_per_year: int = 252,
) -> dict[str, Any]:
    """OLS of strategy daily returns on SPY daily returns; Newey-West HAC se if available."""
    a = strat_daily[["session_date", "daily_return"]].rename(columns={"daily_return": "r_strat"})
    b = spy_daily[["session_date", "daily_return"]].rename(columns={"daily_return": "r_spy"})
    m = a.merge(b, on="session_date", how="inner").dropna()
    if len(m) < 5:
        return {"n": len(m), "alpha_daily": np.nan, "beta": np.nan, "r2": np.nan}

    y = m["r_strat"].to_numpy()
    x = m["r_spy"].to_numpy()
    X = np.column_stack([np.ones(len(x)), x])
    beta_hat, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta_hat
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

    alpha_d = float(beta_hat[0])
    beta = float(beta_hat[1])
    out = {
        "n": int(len(m)),
        "alpha_daily": alpha_d,
        "alpha_ann_252x": alpha_d * trading_days_per_year,
        "beta": beta,
        "r2": r2,
        "corr": float(np.corrcoef(y, x)[0, 1]),
    }

    try:
        import statsmodels.api as sm
        model = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
        out["alpha_se_hac"] = float(model.bse[0])
        out["beta_se_hac"] = float(model.bse[1])
        out["alpha_t_hac"] = float(model.tvalues[0])
        out["beta_t_hac"] = float(model.tvalues[1])
        out["hac_maxlags"] = 5
    except Exception as e:
        out["hac_error"] = str(e)

    return out


def block_bootstrap_sharpe(
    rets: np.ndarray,
    *,
    block_length: int = 5,
    n_resamples: int = 1000,
    seed: int = 42,
    trading_days_per_year: int = 252,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    rets = np.asarray(rets, dtype=float)
    n = len(rets)
    if n < block_length + 2:
        return {"n": n, "sharpe_ci": (np.nan, np.nan)}

    def sharpe(x: np.ndarray) -> float:
        if len(x) < 2 or np.std(x, ddof=1) == 0:
            return np.nan
        return float(np.sqrt(trading_days_per_year) * np.mean(x) / np.std(x, ddof=1))

    point = sharpe(rets)
    samples = []
    n_blocks = int(np.ceil(n / block_length))
    for _ in range(n_resamples):
        starts = rng.integers(0, n - block_length + 1, size=n_blocks)
        boot = np.concatenate([rets[s : s + block_length] for s in starts])[:n]
        samples.append(sharpe(boot))
    samples = np.array(samples, dtype=float)
    samples = samples[np.isfinite(samples)]
    return {
        "point_sharpe": point,
        "boot_mean": float(np.mean(samples)) if len(samples) else np.nan,
        "boot_ci_025": float(np.quantile(samples, 0.025)) if len(samples) else np.nan,
        "boot_ci_975": float(np.quantile(samples, 0.975)) if len(samples) else np.nan,
        "block_length": block_length,
        "n_resamples": n_resamples,
        "seed": seed,
    }


def fmt5(x: Any) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "N/A"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    try:
        return f"{float(x):.5f}"
    except Exception:
        return str(x)
