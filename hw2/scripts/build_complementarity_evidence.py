#!/usr/bin/env python3
"""Complementarity evidence: holdings overlap, characteristic exposures, active-return correlations."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sis_hw2.backtest.engine import run_backtest
from sis_hw2.signals.factors import build_signals_for_date
from sis_hw2.utils.config import load_config, project_root
from sis_hw2.utils.io import load_frame


def main():
    cfg = load_config()
    root = project_root()
    processed = root / cfg["paths"]["processed"]
    tables = Path(root / cfg["paths"]["tables"])
    figures = Path(root / cfg["paths"]["figures"])
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    prices = load_frame(processed / "prices.pkl")
    etf = load_frame(processed / "etf_prices.pkl")
    fund_q = load_frame(processed / "fundamentals_q.pkl")
    shares = load_frame(processed / "shares.pkl")
    sectors = pd.read_csv(processed / "sectors.csv")

    common = dict(
        prices=prices,
        fund_q=fund_q,
        sector_map=sectors,
        shares=shares,
        start=cfg["sample"]["price_start"],
        end=cfg["sample"]["design_end"],
        first_rebalance=cfg["sample"]["first_rebalance"],
        n_universe=min(500, int(prices["ticker"].nunique())),
        selection_pct=cfg["signals"]["selection_pct"],
        composite_weights=cfg["signals"]["composite_weights"],
        lag_days=cfg["signals"]["fundamental_lag_days"],
        min_price=cfg["universe"]["min_price"],
        min_adv=cfg["universe"]["min_adv_usd"],
        quality_mode="annual_labelled",
        execution="next_close",
        cost_bps_per_side=5.0,
        mgmt_fee_bps_annual=0.0,
    )

    specs = {
        "VQM": {},
        "Momentum": dict(single_factor="momentum"),
        "Value": dict(single_factor="value"),
        "Quality": dict(single_factor="quality"),
        "UniverseCap": dict(universe_cap_weight=True),
    }
    results = {}
    for name, kw in specs.items():
        print(f"Running {name}...", flush=True)
        results[name] = run_backtest(name=name, **{**common, **kw})
        # persist holdings for reuse
        results[name].holdings_log.to_csv(tables / f"holdings_{name}.csv", index=False)

    def holdings_map(res):
        h = res.holdings_log.copy()
        h["date"] = pd.to_datetime(h["date"])
        if "signal_date" in h.columns:
            h["signal_date"] = pd.to_datetime(h["signal_date"])
        out = {}
        for dt, g in h.groupby("date"):
            out[dt] = g.set_index("ticker")["weight"]
        return out

    maps = {k: holdings_map(v) for k, v in results.items() if len(v.holdings_log)}
    dates = sorted(set.intersection(*[set(m) for m in maps.values()]))

    def jaccard(a: set, b: set) -> float:
        if not a and not b:
            return np.nan
        return len(a & b) / max(len(a | b), 1)

    def weight_overlap(wa: pd.Series, wb: pd.Series) -> float:
        idx = wa.index.union(wb.index)
        return float(np.minimum(wa.reindex(idx).fillna(0), wb.reindex(idx).fillna(0)).sum())

    pairs = [
        ("VQM", "Momentum"),
        ("VQM", "Value"),
        ("VQM", "Quality"),
        ("Momentum", "Value"),
        ("Momentum", "Quality"),
        ("Value", "Quality"),
    ]
    overlap_rows = []
    for a, b in pairs:
        js, wo = [], []
        for dt in dates:
            sa, sb = set(maps[a][dt].index), set(maps[b][dt].index)
            js.append(jaccard(sa, sb))
            wo.append(weight_overlap(maps[a][dt], maps[b][dt]))
        overlap_rows.append(
            {
                "pair": f"{a}_vs_{b}",
                "avg_jaccard": float(np.nanmean(js)),
                "avg_weight_overlap": float(np.nanmean(wo)),
                "n_dates": len(dates),
            }
        )
    overlap_df = pd.DataFrame(overlap_rows)
    overlap_df.to_csv(tables / "holdings_overlap_summary.csv", index=False, float_format="%.6f")
    print(overlap_df.to_string(index=False), flush=True)

    detail = []
    for dt in dates:
        detail.append(
            {
                "date": dt,
                "jaccard_VQM_Mom": jaccard(set(maps["VQM"][dt].index), set(maps["Momentum"][dt].index)),
                "weight_overlap_VQM_Mom": weight_overlap(maps["VQM"][dt], maps["Momentum"][dt]),
                "n_VQM": len(maps["VQM"][dt]),
                "n_Mom": len(maps["Momentum"][dt]),
            }
        )
    pd.DataFrame(detail).to_csv(tables / "holdings_overlap_VQM_vs_Mom.csv", index=False, float_format="%.6f")

    # Cache signals by signal_date (from holdings_log)
    sig_cache: dict[pd.Timestamp, pd.DataFrame] = {}

    def get_signals(asof: pd.Timestamp) -> pd.DataFrame:
        asof = pd.Timestamp(asof).normalize()
        if asof not in sig_cache:
            print(f"  signals @ {asof.date()}", flush=True)
            sig_cache[asof] = build_signals_for_date(
                asof,
                prices,
                fund_q,
                sectors,
                shares,
                lag_days=cfg["signals"]["fundamental_lag_days"],
                min_price=cfg["universe"]["min_price"],
                min_adv=cfg["universe"]["min_adv_usd"],
                n_universe=min(500, int(prices["ticker"].nunique())),
                quality_mode="annual_labelled",
            )
        return sig_cache[asof]

    def portfolio_exposures(res, label):
        rows = []
        h = res.holdings_log.copy()
        h["date"] = pd.to_datetime(h["date"])
        if "signal_date" in h.columns:
            h["signal_date"] = pd.to_datetime(h["signal_date"])
        for dt, g in h.groupby("date"):
            if "signal_date" in g.columns and g["signal_date"].notna().any():
                asof = pd.Timestamp(g["signal_date"].iloc[0]).normalize()
            else:
                asof = (pd.Timestamp(dt).normalize() - pd.offsets.MonthEnd(0))
                if asof > pd.Timestamp(dt):
                    asof = pd.Timestamp(dt) - pd.offsets.MonthEnd(1)
            sig = get_signals(asof)
            w = g.set_index("ticker")["weight"]
            s = sig.reindex(w.index)

            def wavg(col):
                x = s[col].astype(float)
                m = x.notna() & w.notna()
                if m.sum() == 0:
                    return np.nan
                return float((w[m] * x[m]).sum() / w[m].sum())

            rows.append(
                {
                    "portfolio": label,
                    "date": dt,
                    "asof_signals": asof,
                    "wavg_rank_value": wavg("rank_value"),
                    "wavg_rank_quality": wavg("rank_quality"),
                    "wavg_rank_momentum": wavg("rank_momentum"),
                    "wavg_value_bm": wavg("value_bm"),
                    "wavg_quality_roe": wavg("quality_roe"),
                    "wavg_momentum": wavg("momentum"),
                    "n_holdings": int(len(w)),
                }
            )
        return pd.DataFrame(rows)

    exp_frames = []
    for label in ["VQM", "Momentum", "Value", "Quality", "UniverseCap"]:
        print(f"Exposures {label}...", flush=True)
        exp_frames.append(portfolio_exposures(results[label], label))
    exp = pd.concat(exp_frames, ignore_index=True)
    exp.to_csv(tables / "portfolio_signal_exposures.csv", index=False, float_format="%.6f")
    exp_avg = exp.groupby("portfolio")[
        [
            "wavg_rank_value",
            "wavg_rank_quality",
            "wavg_rank_momentum",
            "wavg_value_bm",
            "wavg_quality_roe",
            "wavg_momentum",
        ]
    ].mean()
    exp_avg.to_csv(tables / "portfolio_signal_exposures_avg.csv", float_format="%.6f")
    print(exp_avg, flush=True)

    spy = etf[etf["ticker"] == "SPY"].sort_values("date").set_index("date")["adj_close"]
    try:
        spy_r = spy.pct_change(fill_method=None).dropna()
    except TypeError:
        spy_r = spy.pct_change().dropna()

    rets = pd.DataFrame({k: v.returns for k, v in results.items()}).dropna(how="all")
    active = rets.sub(spy_r.reindex(rets.index), axis=0)
    sleeve_cols = ["VQM", "Momentum", "Value", "Quality"]
    corr_total = rets[sleeve_cols].corr()
    corr_active = active[sleeve_cols].corr()
    corr_total.to_csv(tables / "sleeve_return_corr.csv", float_format="%.6f")
    corr_active.to_csv(tables / "sleeve_active_return_corr.csv", float_format="%.6f")
    print("active corr\n", corr_active, flush=True)

    # Plots
    footnote = "Exploratory backtest: current constituents and restated fundamentals; survivorship and look-ahead risks."

    fig, ax = plt.subplots(figsize=(9, 4))
    d = pd.DataFrame(detail)
    ax.plot(d["date"], d["weight_overlap_VQM_Mom"], label="Weight overlap VQM∩Mom")
    ax.plot(d["date"], d["jaccard_VQM_Mom"], label="Jaccard (names)", alpha=0.85)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Overlap")
    ax.set_title("VQM vs momentum holdings overlap at rebalance")
    ax.legend(fontsize=8)
    ax.annotate(footnote, xy=(0, -0.22), xycoords="axes fraction", fontsize=7, color="dimgray")
    fig.tight_layout()
    fig.savefig(figures / "holdings_overlap_VQM_Mom.png", dpi=150, bbox_inches="tight")
    plt.close()

    fig, ax = plt.subplots(figsize=(8, 4))
    plot = exp_avg.loc[
        ["UniverseCap", "Value", "Quality", "Momentum", "VQM"],
        ["wavg_rank_value", "wavg_rank_quality", "wavg_rank_momentum"],
    ]
    plot.columns = ["Value rank", "Profitability rank", "Momentum rank"]
    plot.plot(kind="bar", ax=ax)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Portfolio-weighted avg sector percentile rank")
    ax.set_title("Characteristic exposures by sleeve (design-window average)")
    ax.legend(fontsize=8)
    ax.annotate(footnote, xy=(0, -0.28), xycoords="axes fraction", fontsize=7, color="dimgray")
    fig.tight_layout()
    fig.savefig(figures / "portfolio_characteristic_exposures.png", dpi=150, bbox_inches="tight")
    plt.close()

    fig, ax = plt.subplots(figsize=(5.5, 4))
    im = ax.imshow(corr_active.values, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(sleeve_cols)))
    ax.set_yticks(range(len(sleeve_cols)))
    ax.set_xticklabels(sleeve_cols)
    ax.set_yticklabels(sleeve_cols)
    for ii in range(len(sleeve_cols)):
        for jj in range(len(sleeve_cols)):
            ax.text(jj, ii, f"{corr_active.values[ii, jj]:.2f}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046)
    ax.set_title("Correlation of active returns (vs SPY)")
    ax.annotate(
        "Common equity residual may remain; not pure style independence.",
        xy=(0, -0.18),
        xycoords="axes fraction",
        fontsize=7,
        color="dimgray",
    )
    fig.tight_layout()
    fig.savefig(figures / "sleeve_active_corr.png", dpi=150, bbox_inches="tight")
    plt.close()

    if (figures / "AF_comparison_cumret.png").exists():
        shutil.copyfile(figures / "AF_comparison_cumret.png", figures / "design_cumret.png")

    meta = {
        "note": "Complementarity evidence for pitch — evaluates a pre-existing rationale",
        "avg_weight_overlap_VQM_Mom": float(
            overlap_df.loc[overlap_df["pair"] == "VQM_vs_Momentum", "avg_weight_overlap"].iloc[0]
        ),
        "avg_jaccard_VQM_Mom": float(
            overlap_df.loc[overlap_df["pair"] == "VQM_vs_Momentum", "avg_jaccard"].iloc[0]
        ),
        "active_corr_VQM_Mom": float(corr_active.loc["VQM", "Momentum"]),
        "active_corr_Value_Mom": float(corr_active.loc["Value", "Momentum"]),
        "active_corr_Quality_Mom": float(corr_active.loc["Quality", "Momentum"]),
        "active_corr_Value_Quality": float(corr_active.loc["Value", "Quality"]),
    }
    (tables / "complementarity_evidence.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
