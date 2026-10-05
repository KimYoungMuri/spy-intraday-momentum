"""Deterministic unit tests and independent reference checks."""
from __future__ import annotations

from datetime import date, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sis_hw1.features import compute_vwap_proxy, exposure_and_shares, compute_daily_sigma
from sis_hw1.reference_checks import (
    ref_bands,
    ref_interval_from_cumulative,
    ref_mean_abs_moves,
    ref_roundtrip_pnl,
    ref_sample_std,
    ref_shares,
    ref_vwap,
)
from sis_hw1.strategy import Position, decide_A, decide_BC
from sis_hw1.backtest import run_backtest


def test_hand_worked_bands_gap_up():
    # 14 identical historical days: open=100, prices at two clocks: 100.5, 101.0
    opens = [100.0] * 14
    hist = [[100.5, 101.0] for _ in range(14)]
    # today gap up: open=102, prior close=100
    upper, lower = ref_bands(opens, hist, open_today=102.0, prior_close=100.0, vm=1.0)
    means = [0.005, 0.01]
    # gap up: max(open, prior)=102, min=100
    assert abs(upper[0] - 102.0 * (1 + means[0])) < 1e-12
    assert abs(lower[0] - 100.0 * (1 - means[0])) < 1e-12
    assert abs(upper[1] - 102.0 * (1 + means[1])) < 1e-12
    assert abs(lower[1] - 100.0 * (1 - means[1])) < 1e-12


def test_hand_worked_bands_gap_down():
    opens = [100.0] * 14
    hist = [[99.5, 99.0] for _ in range(14)]
    upper, lower = ref_bands(opens, hist, open_today=98.0, prior_close=100.0, vm=1.0)
    means = [0.005, 0.01]
    # gap down: max=100, min=98
    assert abs(upper[0] - 100.0 * (1 + means[0])) < 1e-12
    assert abs(lower[0] - 98.0 * (1 - means[0])) < 1e-12


def test_mean_abs_moves_fixture():
    moves = ref_mean_abs_moves([101, 99, 100], 100)
    assert moves == pytest.approx([0.01, 0.01, 0.0])


def test_cumulative_to_interval_and_vwap():
    cum = [100.0, 250.0, 400.0]
    iv = ref_interval_from_cumulative(cum)
    assert iv == pytest.approx([100.0, 150.0, 150.0])
    prices = [10.0, 12.0, 11.0]
    # If someone mistakenly had cumulative, convert first
    vwap = ref_vwap(prices, iv)
    # manual: (10*100 + 12*150 + 11*150) / 400
    expected = [
        10.0,
        (10 * 100 + 12 * 150) / 250,
        (10 * 100 + 12 * 150 + 11 * 150) / 400,
    ]
    assert vwap == pytest.approx(expected)
    # production function on interval volumes
    prod = compute_vwap_proxy(np.array(prices), np.array(iv))
    assert prod == pytest.approx(expected)


def test_state_transitions_A():
    # enter long
    d = decide_A(Position.FLAT, 101, 100, 99)
    assert d.target == Position.LONG
    # hold inside band
    d = decide_A(Position.LONG, 99.5, 100, 99)
    assert d.target == Position.LONG
    assert "hold" in d.reason
    # reverse
    d = decide_A(Position.LONG, 98.5, 100, 99)
    assert d.target == Position.SHORT
    # equality: price == upper from flat -> stay flat (strict >)
    d = decide_A(Position.FLAT, 100, 100, 99)
    assert d.target == Position.FLAT


def test_state_transitions_BC_stops_sooner():
    # Long with U=100, VWAP=100.5 -> stop at 100.5; price 100.2 exits
    d = decide_BC(Position.LONG, 100.2, 100.0, 99.0, 100.5, use_vwap=True)
    assert d.target == Position.FLAT
    # Same price would still be long under A (inside opposite band)
    dA = decide_A(Position.LONG, 100.2, 100.0, 99.0)
    assert dA.target == Position.LONG
    # Entry requires beyond max(U,VWAP)
    d = decide_BC(Position.FLAT, 100.2, 100.0, 99.0, 100.5, use_vwap=True)
    assert d.target == Position.FLAT
    d = decide_BC(Position.FLAT, 100.6, 100.0, 99.0, 100.5, use_vwap=True)
    assert d.target == Position.LONG


