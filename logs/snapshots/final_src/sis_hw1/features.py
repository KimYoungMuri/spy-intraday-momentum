"""Feature construction: noise bands, VWAP proxy, daily volatility sizing."""
from __future__ import annotations

from datetime import time
from typing import Iterable

import numpy as np
import pandas as pd


def compute_vwap_proxy(prices: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    """Endpoint-weighted cumulative VWAP; zero-volume denominators -> NaN then ffill within session."""
    pv = np.cumsum(prices * volumes)
    vv = np.cumsum(volumes)
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap = np.where(vv > 0, pv / vv, np.nan)
    # forward-fill within the provided session arrays only
    s = pd.Series(vwap)
    return s.ffill().to_numpy(dtype=float)


def session_absolute_moves(
    session_prices: pd.Series,
    open_proxy: float,
    available_times: Iterable[time],
) -> dict[time, float]:
    """a_h = |P_h / O - 1| for each availability time in the session."""
    out: dict[time, float] = {}
    for t, p in zip(available_times, session_prices):
        out[t] = abs(float(p) / open_proxy - 1.0)
    return out


def build_band_history(
    clean: pd.DataFrame,
    lookback: int = 14,
) -> pd.DataFrame:
    """Attach lagged mean absolute moves and bands to each bar.

    Uses last `lookback` prior sessions that have an observation at the same available_at.
    Half-day afternoon times simply have fewer historical observations available;
    we require a full lookback of prior same-clock observations (may span >lookback calendar sessions).
    Documented deviation if fewer than lookback priors exist -> bands are NaN (no trade).
    """
    clean = clean.sort_values(["session_date", "available_at"]).copy()
    sessions = sorted(clean["session_date"].unique())

    # Precompute per-session open and moves by available_at
    moves: dict[tuple, float] = {}
    opens: dict = {}
    for d, g in clean.groupby("session_date"):
        g = g.sort_values("available_at")
        o = float(g["open_proxy"].iloc[0])
        opens[d] = o
        for _, row in g.iterrows():
            moves[(d, row["available_at"])] = abs(float(row["price"]) / o - 1.0)

    # For each session index, gather prior sessions
    sess_index = {d: i for i, d in enumerate(sessions)}

    rows = []
    for _, row in clean.iterrows():
        d = row["session_date"]
        h = row["available_at"]
        i = sess_index[d]
        prior = []
        j = i - 1
        while j >= 0 and len(prior) < lookback:
            pd_ = sessions[j]
            key = (pd_, h)
            if key in moves:
                prior.append(moves[key])
            j -= 1
        if len(prior) < lookback:
            m = np.nan
        else:
            m = float(np.mean(prior))
        rows.append(m)

    clean = clean.copy()
    clean["mean_abs_move"] = rows
    return clean


def attach_bands_and_vwap(
    clean: pd.DataFrame,
    daily: pd.DataFrame,
    lookback: int = 14,
    vm: float = 1.0,
) -> pd.DataFrame:
    """Compute U/L bands with gap adjustment and session VWAP proxy."""
    df = build_band_history(clean, lookback=lookback)
    daily_map = daily.set_index("session_date")[["close", "prior_close"]].to_dict("index")

    uppers, lowers, vwaps = [], [], []
    for d, g in df.groupby("session_date", sort=False):
        g = g.sort_values("available_at")
        o = float(g["open_proxy"].iloc[0])
        prior_close = daily_map.get(d, {}).get("prior_close", np.nan)
        if not np.isfinite(prior_close):
            # Fall back: use previous session's session_close_price from clean
            prior_sessions = [s for s in sorted(df["session_date"].unique()) if s < d]
            if prior_sessions:
                prev = df[df["session_date"] == prior_sessions[-1]]
                prior_close = float(prev["session_close_price"].iloc[0])
            else:
                prior_close = o

        anchor_up = max(o, prior_close)
        anchor_dn = min(o, prior_close)

        vwap = compute_vwap_proxy(
            g["price"].to_numpy(dtype=float),
            g["interval_volume"].to_numpy(dtype=float),
        )

        for k, (_, row) in enumerate(g.iterrows()):
            m = row["mean_abs_move"]
            if not np.isfinite(m):
                uppers.append(np.nan)
                lowers.append(np.nan)
            else:
                uppers.append(anchor_up * (1.0 + vm * m))
                lowers.append(anchor_dn * (1.0 - vm * m))
            vwaps.append(float(vwap[k]) if np.isfinite(vwap[k]) else np.nan)

    df = df.copy()
    df["upper"] = uppers
    df["lower"] = lowers
    df["vwap"] = vwaps
    df["prior_close"] = df["session_date"].map(
        lambda d: daily_map.get(d, {}).get("prior_close", np.nan)
    )
    return df


def compute_daily_sigma(
    daily: pd.DataFrame,
    lookback: int = 14,
) -> pd.DataFrame:
    """Sample std of prior `lookback` close-to-close returns (ddof=1), lagged."""
    d = daily.sort_values("session_date").copy()
    rets = d["daily_return"].to_numpy(dtype=float)
    sigmas = np.full(len(d), np.nan)
    for i in range(len(d)):
        # need rets[i-lookback : i] — these are returns ending on days i-lookback .. i-1
        start = i - lookback
        if start < 0:
            continue
        window = rets[start:i]
        if np.sum(np.isfinite(window)) < lookback:
            continue
        sigmas[i] = float(np.std(window, ddof=1))
    d["sigma"] = sigmas
    return d


def exposure_and_shares(
    equity: float,
    open_proxy: float,
    sigma: float,
    vol_target: float = 0.02,
    max_leverage: float = 4.0,
    fixed_exposure: float | None = None,
) -> tuple[float, int]:
    """Return (exposure_multiple, floor_shares)."""
    if fixed_exposure is not None:
        exposure = float(fixed_exposure)
    else:
        if not np.isfinite(sigma) or sigma <= 0:
            exposure = 0.0
        else:
            exposure = min(max_leverage, vol_target / sigma)
    if open_proxy <= 0 or not np.isfinite(open_proxy):
        return exposure, 0
    shares = int(np.floor(equity * exposure / open_proxy))
    return exposure, shares
