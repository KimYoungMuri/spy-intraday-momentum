#!/usr/bin/env python3
"""End-to-end research runner: download -> process -> backtest -> charts -> tables."""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sis_hw2.utils.io import save_frame, load_frame
from sis_hw2.utils.config import load_config, ensure_dirs, project_root
from sis_hw2.data.universe import save_universe
from sis_hw2.data.download import run_download, download_etf_benchmarks, download_fred_rf
from sis_hw2.data.process import run_process
from sis_hw2.backtest.engine import run_backtest, portfolio_from_etf_weights
from sis_hw2.metrics.performance import summarize, format_summary_table, cumulative_returns, annual_returns


def save_fig(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def etf_daily_returns(etf: pd.DataFrame, ticker: str) -> pd.Series:
    g = etf[etf["ticker"] == ticker].sort_values("date").set_index("date")["adj_close"]
    return g.pct_change().dropna().rename(ticker)


def run_etf_proxy_study(cfg, etf, rf, tables, figures, start, end, tag=""):
    """Separately labeled real-data factor ETF proxy — NOT the stock strategy."""
    spy = etf_daily_returns(etf, cfg["benchmarks"]["primary_etf"])
    available = set(etf["ticker"].unique())
    legs = [t for t in ["VLUE", "QUAL", "MTUM"] if t in available]
    if len(legs) < 2:
        legs = [t for t in ["VTV", "SPHQ", "PDP"] if t in available]
    w = {t: 1 / len(legs) for t in legs}
    proxy = portfolio_from_etf_weights(
        etf, w, start, end,
        cost_bps_per_side=cfg["costs"]["baseline_bps_per_side"],
        name="ETF_proxy_equal_VQM",
        execution="next_close",
    )
    rf_s = rf.set_index("date")["rf_daily"]
    spy_a = spy.reindex(proxy.returns.index)
    summ = {
        "ETF_proxy_VQM": summarize(proxy.returns, spy_a, rf_s),
        "SPY": summarize(spy_a.dropna(), None, rf_s),
    }
    for t in legs:
        r = etf_daily_returns(etf, t).reindex(proxy.returns.index)
        summ[t] = summarize(r.dropna(), spy_a, rf_s)
    df = format_summary_table(summ)
    suffix = f"_{tag}" if tag else ""
    df.to_csv(tables / f"etf_proxy_summary{suffix}.csv", float_format="%.8f")
    plt.figure(figsize=(10, 5))
    cumulative_returns(proxy.returns).plot(label="ETF proxy V/Q/M")
    cumulative_returns(spy_a.fillna(0)).plot(label="SPY")
    plt.legend()
    plt.title("LABELLED ETF PROXY (not stock-selection track record)")
    plt.ylabel("Cumulative return")
    save_fig(figures / f"etf_proxy_cumret{suffix}.png")
    meta = {
        "label": "ETF_PROXY_NOT_STOCK_STRATEGY",
        "weights": w,
        "start": start,
        "end": end,
        "difference_from_proposed": (
            "Uses factor ETFs with their own methodologies; "
            "not the proposed sector-weight-matched stock-selection strategy."
        ),
    }
    (tables / f"etf_proxy_meta{suffix}.json").write_text(json.dumps(meta, indent=2))
    return proxy, df


def main(skip_download: bool = False, prices_only: bool = False):
    cfg = load_config()
    ensure_dirs(cfg)
    root = project_root()
    raw = root / cfg["paths"]["raw"]
    processed = root / cfg["paths"]["processed"]
    tables = root / cfg["paths"]["tables"]
    figures = root / cfg["paths"]["figures"]
    logs = root / cfg["paths"]["logs"]
    research_log = []

    def log(msg: str):
        research_log.append(msg)
        print(msg)

    log(f"Config loaded. Cutoff={cfg['project']['assignment_cutoff']}")

    if not skip_download:
        log("Building research ticker panel...")
        save_universe()
        if prices_only:
            log("Downloading prices/ETFs/RF only...")
            panel = pd.read_csv(raw / "research_ticker_panel.csv")
            from sis_hw2.data.download import download_prices
            tickers = panel["ticker"].astype(str).tolist()
            # Prefer S&P500-only for tractability if panel huge
            if "source" in panel.columns:
                sp = panel[panel["source"].astype(str).str.contains("sp500", case=False, na=False)]
                if len(sp) >= 400:
                    tickers = sp["ticker"].tolist()
                    panel[panel["ticker"].isin(tickers)].to_csv(raw / "research_ticker_panel.csv", index=False)
            px = download_prices(tickers, cfg["sample"]["price_start"], cfg["sample"]["price_end"])
            save_frame(px, raw / "prices_daily.pkl")
            etfs = [cfg["benchmarks"]["primary_etf"]] + list(cfg["benchmarks"]["factor_etfs"])
            etf = download_etf_benchmarks(etfs, cfg["sample"]["price_start"], cfg["sample"]["price_end"])
            save_frame(etf, raw / "etf_prices.pkl")
            rf = download_fred_rf(cfg["benchmarks"]["risk_free"], cfg["sample"]["price_start"])
            save_frame(rf, raw / "risk_free.pkl")
            panel[["ticker", "sector"]].assign(sector_source="wikipedia_current").to_csv(raw / "sector_map.csv", index=False)
        else:
            log("Full download (prices + fundamentals)...")
            # Restrict to S&P500 current for runtime
            panel = pd.read_csv(raw / "research_ticker_panel.csv")
            if "source" in panel.columns:
                sp = panel[panel["source"].astype(str).str.contains("sp500", case=False, na=False)]
                if len(sp) >= 400:
                    sp.to_csv(raw / "research_ticker_panel.csv", index=False)
                    log(f"Restricted panel to {len(sp)} S&P500-panel names for download tractability.")
            run_download()
    else:
        log("Skipping download (using existing raw data).")

    # Ensure ETF proxy can always run
    if (raw / "etf_prices.pkl").exists():
        etf = load_frame(raw / "etf_prices.pkl")
        if (raw / "risk_free.pkl").exists():
            rf = load_frame(raw / "risk_free.pkl")
        else:
            rf = download_fred_rf(cfg["benchmarks"]["risk_free"], cfg["sample"]["price_start"])
            save_frame(rf, raw / "risk_free.pkl")
        log("Running labelled ETF proxy study (long horizon, separate from stock strategy)...")
        proxy, proxy_df = run_etf_proxy_study(
            cfg, etf, rf, tables, figures,
            "2014-01-31", cfg["sample"]["price_end"], tag="long",
        )
        log("ETF proxy long-horizon summary:\n" + proxy_df.to_string())
        # also write default name expected by older docs
        proxy_df.to_csv(tables / "etf_proxy_summary.csv", float_format="%.8f")
        proxy_df.to_csv(tables / "etf_proxy_long_horizon_summary.csv", float_format="%.8f")

    # Process + stock backtest if fundamentals exist
    fund_path = raw / "fundamentals_raw.pkl"
    if not fund_path.exists():
        log("Fundamentals missing — stock-level backtest deferred. ETF proxy results remain valid as labelled proxy.")
        (logs / "research_log.txt").write_text("\n".join(research_log))
        return

    log("Processing raw data...")
    coverage = run_process()
    log("Coverage: " + json.dumps(coverage))

    prices = load_frame(processed / "prices.pkl")
    etf = load_frame(processed / "etf_prices.pkl")
    rf = load_frame(processed / "risk_free.pkl")
    fund_q = load_frame(processed / "fundamentals_q.pkl")
    shares = load_frame(processed / "shares.pkl")
    sectors = pd.read_csv(processed / "sectors.csv")

    start = cfg["sample"]["first_rebalance"]
    end = cfg["sample"]["design_end"]  # design period first
    holdout_start = cfg["sample"]["holdout_start"]
    holdout_end = cfg["sample"]["price_end"]
    spy = etf_daily_returns(etf, "SPY")
    rf_s = rf.set_index("date")["rf_daily"]

    common_kwargs = dict(
        prices=prices,
        fund_q=fund_q,
        sector_map=sectors,
        shares=shares,
        start=cfg["sample"]["price_start"],
        end=end,
        first_rebalance=start,
        n_universe=min(500, prices["ticker"].nunique()),
        selection_pct=cfg["signals"]["selection_pct"],
        composite_weights=cfg["signals"]["composite_weights"],
        lag_days=cfg["signals"]["fundamental_lag_days"],
        cost_bps_per_side=cfg["costs"]["baseline_bps_per_side"],
        mgmt_fee_bps_annual=0.0,
        min_price=cfg["universe"]["min_price"],
        min_adv=cfg["universe"]["min_adv_usd"],
    )

    log("Running VQM gross (0 trading cost)...")
    gross = run_backtest(name="VQM_gross", **{**common_kwargs, "cost_bps_per_side": 0.0})
    log("Running baseline VQM (after 5bps/side trading costs, before mgmt fee)...")
    baseline = run_backtest(name="VQM_after_costs", **common_kwargs)
    log("Running value/quality/momentum only...")
    value_only = run_backtest(name="value_only", single_factor="value", **common_kwargs)
    quality_only = run_backtest(name="quality_only", single_factor="quality", **common_kwargs)
    mom_only = run_backtest(name="momentum_only", single_factor="momentum", **common_kwargs)
    log("Running cap-weight eligible universe benchmark...")
    univ_cap = run_backtest(name="universe_cap", universe_cap_weight=True, **common_kwargs)
    log("Running net of illustrative mgmt fee...")
    net_fee = run_backtest(
        name="VQM_after_costs_and_fee",
        **{**common_kwargs, "mgmt_fee_bps_annual": cfg["costs"]["management_fee_bps_annual"]},
    )
    log("Running high cost scenario...")
    high_cost = run_backtest(
        name="VQM_high_cost",
        **{**common_kwargs, "cost_bps_per_side": cfg["costs"]["high_bps_per_side"]},
    )

    strategies = {
        "VQM_gross": gross,
        "VQM_after_costs": baseline,
        "VQM_after_costs_and_fee": net_fee,
        "VQM_high_cost": high_cost,
        "value_only": value_only,
        "quality_only": quality_only,
        "momentum_only": mom_only,
        "universe_cap": univ_cap,
    }

    # Align SPY on strategy dates only (no fillna inventing returns)
    spy_d = spy.reindex(baseline.returns.index)
    summaries = {}
    for k, res in strategies.items():
        summaries[k] = summarize(res.returns, spy_d, rf_s)
        summaries[k]["avg_turnover_one_way"] = float(res.turnover.mean()) if len(res.turnover) else np.nan
        summaries[k]["sample_start"] = str(res.returns.index.min().date()) if len(res.returns) else None
        summaries[k]["sample_end"] = str(res.returns.index.max().date()) if len(res.returns) else None
    summaries["SPY"] = summarize(spy_d.dropna(), None, rf_s)
    summaries["SPY"]["sample_start"] = str(spy_d.dropna().index.min().date()) if spy_d.notna().any() else None
    summaries["SPY"]["sample_end"] = str(spy_d.dropna().index.max().date()) if spy_d.notna().any() else None
    summary_df = format_summary_table(summaries)
    summary_df.to_csv(tables / "design_period_summary.csv", float_format="%.8f")
    # Readable percent table for humans
    pct_cols = ["cagr", "ann_vol", "max_drawdown", "tracking_error", "active_cagr", "total_return"]
    readable = summary_df.copy()
    for c in pct_cols:
        if c in readable.columns:
            readable[c] = (readable[c] * 100).map(lambda x: f"{x:.2f}%" if pd.notna(x) else "")
    readable.to_csv(tables / "design_period_summary_readable.csv")
    log("Design-period summary:\n" + summary_df.to_string())

    # Annual returns
    ann = {k: annual_returns(v.returns) for k, v in strategies.items()}
    ann["SPY"] = annual_returns(spy_d.dropna())
    ann_df = pd.DataFrame(ann)
    ann_df.to_csv(tables / "annual_returns.csv", float_format="%.8f")

    # Turnover
    turn = {k: float(v.turnover.mean()) if len(v.turnover) else np.nan for k, v in strategies.items()}
    pd.Series(turn, name="avg_monthly_turnover_one_way").to_csv(tables / "turnover.csv", float_format="%.8f")

    # Holdings log
    baseline.holdings_log.to_csv(tables / "rebalance_holdings_log.csv", index=False)
    baseline.returns.to_csv(tables / "VQM_baseline_daily_returns.csv", float_format="%.10f", header=["ret"])
    gross.returns.to_csv(tables / "VQM_gross_daily_returns.csv", float_format="%.10f", header=["ret"])

    # Charts
    plt.figure(figsize=(10, 5))
    for k in ["VQM_after_costs", "value_only", "quality_only", "momentum_only", "universe_cap"]:
        cumulative_returns(strategies[k].returns).plot(label=k)
    cumulative_returns(spy_d.fillna(0)).plot(label="SPY", linewidth=2, color="black")
    plt.legend()
    plt.title("Design period — CORRECTED accounting (Yahoo exploratory panel)")
    plt.ylabel("Cumulative return")
    save_fig(figures / "design_cumret.png")

    # Growth of $10,000
    plt.figure(figsize=(10, 5))
    ((1 + baseline.returns.fillna(0)).cumprod() * 10000).plot(label="VQM after costs")
    ((1 + spy_d.fillna(0)).cumprod() * 10000).plot(label="SPY")
    plt.legend()
    plt.title("Growth of $10,000 (design window; exploratory Yahoo panel)")
    plt.ylabel("Portfolio value ($)")
    save_fig(figures / "growth_of_10000.png")

    # Drawdown from NAV=1
    wealth = pd.concat([pd.Series([1.0]), (1 + baseline.returns.fillna(0)).cumprod()])
    dd = wealth / wealth.cummax() - 1
    plt.figure(figsize=(10, 3))
    dd.iloc[1:].plot(color="firebrick")
    plt.title("VQM after-costs drawdown (peak includes initial NAV=1)")
    plt.ylabel("Drawdown")
    save_fig(figures / "vqm_drawdown.png")

    # Robustness: selection pct, lags, weights, quarterly
    rob_rows = []
    for pct in cfg["robustness"]["selection_pcts"]:
        res = run_backtest(name=f"sel_{pct}", **{**common_kwargs, "selection_pct": pct})
        s = summarize(res.returns, spy_d, rf_s)
        s["variant"] = f"selection_pct={pct}"
        rob_rows.append(s)
    for lag in cfg["robustness"]["lag_days"]:
        res = run_backtest(name=f"lag_{lag}", **{**common_kwargs, "lag_days": lag})
        s = summarize(res.returns, spy_d, rf_s)
        s["variant"] = f"lag_days={lag}"
        rob_rows.append(s)
    for wts in cfg["robustness"]["signal_weights"]:
        res = run_backtest(name=f"w_{wts}", **{**common_kwargs, "composite_weights": wts})
        s = summarize(res.returns, spy_d, rf_s)
        s["variant"] = f"weights={wts}"
        rob_rows.append(s)
    res_q = run_backtest(name="quarterly", **{**common_kwargs, "rebalance_freq": "Q"})
    s = summarize(res_q.returns, spy_d, rf_s)
    s["variant"] = "rebalance=Q"
    rob_rows.append(s)
    for c in cfg["robustness"]["cost_bps"]:
        res = run_backtest(name=f"cost_{c}", **{**common_kwargs, "cost_bps_per_side": c})
        s = summarize(res.returns, spy_d, rf_s)
        s["variant"] = f"cost_bps_per_side={c}"
        rob_rows.append(s)
    rob_df = pd.DataFrame(rob_rows).set_index("variant")
    rob_df.to_csv(tables / "robustness_design.csv", float_format="%.8f")
    log("Robustness done.")

    # Cost sensitivity chart
    cost_rows = rob_df[rob_df.index.str.startswith("cost_bps")]
    if len(cost_rows):
        plt.figure(figsize=(8, 4))
        (cost_rows["cagr"] * 100).plot(kind="bar")
        plt.ylabel("CAGR (%)")
        plt.title("Cost sensitivity (design window)")
        save_fig(figures / "cost_sensitivity.png")

    # Previously examined historical evaluation period (NOT untouched OOS)
    log("Evaluating previously examined historical period (not untouched holdout)...")
    full_kwargs = {**common_kwargs, "end": holdout_end}
    full = run_backtest(name="VQM_full", **full_kwargs)
    hold = full.returns.loc[holdout_start:]
    spy_h = spy.reindex(hold.index)
    holdout_sum = {
        "VQM_prev_examined": summarize(hold, spy_h, rf_s),
        "SPY_same_dates": summarize(spy_h.dropna(), None, rf_s),
    }
    format_summary_table(holdout_sum).to_csv(tables / "holdout_summary.csv", float_format="%.8f")
    full.returns.to_csv(tables / "VQM_full_daily_returns.csv", float_format="%.10f", header=["ret"])

    plt.figure(figsize=(10, 5))
    cumulative_returns(full.returns).plot(label="VQM full")
    cumulative_returns(spy.reindex(full.returns.index).fillna(0)).plot(label="SPY")
    plt.axvline(pd.Timestamp(holdout_start), color="gray", linestyle="--", label="prev-examined period start")
    plt.legend()
    plt.title("Full sample (corrected); 2026 slice previously examined — not untouched OOS")
    save_fig(figures / "full_cumret_holdout.png")

    (logs / "research_log.txt").write_text("\n".join(research_log))
    meta = {
        "correction_branch": "hw2/accounting-correction",
        "design_end": end,
        "prev_examined_start": holdout_start,
        "n_universe_used": common_kwargs["n_universe"],
        "execution": "next_close",
        "accounting": "begin_weight_dot_return_then_drift",
        "data_label": "BIASED_EXPLORATORY_YAHOO_CURRENT_CONSTITUENT_PANEL",
        "superseded_numbers": [
            "Do not cite pre-correction ~43.5% stock CAGR, ~81.6% holdout CAGR, or ~14.7% ETF-proxy CAGR",
        ],
        "assumptions": [
            "Research panel = current S&P 500 constituents (survivorship/membership bias).",
            "Not historical S&P 500; not CRSP top-500.",
            "Yahoo fundamentals are restated; 60-day lag approximates availability only.",
            "Current GICS sectors applied historically.",
            "Signals at month-end close; trades at next session close.",
            "Portfolio return = beginning weights · asset returns; then drift.",
            "Costs = L1 traded weight * bps_per_side; NAV scaled (1+Rp)*(1-cost)*(1-fee)-1.",
            "FRED DGS3MO is a yield converted as y/100/252 — not Kenneth French realized RF.",
            "2026 evaluation period was previously inspected — not an untouched test set.",
        ],
    }
    (tables / "run_meta.json").write_text(json.dumps(meta, indent=2))
    log("Done.")


if __name__ == "__main__":
    skip = "--skip-download" in sys.argv
    prices_only = "--prices-only" in sys.argv
    try:
        main(skip_download=skip, prices_only=prices_only)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
