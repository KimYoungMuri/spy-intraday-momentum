"""Independent arithmetic reference checks (not wrappers of production functions)."""
from __future__ import annotations

import math


def ref_mean_abs_moves(prices: list[float], open_: float) -> list[float]:
    return [abs(p / open_ - 1.0) for p in prices]


def ref_bands(
    opens_hist: list[float],
    prices_hist: list[list[float]],
    open_today: float,
    prior_close: float,
    vm: float = 1.0,
) -> tuple[list[float], list[float]]:
    """Hand-style band construction.

    prices_hist[i] is list of endpoint prices for historical day i (same length / clocks).
    """
    n_clocks = len(prices_hist[0])
    means = []
    for h in range(n_clocks):
        moves = [abs(prices_hist[i][h] / opens_hist[i] - 1.0) for i in range(len(opens_hist))]
        means.append(sum(moves) / len(moves))
    up_anchor = max(open_today, prior_close)
    dn_anchor = min(open_today, prior_close)
    upper = [up_anchor * (1.0 + vm * m) for m in means]
    lower = [dn_anchor * (1.0 - vm * m) for m in means]
    return upper, lower


def ref_interval_from_cumulative(cum: list[float]) -> list[float]:
    out = [cum[0]]
    for i in range(1, len(cum)):
        out.append(cum[i] - cum[i - 1])
    return out


def ref_vwap(prices: list[float], volumes: list[float]) -> list[float]:
    pv = 0.0
    vv = 0.0
    out = []
    last = float("nan")
    for p, v in zip(prices, volumes):
        pv += p * v
        vv += v
        if vv > 0:
            last = pv / vv
        out.append(last)
    return out


def ref_sample_std(xs: list[float]) -> float:
    n = len(xs)
    mu = sum(xs) / n
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))


def ref_shares(equity: float, open_: float, sigma: float, target: float = 0.02, cap: float = 4.0) -> tuple[float, int]:
    if sigma <= 0:
        return 0.0, 0
    exposure = min(cap, target / sigma)
    return exposure, math.floor(equity * exposure / open_)


def ref_roundtrip_pnl(
    entry: float,
    exit_: float,
    shares: int,
    side: int,
    commission: float,
    slippage: float,
) -> dict[str, float]:
    """side=+1 long, -1 short. Costs on entry and exit (2 sides)."""
    gross = side * (exit_ - entry) * shares
    traded = 2 * abs(shares)
    cost = traded * (commission + slippage)
    return {"gross": gross, "cost": cost, "net": gross - cost}
