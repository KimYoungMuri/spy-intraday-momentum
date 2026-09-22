#!/usr/bin/env python3
"""One-command analysis runner for B9339 HW1."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import date, datetime, time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sis_hw1.backtest import buy_and_hold_spy, run_backtest
from sis_hw1.config import load_config, resolve_path
from sis_hw1.data import audit_and_clean
from sis_hw1.metrics import (
    block_bootstrap_sharpe,
    fmt5,
    regression_on_spy,
    summarize_equity,
    trade_stats,
)


def _ensure_dirs(cfg):
    for k in ("processed_dir", "outputs_dir", "logs_dir", "reports_dir"):
        resolve_path(cfg, k).mkdir(parents=True, exist_ok=True)
    for sub in ("figures", "tables", "traces", "ledgers"):
        (resolve_path(cfg, "outputs_dir") / sub).mkdir(parents=True, exist_ok=True)


def _eligible_start(clean: pd.DataFrame, lookback: int = 14) -> date:
    sessions = sorted(clean["session_date"].unique())
    # Need lookback prior sessions in the intraday sample
    return sessions[lookback]


def _save_summary_table(rows: list[dict], path: Path):
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    # human-readable with 5 decimals
    disp = df.copy()
    for c in disp.columns:
        if pd.api.types.is_float_dtype(disp[c]):
            disp[c] = disp[c].map(lambda x: fmt5(x))
    disp.to_csv(path.with_name(path.stem + "_display5.csv"), index=False)
    return df


def plot_wealth(
    daily_map: dict[str, pd.DataFrame],
    path: Path,
    title: str,
    initial_equity: float = 100_000.0,
):
    """Normalize by original initial equity and include the pre-sample point at 1.0."""
    fig, ax = plt.subplots(figsize=(10, 5))
    for label, d in daily_map.items():
        if d is None or d.empty:
            continue
        dates = pd.to_datetime(d["session_date"])
        # Start one calendar day before first session for the initial mark at 1.0
        t0 = dates.iloc[0] - pd.Timedelta(days=1)
        wealth = np.concatenate(
            [[1.0], (d["equity_end"].to_numpy(dtype=float) / float(initial_equity))]
        )
        ax.plot(
            [t0] + list(dates),
            wealth,
            label=label,
            linewidth=1.5,
        )
    ax.set_title(title)
    ax.set_ylabel(f"Normalized wealth (E / {initial_equity:,.0f})")
    ax.set_xlabel("Date")
    ax.axhline(1.0, color="gray", linewidth=0.8, alpha=0.5)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_drawdown(daily: pd.DataFrame, path: Path, label: str):
    eq = daily["equity_end"].to_numpy()
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.fill_between(pd.to_datetime(daily["session_date"]), dd, 0, alpha=0.5)
    ax.set_title(f"Drawdown — {label}")
    ax.set_ylabel("Drawdown")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_monthly(daily: pd.DataFrame, path: Path, label: str):
    d = daily.copy()
    d["session_date"] = pd.to_datetime(d["session_date"])
    d["month"] = d["session_date"].dt.to_period("M")
    # compound within month
    mrets = d.groupby("month", group_keys=False).apply(
        lambda g: float((1 + g["daily_return"]).prod() - 1), include_groups=False
    )
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.bar(range(len(mrets)), mrets.values)
    ax.set_xticks(range(len(mrets)))
    ax.set_xticklabels([str(x) for x in mrets.index], rotation=45, ha="right")
    ax.set_title(f"Monthly returns — {label}")
    ax.set_ylabel("Return")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_day_trace(bars: pd.DataFrame, session: date, path: Path, title: str, trades: pd.DataFrame | None = None):
    b = bars[bars["session_date"] == session].copy()
    if b.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = range(len(b))
    ax.plot(x, b["price"], label="Price", color="black")
    ax.plot(x, b["upper"], label="Upper", linestyle="--")
    ax.plot(x, b["lower"], label="Lower", linestyle="--")
    if b["vwap"].notna().any():
        ax.plot(x, b["vwap"], label="VWAP proxy", linestyle=":")
    # annotate fills
    if trades is not None and not trades.empty:
        tday = trades[trades["session_date"] == session]
        avail_list = [str(a) for a in b["available_at"]]
        for _, tr in tday.iterrows():
            key = str(tr["available_at"])
            if key in avail_list:
                i = avail_list.index(key)
                ax.scatter([i], [tr["fill_price"]], s=60, zorder=5)
                ax.annotate(
                    tr["reason"].replace("BC_", "").replace("session_", ""),
                    (i, tr["fill_price"]),
                    textcoords="offset points",
                    xytext=(0, 8),
                    ha="center",
                    fontsize=7,
                )
    pos = b["position"].to_numpy()
    for i in range(1, len(pos)):
        if pos[i] != pos[i - 1]:
            ax.axvline(i, color="gray", alpha=0.35)
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(t) for t in b["available_at"]], rotation=45, ha="right")
    ax.set_title(title)
    ax.set_ylabel("Price")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def export_session_trace(res, session: date, path: Path):
    b = res.bars[res.bars["session_date"] == session].copy()
    t = res.trades[res.trades["session_date"] == session].copy() if not res.trades.empty else pd.DataFrame()
    b.to_csv(path.with_name(path.stem + "_bars.csv"), index=False)
    t.to_csv(path.with_name(path.stem + "_trades.csv"), index=False)


def main():
    cfg = load_config()
    _ensure_dirs(cfg)
    out = resolve_path(cfg, "outputs_dir")
    processed = resolve_path(cfg, "processed_dir")
    logs = resolve_path(cfg, "logs_dir")
    reports = resolve_path(cfg, "reports_dir")

    log_events = []
    def log(msg: str):
        ts = datetime.now().isoformat(timespec="seconds")
        line = f"[{ts}] {msg}"
        print(line)
        log_events.append(line)

    log("Starting HW1 pipeline")
    workbook = resolve_path(cfg, "raw_workbook")
    if not workbook.exists():
        log(f"MISSING workbook: {workbook}")
        sys.exit(1)

    clean, daily, audit = audit_and_clean(workbook, processed)
    log(f"Audit complete: {audit.summary['n_sessions']} sessions, "
        f"{audit.summary['intraday_first']} → {audit.summary['intraday_last']}")

    # Inclusion calendar
    sessions = sorted(clean["session_date"].unique())
    lookback = cfg["strategy"]["band_lookback"]
    eval_start = _eligible_start(clean, lookback)
    eval_end = sessions[-1]  # include Dec 1
    nov_end = date(2025, 11, 28)  # last Nov session in sample (half-day); use last Nov trading day
    nov_sessions = [s for s in sessions if s.month <= 11 or s.year < 2025]
    # better: through November
    through_nov = [s for s in sessions if s <= date(2025, 11, 30)]
    eval_end_nov = through_nov[-1] if through_nov else eval_end

    calendar = pd.DataFrame({
        "session_date": sessions,
        "in_eval_core": [(s >= eval_start) and (s <= eval_end) for s in sessions],
        "reason_if_excluded": [
            "warm-up: need 14 prior intraday sessions for bands" if s < eval_start else ""
            for s in sessions
        ],
        "is_half_day": [s in {date(2025, 7, 3), date(2025, 11, 28)} for s in sessions],
    })
    calendar.to_csv(processed / "inclusion_exclusion_calendar.csv", index=False)
    log(f"Eval window: {eval_start} → {eval_end} (N expected ~{sum(calendar['in_eval_core'])})")

    S = cfg["strategy"]
    common_kwargs = dict(
        initial_equity=S["initial_equity"],
        band_lookback=S["band_lookback"],
        sizing_lookback=S["sizing_lookback"],
        vm=S["volatility_multiplier"],
        vol_target=S["vol_target_daily"],
        max_leverage=S["max_leverage"],
        commission=S["commission_per_share"],
        slippage=S["slippage_per_share"],
        eval_start=eval_start,
        eval_end=eval_end,
    )

    results = {}
    for v in ("A", "B", "C"):
        log(f"Running variant {v}...")
        results[v] = run_backtest(clean, daily, v, **common_kwargs)
        results[v].daily.to_csv(out / "ledgers" / f"daily_{v}.csv", index=False)
        results[v].trades.to_csv(out / "ledgers" / f"trades_{v}.csv", index=False)
        results[v].bars.to_csv(out / "ledgers" / f"bars_{v}.csv", index=False)

    spy = buy_and_hold_spy(daily, eval_start, eval_end, S["initial_equity"])
    spy.to_csv(out / "ledgers" / "daily_SPY_BH.csv", index=False)

    # Summaries
    summary_rows = []
    trade_rows = []
    for v, res in results.items():
        s = summarize_equity(res.daily, initial_equity=S["initial_equity"], label=v)
        s.update(trade_stats(res.trades))
        reg = regression_on_spy(res.daily, spy.rename(columns={"daily_return": "daily_return"}))
        # spy already has daily_return
        s.update({f"reg_{k}": val for k, val in reg.items()})
        boot = block_bootstrap_sharpe(
            res.daily["daily_return"].to_numpy(),
            block_length=cfg["bootstrap"]["block_length"],
            n_resamples=cfg["bootstrap"]["n_resamples"],
            seed=cfg["bootstrap"]["seed"],
        )
        s.update({f"boot_{k}": val for k, val in boot.items()})
        summary_rows.append(s)
        log(f"  {v}: total_return={s['total_return']:.5f}, Sharpe={s['sharpe']:.5f}, "
            f"end_eq={s['end_equity']:.5f}, trades={s.get('n_trade_events')}")

    spy_s = summarize_equity(spy, initial_equity=S["initial_equity"], label="SPY_BH")
    summary_rows.append(spy_s)
    summary_df = _save_summary_table(summary_rows, out / "tables" / "core_summary.csv")

    # Through-November sensitivity for C
    res_nov = run_backtest(clean, daily, "C", **{**common_kwargs, "eval_end": eval_end_nov})
    s_nov = summarize_equity(res_nov.daily, initial_equity=S["initial_equity"], label="C_through_Nov")
    _save_summary_table([s_nov], out / "tables" / "c_through_november.csv")

    # Robustness grid
    sens_rows = []
    # lookbacks
    for lb in cfg["sensitivity"]["band_lookbacks"]:
        start_lb = _eligible_start(clean, lb)
        # matched period across lookbacks: use max start
        pass  # collect first
    max_start = max(_eligible_start(clean, lb) for lb in cfg["sensitivity"]["band_lookbacks"])
    for lb in cfg["sensitivity"]["band_lookbacks"]:
        for v in ("A", "B", "C"):
            r = run_backtest(
                clean, daily, v,
                **{**common_kwargs, "band_lookback": lb, "eval_start": max_start},
            )
            s = summarize_equity(r.daily, initial_equity=S["initial_equity"], label=f"{v}_lb{lb}")
            s["band_lookback"] = lb
            s["matched_start"] = str(max_start)
            sens_rows.append(s)

    for vm in cfg["sensitivity"]["volatility_multipliers"]:
        for v in ("A", "B", "C"):
            r = run_backtest(clean, daily, v, **{**common_kwargs, "vm": vm})
            s = summarize_equity(r.daily, initial_equity=S["initial_equity"], label=f"{v}_vm{vm}")
            s["vm"] = vm
            sens_rows.append(s)

    for cap in cfg["sensitivity"]["exposure_caps"]:
        r = run_backtest(clean, daily, "C", **{**common_kwargs, "max_leverage": cap})
        s = summarize_equity(r.daily, initial_equity=S["initial_equity"], label=f"C_cap{cap}")
        s["max_leverage"] = cap
        sens_rows.append(s)

    for slip in cfg["sensitivity"]["slippage_stress"]:
        for v in ("A", "B", "C"):
            r = run_backtest(clean, daily, v, **{**common_kwargs, "slippage": slip})
            s = summarize_equity(r.daily, initial_equity=S["initial_equity"], label=f"{v}_slip{slip}")
            s["slippage"] = slip
            sens_rows.append(s)

    # delayed fills
    for v in ("A", "B", "C"):
        r = run_backtest(clean, daily, v, **{**common_kwargs, "fill_mode": "delay_one"})
        s = summarize_equity(r.daily, initial_equity=S["initial_equity"], label=f"{v}_delay")
        s["fill_mode"] = "delay_one"
        sens_rows.append(s)

    # band-only exits for B/C
    for v in ("B", "C"):
        r = run_backtest(clean, daily, v, **{**common_kwargs, "use_vwap": False})
        s = summarize_equity(r.daily, initial_equity=S["initial_equity"], label=f"{v}_band_only")
        s["use_vwap"] = False
        sens_rows.append(s)

    sens_df = _save_summary_table(sens_rows, out / "tables" / "sensitivity.csv")
    log(f"Sensitivity rows: {len(sens_df)}")

    # Plots
    plot_wealth(
        {v: results[v].daily for v in results} | {"SPY_BH": spy},
        out / "figures" / "normalized_wealth.png",
        f"Normalized wealth ({eval_start} to {eval_end})",
        initial_equity=S["initial_equity"],
    )
    # Multi-strategy drawdown comparison
    fig, ax = plt.subplots(figsize=(10, 4))
    for label, dframe in {**{v: results[v].daily for v in results}, "SPY_BH": spy}.items():
        eq = np.concatenate([[S["initial_equity"]], dframe["equity_end"].to_numpy(dtype=float)])
        peak = np.maximum.accumulate(eq)
        dd = eq / peak - 1.0
        dates = [pd.Timestamp(eval_start) - pd.Timedelta(days=1)] + list(pd.to_datetime(dframe["session_date"]))
        ax.plot(dates, dd, label=label, linewidth=1.2)
    ax.set_title(f"Drawdown from peak equity including initial $100,000 ({eval_start} to {eval_end})")
    ax.set_ylabel("Drawdown")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "figures" / "drawdown_comparison.png", dpi=150)
    plt.close(fig)

    plot_drawdown(results["C"].daily, out / "figures" / "drawdown_C.png", "Variant C")
    plot_monthly(results["C"].daily, out / "figures" / "monthly_C.png", "Variant C")

    # Leverage plot for C
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(pd.to_datetime(results["C"].daily["session_date"]), results["C"].daily["exposure"])
    ax.set_title("Variant C daily exposure multiple")
    ax.set_ylabel("Exposure")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "figures" / "leverage_C.png", dpi=150)
    plt.close(fig)

    # Selected day traces
    # Prefer a day with trades, plus half-days
    traded_days = results["C"].daily[results["C"].daily["n_trades"] > 0]["session_date"].tolist()
    pick = date(2025, 10, 10) if date(2025, 10, 10) >= eval_start else (
        traded_days[len(traded_days) // 2] if traded_days else eval_start
    )
    plot_day_trace(
        results["C"].bars, pick,
        out / "figures" / f"trace_C_{pick}.png",
        f"Variant C annotated session — {pick}",
        trades=results["C"].trades,
    )
    export_session_trace(results["C"], pick, out / "traces" / f"C_{pick}")
    for hd in (date(2025, 7, 3), date(2025, 11, 28)):
        if hd >= eval_start:
            plot_day_trace(
                results["C"].bars, hd,
                out / "figures" / f"trace_C_{hd}.png",
                f"Variant C half-day — {hd}",
                trades=results["C"].trades,
            )
            export_session_trace(results["C"], hd, out / "traces" / f"C_{hd}")
            export_session_trace(results["A"], hd, out / "traces" / f"A_{hd}")

    # Assumptions / deviations table
    deviations = pd.DataFrame([
        {
            "topic": "Opening price",
            "paper": "True 09:30 open O_d",
            "this_replication": "First regular bar endpoint as open_proxy (available at 10:00 under bar-start shift)",
            "impact": "Adaptation; gap adjustment spans overnight + first 30m; first entry ordinarily at 10:30 availability",
        },
        {
            "topic": "Timestamp convention",
            "paper": "Semi-hourly decisions at HH:00/HH:30 with 1-minute data",
            "this_replication": "Inferred bar-start labels; availability = label+30m",
            "impact": "Idealized endpoint execution; unresolved if labels are bar-end",
        },
        {
            "topic": "VWAP",
            "paper": "VWAP from market-hours trade data",
            "this_replication": "Endpoint-weighted proxy using interval volumes × endpoint prices",
            "impact": "Approximation; band-only diagnostic included",
        },
        {
            "topic": "Volume field",
            "paper": "Trade volume for VWAP",
            "this_replication": "Volume, AV treated as per-interval (not cumulative)",
            "impact": "Supported by within-session decreases; 16:00 residual excluded from VWAP",
        },
        {
            "topic": "B/C entry with VWAP",
            "paper": "Enter on band break; stop = max/min(band, VWAP)",
            "this_replication": "Operational entry requires price beyond stop threshold to avoid instant exit",
            "impact": "Documented interpretation of combined conditions",
        },
        {
            "topic": "Benchmark",
            "paper": "SPY buy&hold (total vs price return not fully specified in main tables)",
            "this_replication": "Buy-and-hold on supplied Last Price series; adjustment/dividend basis unverified",
            "impact": "Described as price-series return until verified",
        },
        {
            "topic": "Sample period",
            "paper": "May 2007–Apr 2024 (headline)",
            "this_replication": f"{eval_start} to {eval_end} after warm-up (~8 months instructor data)",
            "impact": "Cannot reproduce headline 19.6%/1.33 Sharpe; limited subgroup power",
        },
    ])
    deviations.to_csv(out / "tables" / "assumptions_deviations.csv", index=False)

    # Machine-readable results blob for the report
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "eval_start": str(eval_start),
        "eval_end": str(eval_end),
        "eval_end_nov": str(eval_end_nov),
        "audit_summary": audit.summary,
        "chatgpt_checks": audit.chatgpt_supplied_checks,
        "core_summary": summary_rows,
        "c_through_nov": s_nov,
        "n_sensitivity": len(sens_rows),
        "python": sys.version,
    }
    with open(out / "tables" / "results_payload.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

    with open(logs / "run_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log_events))

    log("Pipeline complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
