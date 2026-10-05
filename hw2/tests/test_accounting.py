"""Regression tests for portfolio accounting and signal conventions."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sis_hw2.backtest.engine import (
    portfolio_return_and_drift,
    portfolio_from_etf_weights,
    _daily_returns_matrix,
)
from sis_hw2.data.process import process_fundamentals, build_shares_panel
from sis_hw2.signals.factors import (
    adv_20_sessions,
    average_book_equity_for_income_window,
    annual_net_income,
    market_caps_on,
)


def test_two_asset_drift_zero_portfolio_return():
    """
    50/50 portfolio, +10% / -10% asset returns:
    portfolio return must be 0%; ending weights 55% / 45%.
    """
    w = pd.Series({"A": 0.5, "B": 0.5})
    r = pd.Series({"A": 0.10, "B": -0.10})
    port_r, drifted, miss = portfolio_return_and_drift(w, r)
    assert abs(port_r - 0.0) < 1e-12
    assert abs(drifted["A"] - 0.55) < 1e-12
    assert abs(drifted["B"] - 0.45) < 1e-12
    assert miss == 0.0


def test_missing_held_return_flagged_not_silent():
    w = pd.Series({"A": 0.6, "B": 0.4})
    r = pd.Series({"A": 0.10, "B": np.nan})
    port_r, drifted, miss = portfolio_return_and_drift(w, r)
    assert abs(miss - 0.4) < 1e-12
    # B treated as halt (r=0): port = 0.6*0.1 + 0.4*0 = 0.06
    assert abs(port_r - 0.06) < 1e-12


def test_buggy_formula_would_be_wrong():
    """Document the old bug: updating weights before return gave +1%."""
    w = pd.Series({"A": 0.5, "B": 0.5})
    r = pd.Series({"A": 0.10, "B": -0.10})
    w_wrong = w * (1.0 + r)
    buggy_r = float((w_wrong / w_wrong.sum() * r).sum())
    assert abs(buggy_r - 0.01) < 1e-12


def test_one_stock_buy_and_hold_matches_asset():
    w = pd.Series({"A": 1.0})
    r = pd.Series({"A": 0.03})
    port_r, drifted, _ = portfolio_return_and_drift(w, r)
    assert abs(port_r - 0.03) < 1e-12
    assert abs(drifted["A"] - 1.0) < 1e-12


def test_pct_change_no_implicit_fill():
    dates = pd.bdate_range("2020-01-01", periods=4)
    rows = [
        {"date": dates[0], "ticker": "A", "adj_close": 10.0},
        {"date": dates[1], "ticker": "A", "adj_close": 11.0},
        # missing A on dates[2]
        {"date": dates[3], "ticker": "A", "adj_close": 12.0},
        {"date": dates[0], "ticker": "B", "adj_close": 20.0},
        {"date": dates[1], "ticker": "B", "adj_close": 20.0},
        {"date": dates[2], "ticker": "B", "adj_close": 20.0},
        {"date": dates[3], "ticker": "B", "adj_close": 20.0},
    ]
    px = pd.DataFrame(rows)
    rets = _daily_returns_matrix(px)
    # Gap day for A should be NaN, not filled from 11->12
    assert pd.isna(rets.loc[dates[2], "A"])
    assert pd.isna(rets.loc[dates[3], "A"])  # prior missing -> pct from NaN


def test_zero_returns_with_costs_via_etf_engine():
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
    assert len(res.returns) > 0
    first = float(res.returns.iloc[0])
    assert first < 0
    if len(res.returns) > 1:
        assert abs(float(res.returns.iloc[1])) < 1e-12
    assert "PROPORTIONAL" in res.meta["cost_model"]


def test_spy_no_return_before_first_exec_etf():
    """Returns series starts at first execution close, not earlier."""
    dates = pd.DatetimeIndex(
        [
            pd.Timestamp("2020-01-29"),
            pd.Timestamp("2020-01-30"),
            pd.Timestamp("2020-01-31"),
            pd.Timestamp("2020-02-03"),
        ]
    )
    rows = []
    for d, px in zip(dates, [100.0, 101.0, 102.0, 103.0]):
        rows.append({"date": d, "ticker": "SPY", "adj_close": px})
    etf = pd.DataFrame(rows)
    res = portfolio_from_etf_weights(
        etf, {"SPY": 1.0}, start="2020-01-29", end="2020-02-03",
        cost_bps_per_side=0.0, execution="next_close",
    )
    assert res.meta["first_execution"] == "2020-02-03"
    assert res.returns.index.min() == pd.Timestamp("2020-02-03")


def test_drawdown_from_nav_one():
    from sis_hw2.metrics.performance import max_drawdown

    r = pd.Series([-0.10, 0.05, -0.02])
    dd = max_drawdown(r)
    assert dd <= -0.10 + 1e-12


def test_adv_requires_all_20_observations():
    from sis_hw2.signals.factors import adv_20_sessions

    cal = pd.bdate_range("2020-01-01", periods=30)
    rows = []
    for i, d in enumerate(cal):
        # Skip 5 days in the last 20 for ticker A only
        if not (10 <= i < 15):
            rows.append(
                {
                    "date": d,
                    "ticker": "A",
                    "close": 10.0,
                    "volume": 1000.0,
                    "adj_close": 10.0,
                }
            )
        rows.append(
            {
                "date": d,
                "ticker": "B",
                "close": 10.0,
                "volume": 1000.0,
                "adj_close": 10.0,
            }
        )
    px = pd.DataFrame(rows)
    asof = cal[-1]
    adv = adv_20_sessions(px, asof, pd.DatetimeIndex(cal))
    assert "A" not in adv.index or pd.isna(adv.get("A", np.nan))
    assert abs(float(adv["B"]) - 10_000.0) < 1e-8


def test_avg_book_matches_income_period_dates():
    fund = pd.DataFrame(
        [
            {"ticker": "X", "period_end": pd.Timestamp("2022-12-31"), "book_equity": 100.0, "net_income_q": 1.0, "statement_freq": "quarterly"},
            {"ticker": "X", "period_end": pd.Timestamp("2023-03-31"), "book_equity": 110.0, "net_income_q": 1.0, "statement_freq": "quarterly"},
            {"ticker": "X", "period_end": pd.Timestamp("2023-06-30"), "book_equity": 120.0, "net_income_q": 1.0, "statement_freq": "quarterly"},
            {"ticker": "X", "period_end": pd.Timestamp("2023-09-30"), "book_equity": 130.0, "net_income_q": 1.0, "statement_freq": "quarterly"},
            {"ticker": "X", "period_end": pd.Timestamp("2023-12-31"), "book_equity": 140.0, "net_income_q": 1.0, "statement_freq": "quarterly"},
        ]
    )
    start = pd.Series({"X": pd.Timestamp("2023-03-31")})
    end = pd.Series({"X": pd.Timestamp("2023-12-31")})
    avg = average_book_equity_for_income_window(
        fund, pd.Timestamp("2024-06-01"), lag_days=0, income_start=start, income_end=end
    )
    # book at/before start=110, at/before end=140 → 125
    assert abs(float(avg["X"]) - 125.0) < 1e-9


def test_no_gap_inferred_annual_income():
    """Sparse quarterly rows must not become annual via gap heuristic."""
    fund = pd.DataFrame(
        [
            {"ticker": "Y", "period_end": pd.Timestamp("2022-03-31"), "book_equity": 50.0, "net_income_q": 5.0, "statement_freq": np.nan},
            {"ticker": "Y", "period_end": pd.Timestamp("2023-03-31"), "book_equity": 55.0, "net_income_q": 6.0, "statement_freq": np.nan},
            {"ticker": "Y", "period_end": pd.Timestamp("2024-03-31"), "book_equity": 60.0, "net_income_q": 7.0, "statement_freq": "annual"},
        ]
    )
    processed = process_fundamentals(fund)
    # First two unknown/not annual; only vendor annual counts
    ann = annual_net_income(processed, pd.Timestamp("2024-12-31"), lag_days=0)
    assert float(ann["Y"]) == 7.0
    # Without vendor annual label, gap-inferred must not invent annual
    fund2 = fund.copy()
    fund2["statement_freq"] = pd.Series([None, None, None], dtype=object)
    processed2 = process_fundamentals(fund2)
    assert (processed2["statement_freq"] == "annual").sum() == 0
    ann2 = annual_net_income(processed2, pd.Timestamp("2024-12-31"), lag_days=0)
    assert pd.isna(ann2.get("Y", np.nan))


def test_bs_shares_use_availability_not_period_end(tmp_path):
    fund = pd.DataFrame(
        [
            {
                "ticker": "Z",
                "period_end": pd.Timestamp("2023-12-31"),
                "shares_bs": 1_000_000.0,
                "book_equity": 10.0,
                "net_income_q": 1.0,
                "statement_freq": "annual",
                "_meta": False,
            }
        ]
    )
    prices = pd.DataFrame(
        {
            "date": pd.bdate_range("2023-12-01", periods=80),
            "ticker": "Z",
            "close": 10.0,
            "adj_close": 10.0,
            "volume": 1e5,
        }
    )
    sh = build_shares_panel(tmp_path, fund, prices, bs_availability_lag_days=60)
    assert sh["source"].iloc[0] == "balance_sheet_lagged"
    assert sh["date"].iloc[0] == pd.Timestamp("2023-12-31") + pd.Timedelta(days=60)


def test_constant_latest_excluded_from_mcap():
    prices = pd.DataFrame(
        [
            {"date": pd.Timestamp("2024-01-02"), "ticker": "C", "close": 50.0, "adj_close": 50.0, "volume": 1e6},
            {"date": pd.Timestamp("2024-01-03"), "ticker": "C", "close": 50.0, "adj_close": 50.0, "volume": 1e6},
        ]
    )
    shares = pd.DataFrame(
        [
            {"date": pd.Timestamp("2024-01-01"), "ticker": "C", "shares": 1e6, "source": "constant_latest"},
            {"date": pd.Timestamp("2024-01-03"), "ticker": "C", "shares": 1e6, "source": "constant_latest"},
        ]
    )
    mcap, src = market_caps_on(prices, shares, pd.Timestamp("2024-01-03"))
    assert pd.isna(mcap["C"])
    assert src["C"] == "constant_latest"
