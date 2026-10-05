"""Regression tests for portfolio accounting and signal conventions."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sis_hw2.backtest.engine import portfolio_return_and_drift, portfolio_from_etf_weights


def test_two_asset_drift_zero_portfolio_return():
    """
    50/50 portfolio, +10% / -10% asset returns:
    portfolio return must be 0%; ending weights 55% / 45%.
    The buggy implementation produced +1%.
    """
    w = pd.Series({"A": 0.5, "B": 0.5})
    r = pd.Series({"A": 0.10, "B": -0.10})
    port_r, drifted = portfolio_return_and_drift(w, r)
    assert abs(port_r - 0.0) < 1e-12
    assert abs(drifted["A"] - 0.55) < 1e-12
    assert abs(drifted["B"] - 0.45) < 1e-12


def test_buggy_formula_would_be_wrong():
    """Document the old bug: updating weights before return gave +1%."""
    w = pd.Series({"A": 0.5, "B": 0.5})
    r = pd.Series({"A": 0.10, "B": -0.10})
    w_wrong = w * (1.0 + r)
    buggy_r = float((w_wrong / w_wrong.sum() * r).sum())
    assert abs(buggy_r - 0.01) < 1e-12  # the bug


def test_one_stock_buy_and_hold_matches_asset():
    w = pd.Series({"A": 1.0})
    r = pd.Series({"A": 0.03})
    port_r, drifted = portfolio_return_and_drift(w, r)
    assert abs(port_r - 0.03) < 1e-12
    assert abs(drifted["A"] - 1.0) < 1e-12


def test_zero_returns_with_costs_via_etf_engine():
    """With flat prices, only entry costs reduce NAV."""
    dates = pd.bdate_range("2020-01-01", periods=5)
    # month-end-ish: use dates that include a month end
    dates = pd.DatetimeIndex(
        [
            pd.Timestamp("2020-01-30"),
            pd.Timestamp("2020-01-31"),
            pd.Timestamp("2020-02-03"),
            pd.Timestamp("2020-02-04"),
            pd.Timestamp("2020-02-05"),
        ]
    )
    rows = []
    for t in ["X", "Y"]:
        for d in dates:
            rows.append({"date": d, "ticker": t, "adj_close": 100.0})
    etf = pd.DataFrame(rows)
    res = portfolio_from_etf_weights(
        etf,
        {"X": 0.5, "Y": 0.5},
        start="2020-01-30",
        end="2020-02-05",
        cost_bps_per_side=10.0,
        execution="next_close",
    )
    # First execution day: enter from 0 -> 100% invested, L1=1, cost=1*10bps=0.001
    assert len(res.returns) > 0
    first = float(res.returns.iloc[0])
    assert first < 0  # costs on entry
    # Subsequent flat days ~0
    if len(res.returns) > 1:
        assert abs(float(res.returns.iloc[1])) < 1e-12


def test_drawdown_from_nav_one():
    from sis_hw2.metrics.performance import max_drawdown

    r = pd.Series([-0.10, 0.05, -0.02])
    # wealth: 0.9, 0.945, 0.9261 — max dd from peak 1.0 is -0.10 first, then deeper?
    # peak starts at 1 before returns if we use cumprod of (1+r) from 1
    dd = max_drawdown(r)
    assert dd <= -0.10 + 1e-12


def test_adv_uses_20_sessions():
    from sis_hw2.signals.factors import adv_20_sessions

    cal = pd.bdate_range("2020-01-01", periods=30)
    rows = []
    for i, d in enumerate(cal):
        rows.append(
            {
                "date": d,
                "ticker": "A",
                "close": 10.0,
                "volume": 1000.0 + i,  # increasing
                "adj_close": 10.0,
            }
        )
    px = pd.DataFrame(rows)
    asof = cal[-1]
    adv = adv_20_sessions(px, asof, pd.DatetimeIndex(cal))
    # mean volume of last 20 * 10
    last20_vol = px.tail(20)["volume"]
    expected = float((10.0 * last20_vol).mean())
    assert abs(float(adv["A"]) - expected) < 1e-8