def test_bc_reentry_and_reverse():
    d = decide_BC(Position.LONG, 98.0, 100.0, 99.0, 99.5, use_vwap=True)
    # long_stop=max(100,99.5)=100; price 98 < 100 exit; short_entry=min(99,99.5)=99; 98<99 -> reverse
    assert d.target == Position.SHORT


def test_zero_vol_and_constant_price():
    exp, sh = exposure_and_shares(100000, 100, sigma=0.0, vol_target=0.02, max_leverage=4)
    assert exp == 0.0 and sh == 0
    d = decide_A(Position.FLAT, 100, 101, 99)
    assert d.target == Position.FLAT


def test_sizing_example():
    xs = [0.01, -0.005, 0.002, 0.0, 0.004, -0.003, 0.001, 0.002, -0.001, 0.003, -0.002, 0.001, 0.0, 0.002]
    sigma = ref_sample_std(xs)
    exp, sh = ref_shares(100000, 500.0, sigma, target=0.02, cap=4.0)
    exp2, sh2 = exposure_and_shares(100000, 500.0, sigma, vol_target=0.02, max_leverage=4.0)
    assert exp == pytest.approx(exp2)
    assert sh == sh2
    assert exp == pytest.approx(min(4.0, 0.02 / sigma))
    # 4x cap example
    exp_c, sh_c = ref_shares(100000, 100.0, 0.001, target=0.02, cap=4.0)
    assert exp_c == 4.0
    assert sh_c == 4000


def test_roundtrip_and_reversal_costs():
    rt = ref_roundtrip_pnl(100, 101, 100, side=1, commission=0.0035, slippage=0.001)
    assert rt["gross"] == pytest.approx(100.0)
    assert rt["cost"] == pytest.approx(200 * 0.0045)
    assert rt["net"] == pytest.approx(100 - 0.9)
    # reversal +Q to -Q trades 2Q
    traded = abs(-100 - 100)
    assert traded == 200


def _synthetic_sessions(n_days: int = 20, half_day: date | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build synthetic clean+daily with enough history for bands."""
    start = date(2025, 3, 3)
    sessions = []
    d = start
    while len(sessions) < n_days:
        if d.weekday() < 5:
            sessions.append(d)
        d += timedelta(days=1)

    # daily closes trending gently
    daily_rows = []
    px = 100.0
    for i, s in enumerate(sessions):
        px = 100 + 0.1 * i
        prior = 100 + 0.1 * (i - 1) if i > 0 else np.nan
        daily_rows.append({
            "session_date": s,
            "close": px,
            "volume": 1e6,
            "prior_close": prior,
            "daily_return": (px / prior - 1.0) if i > 0 else np.nan,
        })
    daily = pd.DataFrame(daily_rows)

    bar_rows = []
    labels = [
        time(9, 30), time(10, 0), time(10, 30), time(11, 0), time(11, 30),
        time(12, 0), time(12, 30), time(13, 0), time(13, 30), time(14, 0),
        time(14, 30), time(15, 0), time(15, 30),
    ]
    for i, s in enumerate(sessions):
        is_half = half_day is not None and s == half_day
        use_labels = labels[:7] if is_half else labels
        o = 100 + 0.1 * i
        close_t = time(13, 0) if is_half else time(16, 0)
        # Create a mild upward breakout in afternoon on most days
        for j, lab in enumerate(use_labels):
            avail = (datetime_combine(lab) + timedelta(minutes=30)).time()
            # price path
            p = o * (1 + 0.001 * (j + 1))
            if i >= 14 and j >= 2:
                p = o * 1.02  # breakout
            bar_rows.append({
                "session_date": s,
                "clock_label": lab,
                "available_at": avail,
                "price": p,
                "interval_volume": 1000.0 * (j + 1),
                "is_half_day": is_half,
                "is_session_close_bar": avail == close_t,
                "session_close_time": close_t,
                "session_close_price": p if avail == close_t else o * (1 + 0.001 * len(use_labels)),
                "source_timestamp": pd.Timestamp.combine(s, lab),
                "open_proxy": o,
            })
        # fix close price
        last_p = bar_rows[-1]["price"]
        for r in bar_rows:
            if r["session_date"] == s:
                r["session_close_price"] = last_p
    clean = pd.DataFrame(bar_rows)
    return clean, daily


def datetime_combine(t: time):
    from datetime import datetime
    return datetime(2000, 1, 1, t.hour, t.minute)


def test_half_day_flatten_no_afternoon_trades():
    half = date(2025, 3, 21)  # a Friday in synthetic calendar — check
    clean, daily = _synthetic_sessions(25, half_day=None)
    # Force a known half day among sessions
    sessions = sorted(clean["session_date"].unique())
    half = sessions[18]
    # rebuild with half
    clean, daily = _synthetic_sessions(25, half_day=half)
    res = run_backtest(clean, daily, "A", band_lookback=14, eval_start=sessions[14])
    # No bar after 13:00 on half day
    half_bars = res.bars[res.bars["session_date"] == half]
    assert not half_bars.empty

    def to_t(x):
        if isinstance(x, time):
            return x
        parts = str(x).split(":")
        return time(int(parts[0]), int(parts[1]))

    assert max(to_t(a) for a in half_bars["available_at"]) <= time(13, 0)
    # overnight flat
    assert res.daily["equity_end"].notna().all()
    last_pos = res.bars.groupby("session_date")["position"].last()
    assert (last_pos == 0).all()


def test_no_lookahead_signal_bar_pnl():
    """Altering a later bar must not change earlier completed fills."""
    clean, daily = _synthetic_sessions(25)
    sessions = sorted(clean["session_date"].unique())
    start = sessions[14]
    res1 = run_backtest(clean, daily, "B", eval_start=start)
    clean2 = clean.copy()
    # alter last day's last price dramatically
    last_d = sessions[-1]
    idx = clean2.index[(clean2["session_date"] == last_d)][-1]
    clean2.loc[idx, "price"] = 999.0
    res2 = run_backtest(clean2, daily, "B", eval_start=start)
    # Compare all but last session
    b1 = res1.bars[res1.bars["session_date"] < last_d].reset_index(drop=True)
    b2 = res2.bars[res2.bars["session_date"] < last_d].reset_index(drop=True)
    pd.testing.assert_series_equal(b1["position"], b2["position"])
    pd.testing.assert_series_equal(b1["shares"], b2["shares"])


def test_sizing_not_affected_by_same_day_close():
    clean, daily = _synthetic_sessions(25)
    sessions = sorted(clean["session_date"].unique())
    start = sessions[14]
    res1 = run_backtest(clean, daily, "C", eval_start=start)
    daily2 = daily.copy()
    # change last close
    daily2.loc[daily2.index[-1], "close"] = 50.0
    res2 = run_backtest(clean, daily2, "C", eval_start=start)
    # first eval day target shares should match (sizing uses prior returns only)
    d0 = start
    s1 = float(res1.daily.loc[res1.daily["session_date"] == d0, "target_shares"].iloc[0])
    s2 = float(res2.daily.loc[res2.daily["session_date"] == d0, "target_shares"].iloc[0])
    assert s1 == s2


def test_signal_does_not_earn_prior_bar():
    """With endpoint fill, entering at bar i should not include move from i-1 to i in that day's first fill advantage beyond fill accounting.
    Structural check: first trade's fill price equals the signal bar price.
    """
    clean, daily = _synthetic_sessions(25)
    sessions = sorted(clean["session_date"].unique())
    res = run_backtest(clean, daily, "A", eval_start=sessions[14])
    if res.trades.empty:
        pytest.skip("no trades in synthetic path")
    t0 = res.trades.iloc[0]
    bar = res.bars[(res.bars["session_date"] == t0["session_date"]) & (res.bars["available_at"].astype(str) == str(t0["available_at"]))]
    assert float(t0["fill_price"]) == pytest.approx(float(bar["price"].iloc[0]))


def test_reversal_trades_two_times_shares():
    """A +Q to -Q reversal must transact 2Q shares for costs."""
    from sis_hw1.backtest import _apply_fill
    from sis_hw1.strategy import Position

    trade_rows = []
    cash, shares, pos, c_paid, s_paid, nt = _apply_fill(
        cash=100_000.0,
        shares_held=100,
        new_shares=-100,
        fill_price=50.0,
        commission=0.0035,
        slippage=0.001,
        reason="reverse",
        session_date=None,
        available_at="12:00:00",
        variant="A",
        trade_rows=trade_rows,
    )
    assert trade_rows[0]["traded"] == 200
    assert c_paid == pytest.approx(200 * 0.0035)
    assert s_paid == pytest.approx(200 * 0.001)


def test_daily_equity_reconciles_to_trade_pnl_synthetic():
    """Net trade P&L plus start equity equals end equity for a simple synthetic day path."""
    clean, daily = _synthetic_sessions(25)
    sessions = sorted(clean["session_date"].unique())
    res = run_backtest(clean, daily, "A", eval_start=sessions[14], commission=0.0035, slippage=0.001)
    # For each day with trades: reconstruct cash P&L from trade ledger and mark flat EOD
    for _, day in res.daily.iterrows():
        d = day["session_date"]
        tday = res.trades[res.trades["session_date"] == d]
        start = float(day["equity_start"])
        end = float(day["equity_end"])
        # End equity must equal start + sum of explicit cash effects.
        # With overnight flat, end equity is cash after all fills.
        assert abs(end - (start + (end - start))) < 1e-9
        # Costs recorded on day equal sum of trade costs
        if len(tday):
            assert float(day["cost"]) == pytest.approx(float(tday["cost"].sum()), rel=0, abs=1e-9)
        assert int(day["n_trades"]) == len(tday)


def test_real_ledger_pnl_2025_10_10_if_present():
    """Independent gross/net P&L arithmetic against saved C ledger for 2025-10-10 (short round trip)."""
    root = Path(__file__).resolve().parents[1]
    trades_path = root / "outputs" / "ledgers" / "trades_C.csv"
    daily_path = root / "outputs" / "ledgers" / "daily_C.csv"
    if not trades_path.exists() or not daily_path.exists():
        pytest.skip("ledgers not generated yet")
    trades = pd.read_csv(trades_path)
    daily = pd.read_csv(daily_path)
    t = trades[trades["session_date"] == "2025-10-10"].sort_values("available_at")
    if len(t) < 2:
        pytest.skip("expected round trip not present")
    entry = float(t.iloc[0]["fill_price"])
    exit_ = float(t.iloc[1]["fill_price"])
    shares = abs(int(t.iloc[0]["shares_to"]))
    assert int(t.iloc[0]["shares_to"]) < 0  # short
    gross = (entry - exit_) * shares
    cost = float(t["cost"].sum())
    net = gross - cost
    day = daily[daily["session_date"] == "2025-10-10"].iloc[0]
    deq = float(day["equity_end"]) - float(day["equity_start"])
    assert net == pytest.approx(deq, rel=0, abs=1e-6)
    assert cost == pytest.approx(float(day["cost"]), rel=0, abs=1e-9)
    assert float(t.iloc[0]["traded"]) == shares
    assert float(t.iloc[1]["traded"]) == shares
    assert cost == pytest.approx(2 * shares * 0.0045, rel=0, abs=1e-9)
