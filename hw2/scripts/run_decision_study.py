#!/usr/bin/env python3
"""
Controlled A–F comparison and STRATEGY_DECISION artifacts.

Preserves prior outputs under outputs/archive_pre_decision/ then regenerates
corrected tables under outputs/tables/ and reports/STRATEGY_DECISION.md.

Does not optimize for attractive historical performance.
"""

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

from sis_hw2.utils.io import load_frame
from sis_hw2.utils.config import load_config, ensure_dirs, project_root
from sis_hw2.data.process import run_process
from sis_hw2.backtest.engine import run_backtest
from sis_hw2.metrics.performance import (
    summarize,
    format_summary_table,
    cumulative_returns,
    annual_returns,
    cagr,
    ann_vol,
    max_drawdown,
)


def save_fig(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def etf_daily_returns(etf: pd.DataFrame, ticker: str) -> pd.Series:
    g = etf[etf["ticker"] == ticker].sort_values("date").set_index("date")["adj_close"]
    try:
        return g.pct_change(fill_method=None).dropna().rename(ticker)
    except TypeError:
        return g.pct_change().dropna().rename(ticker)


def archive_prior_outputs(root: Path):
    tables = root / "outputs" / "tables"
    archive = root / "outputs" / "archive_pre_decision"
    if tables.exists() and any(tables.iterdir()):
        archive.mkdir(parents=True, exist_ok=True)
        stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        dest = archive / stamp
        shutil.copytree(tables, dest, dirs_exist_ok=True)
        print(f"Archived prior tables -> {dest}")


def freeze_baseline(cfg: dict, tables: Path) -> dict:
    freeze = {
        "label": "FROZEN_BASELINE_VQM",
        "frozen_at": str(pd.Timestamp.now()),
        "definition": {
            "long_only": True,
            "rebalance": "monthly",
            "sector_weights": "match_eligible_universe_cap_weights_at_rebalance",
            "within_sector": "equal_weight_selected",
            "selection": "top_20pct_within_sector_on_equal_weight_VQM_composite",
            "execution": "next_session_close",
            "value": "book_equity / contemporaneous_market_cap",
            "quality": "vendor_labelled_annual_NI / period_matched_avg_book (Yahoo exploratory)",
            "quality_mode": "annual_labelled",
            "quality_note": "Genuine 4Q TTM unavailable for Yahoo panel at scale; annual labelled separately",
            "momentum": "total_return between 252-session and 21-session lookback endpoints",
            "cost_model": "PROPORTIONAL_APPROXIMATION L1 * bps_per_side",
            "missing_returns": "halt_zero_flagged",
            "first_rebalance": cfg["sample"]["first_rebalance"],
            "design_end": cfg["sample"]["design_end"],
            "data_label": "BIASED_EXPLORATORY_YAHOO_CURRENT_CONSTITUENT_PANEL",
        },
        "cost_fee_layers": {
            "gross": "0 bps trading, 0 mgmt fee",
            "after_trading_cost": f"{cfg['costs']['baseline_bps_per_side']} bps/side proportional approx",
            "after_mgmt_fee": f"trading costs + {cfg['costs']['management_fee_bps_annual']} bps annual mgmt",
        },
    }
    (tables / "baseline_freeze.json").write_text(json.dumps(freeze, indent=2))
    return freeze


def concentration_report(holdings: pd.DataFrame, returns: pd.Series, prices: pd.DataFrame) -> dict:
    if holdings.empty or returns.empty:
        return {"note": "no holdings"}
    # Largest average weights
    avg_w = holdings.groupby("ticker")["weight"].mean().sort_values(ascending=False)
    top10 = avg_w.head(10)
    # Approximate contribution: weight * stock return over sample (rough)
    wide = prices.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    try:
        stock_rets = wide.pct_change(fill_method=None)
    except TypeError:
        stock_rets = wide.pct_change()
    stock_rets = stock_rets.reindex(returns.index)
    contrib = {}
    for t, w in top10.items():
        if t in stock_rets.columns:
            # time-varying weight approximation using mean weight
            contrib[t] = float((w * stock_rets[t].fillna(0)).sum())
    return {
        "top10_avg_weights": top10.to_dict(),
        "approx_top10_sum_weight": float(top10.sum()),
        "approx_cumulative_contrib_mean_weight": contrib,
    }


def adv_capacity_table(holdings: pd.DataFrame, signals_asof_path: Path | None, prices: pd.DataFrame, aum: float = 10_000_000.0) -> pd.DataFrame:
    """Position and rebalance trade size vs ADV using holdings log + price/volume."""
    if holdings.empty:
        return pd.DataFrame()
    rows = []
    prices = prices.copy()
    prices["dv"] = prices["close"].astype(float) * prices["volume"].astype(float)
    for dt, g in holdings.groupby("date"):
        # ADV approx: mean dollar volume over prior 20 sessions ending signal day
        for _, row in g.iterrows():
            t = row["ticker"]
            w = float(row["weight"])
            hist = prices[(prices["ticker"] == t) & (prices["date"] <= dt)].sort_values("date").tail(20)
            adv = float(hist["dv"].mean()) if len(hist) >= 20 else np.nan
            pos = w * aum
            rows.append(
                {
                    "date": dt,
                    "ticker": t,
                    "weight": w,
                    "position_usd": pos,
                    "adv_20d": adv,
                    "position_pct_adv": pos / adv if adv and adv > 0 else np.nan,
                }
            )
    df = pd.DataFrame(rows)
    return df


def vol_match_diagnostic(strat: pd.Series, bench: pd.Series) -> dict:
    """Ex-post full-sample vol scaling — diagnostic only, not executable."""
    aligned = pd.concat([strat, bench], axis=1, join="inner").dropna()
    if aligned.empty:
        return {}
    s, b = aligned.iloc[:, 0], aligned.iloc[:, 1]
    vs, vb = ann_vol(s), ann_vol(b)
    if not vs or np.isnan(vs) or vs == 0:
        return {}
    scale = vb / vs
    scaled = s * scale
    return {
        "label": "EX_POST_VOLATILITY_MATCHED_DIAGNOSTIC_NOT_EXECUTABLE",
        "scale_factor": float(scale),
        "strat_vol": float(vs),
        "bench_vol": float(vb),
        "scaled_cagr": cagr(scaled),
        "bench_cagr": cagr(b),
        "scaled_max_dd": max_drawdown(scaled),
        "bench_max_dd": max_drawdown(b),
    }


def write_strategy_decision(
    path: Path,
    summary: pd.DataFrame,
    freeze: dict,
    corrections: list[str],
    evidence: dict,
):
    # Build comparison markdown table from summary
    cols = [
        c
        for c in [
            "cagr",
            "ann_vol",
            "sharpe",
            "max_drawdown",
            "total_return",
            "beta",
            "tracking_error",
            "avg_turnover_one_way",
            "cost_fee_layer",
        ]
        if c in summary.columns
    ]
    show = summary[cols].copy()
    for c in ["cagr", "ann_vol", "max_drawdown", "total_return", "tracking_error", "avg_turnover_one_way"]:
        if c in show.columns:
            show[c] = show[c].map(lambda x: f"{100*x:.2f}%" if pd.notna(x) else "")
    for c in ["sharpe", "beta"]:
        if c in show.columns:
            show[c] = show[c].map(lambda x: f"{x:.2f}" if pd.notna(x) else "")

    verdict = evidence["verdict"]
    para = evidence["verdict_paragraph"]

    md = f"""# Strategy decision — VQM long-only

**Evaluation window (design):** {evidence.get('design_start')} → {evidence.get('design_end')}  
**Data label:** BIASED exploratory Yahoo / current-constituent panel (not point-in-time; survivorship/membership bias remain).  
**2026 slice:** previously examined historical evaluation period — **not** untouched validation.

## One-paragraph verdict

{para}

## Decision code

**{verdict}**

## Concise comparison (design window)

Cost/fee layers are explicit in the `cost_fee_layer` column. Trading costs use a **proportional L1 approximation**, not exact cash-lot accounting.

| Strategy | {' | '.join(cols)} |
|---|{'|'.join(['---']*len(cols))}|
"""
    for idx, row in show.iterrows():
        md += "| " + str(idx) + " | " + " | ".join(str(row[c]) for c in cols) + " |\n"

    md += f"""
## What improved after corrections

{chr(10).join('- ' + c for c in corrections)}

## What remains uncertain

- Yahoo restated fundamentals and a fixed lag are **not** as-filed point-in-time.
- Current S&P constituents applied historically → survivorship / membership bias.
- Current sector labels applied historically.
- Short fundamental window (first rebalance {freeze['definition']['first_rebalance']}).
- Quality uses **vendor-labelled annual** income on Yahoo (genuine 4Q TTM coverage too thin for a frozen baseline).
- Cost model remains a proportional approximation.
- 2026 results were already inspected in prior work.

## What the evidence says about combining value + quality + momentum

{evidence['factor_combo']}

## Paid management proposition ($10mm illustrative)

{evidence['fee_claim']}

## Operational feasibility vs firm economics

{evidence['capacity']}

## Continue / simplify / reject

**{verdict}** — {evidence['decision_detail']}

## Minimum next research step that could change the decision

{evidence['next_step']}

## Baseline freeze (do not silently change)

```json
{json.dumps(freeze['definition'], indent=2)}
```
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md)


def main():
    cfg = load_config()
    ensure_dirs(cfg)
    root = project_root()
    tables = root / cfg["paths"]["tables"]
    figures = root / cfg["paths"]["figures"]
    reports = root / cfg["paths"]["reports"]
    processed = root / cfg["paths"]["processed"]
    logs = root / cfg["paths"]["logs"]

    archive_prior_outputs(root)

    print("Reprocessing with corrected shares/fundamentals policies...")
    coverage = run_process()
    (tables / "coverage_after_correction.json").write_text(json.dumps(coverage, indent=2))

    freeze = freeze_baseline(cfg, tables)

    prices = load_frame(processed / "prices.pkl")
    etf = load_frame(processed / "etf_prices.pkl")
    rf = load_frame(processed / "risk_free.pkl")
    fund_q = load_frame(processed / "fundamentals_q.pkl")
    shares = load_frame(processed / "shares.pkl")
    sectors = pd.read_csv(processed / "sectors.csv")

    start = cfg["sample"]["first_rebalance"]
    end = cfg["sample"]["design_end"]
    holdout_start = cfg["sample"]["holdout_start"]
    holdout_end = cfg["sample"]["price_end"]
    spy = etf_daily_returns(etf, "SPY")
    rf_s = rf.set_index("date")["rf_daily"]

    common = dict(
        prices=prices,
        fund_q=fund_q,
        sector_map=sectors,
        shares=shares,
        start=cfg["sample"]["price_start"],
        end=end,
        first_rebalance=start,
        n_universe=min(500, int(prices["ticker"].nunique())),
        selection_pct=cfg["signals"]["selection_pct"],
        composite_weights=cfg["signals"]["composite_weights"],
        lag_days=cfg["signals"]["fundamental_lag_days"],
        min_price=cfg["universe"]["min_price"],
        min_adv=cfg["universe"]["min_adv_usd"],
        quality_mode="annual_labelled",
        execution="next_close",
    )

    # A–F under identical universe/execution; three cost layers for selected strategies
    specs = [
        ("A_universe_cap", dict(universe_cap_weight=True, cost_bps_per_side=5.0, mgmt_fee_bps_annual=0.0)),
        ("B_universe_sector_equal", dict(universe_sector_equal=True, cost_bps_per_side=5.0, mgmt_fee_bps_annual=0.0)),
        ("C_momentum_only", dict(single_factor="momentum", cost_bps_per_side=5.0, mgmt_fee_bps_annual=0.0)),
        ("D_value_only", dict(single_factor="value", cost_bps_per_side=5.0, mgmt_fee_bps_annual=0.0)),
        ("E_quality_only", dict(single_factor="quality", cost_bps_per_side=5.0, mgmt_fee_bps_annual=0.0)),
        ("F_VQM_equal", dict(cost_bps_per_side=5.0, mgmt_fee_bps_annual=0.0)),
        ("F_VQM_gross", dict(cost_bps_per_side=0.0, mgmt_fee_bps_annual=0.0)),
        ("F_VQM_after_fee", dict(cost_bps_per_side=5.0, mgmt_fee_bps_annual=cfg["costs"]["management_fee_bps_annual"])),
        ("C_mom_gross", dict(single_factor="momentum", cost_bps_per_side=0.0, mgmt_fee_bps_annual=0.0)),
        ("C_mom_after_fee", dict(single_factor="momentum", cost_bps_per_side=5.0, mgmt_fee_bps_annual=cfg["costs"]["management_fee_bps_annual"])),
        ("A_univ_gross", dict(universe_cap_weight=True, cost_bps_per_side=0.0, mgmt_fee_bps_annual=0.0)),
        ("SPY_buyhold_ref", None),  # handled separately
    ]

    results = {}
    for name, kwargs in specs:
        if kwargs is None:
            continue
        print(f"Running {name}...")
        results[name] = run_backtest(name=name, **{**common, **kwargs})

    # Align on F_VQM_equal dates
    anchor = results["F_VQM_equal"].returns.index
    spy_d = spy.reindex(anchor)

    layer_map = {
        "A_universe_cap": "after_trading_cost_5bps",
        "B_universe_sector_equal": "after_trading_cost_5bps",
        "C_momentum_only": "after_trading_cost_5bps",
        "D_value_only": "after_trading_cost_5bps",
        "E_quality_only": "after_trading_cost_5bps",
        "F_VQM_equal": "after_trading_cost_5bps",
        "F_VQM_gross": "gross_0bps",
        "F_VQM_after_fee": "after_trading_cost_and_75bps_mgmt",
        "C_mom_gross": "gross_0bps",
        "C_mom_after_fee": "after_trading_cost_and_75bps_mgmt",
        "A_univ_gross": "gross_0bps",
        "SPY": "ETF_ER_embedded_no_extra_mgmt",
    }

    summaries = {}
    for k, res in results.items():
        r = res.returns.reindex(anchor).dropna()
        summaries[k] = summarize(r, spy_d, rf_s)
        summaries[k]["avg_turnover_one_way"] = float(res.turnover.mean()) if len(res.turnover) else np.nan
        summaries[k]["cost_fee_layer"] = layer_map.get(k, "")
        summaries[k]["sample_start"] = str(r.index.min().date()) if len(r) else None
        summaries[k]["sample_end"] = str(r.index.max().date()) if len(r) else None
        # treatment mix
        td = res.meta.get("turnover_detail")
        if isinstance(td, pd.DataFrame) and len(td):
            summaries[k]["avg_n_holdings"] = float(td["n_holdings"].mean())
            summaries[k]["avg_quality_annual_weight"] = float(td.get("quality_annual_weight", pd.Series([np.nan])).mean())
            summaries[k]["avg_quality_ttm_weight"] = float(td.get("quality_ttm_weight", pd.Series([np.nan])).mean())

    summaries["SPY"] = summarize(spy_d.dropna(), None, rf_s)
    summaries["SPY"]["cost_fee_layer"] = layer_map["SPY"]
    summaries["SPY"]["sample_start"] = str(spy_d.dropna().index.min().date()) if spy_d.notna().any() else None
    summaries["SPY"]["sample_end"] = str(spy_d.dropna().index.max().date()) if spy_d.notna().any() else None

    summary_df = format_summary_table(summaries)
    summary_df.to_csv(tables / "AF_comparison_summary.csv", float_format="%.8f")
    summary_df.to_csv(tables / "design_period_summary.csv", float_format="%.8f")

    readable = summary_df.copy()
    for c in ["cagr", "ann_vol", "max_drawdown", "tracking_error", "active_cagr", "total_return", "avg_turnover_one_way"]:
        if c in readable.columns:
            readable[c] = (readable[c] * 100).map(lambda x: f"{x:.2f}%" if pd.notna(x) else "")
    readable.to_csv(tables / "design_period_summary_readable.csv")
    readable.to_csv(tables / "AF_comparison_readable.csv")

    # Annual
    ann = {k: annual_returns(v.returns.reindex(anchor).dropna()) for k, v in results.items()}
    ann["SPY"] = annual_returns(spy_d.dropna())
    pd.DataFrame(ann).to_csv(tables / "annual_returns.csv", float_format="%.8f")

    # Holdings / treatment
    vqm = results["F_VQM_equal"]
    vqm.holdings_log.to_csv(tables / "rebalance_holdings_log.csv", index=False)
    td = vqm.meta.get("turnover_detail")
    if isinstance(td, pd.DataFrame):
        td.to_csv(tables / "rebalance_treatment_weights.csv", index=False)

    vqm.returns.to_csv(tables / "VQM_baseline_daily_returns.csv", float_format="%.10f", header=["ret"])
    results["F_VQM_gross"].returns.to_csv(tables / "VQM_gross_daily_returns.csv", float_format="%.10f", header=["ret"])

    # Concentration
    conc = concentration_report(vqm.holdings_log, vqm.returns, prices)
    (tables / "concentration.json").write_text(json.dumps(conc, indent=2, default=str))

    # ADV capacity
    print("Computing ADV / position sizing vs $10mm...")
    adv_df = adv_capacity_table(vqm.holdings_log, None, prices, aum=10_000_000.0)
    if len(adv_df):
        adv_df.to_csv(tables / "adv_position_sizing_10mm.csv", index=False, float_format="%.6f")
        capacity_stats = {
            "median_position_pct_adv": float(adv_df["position_pct_adv"].median()),
            "p95_position_pct_adv": float(adv_df["position_pct_adv"].quantile(0.95)),
            "max_position_pct_adv": float(adv_df["position_pct_adv"].max()),
            "n_positions_gt_1pct_adv": int((adv_df["position_pct_adv"] > 0.01).sum()),
            "n_positions_gt_5pct_adv": int((adv_df["position_pct_adv"] > 0.05).sum()),
        }
    else:
        capacity_stats = {"note": "empty"}
    (tables / "adv_capacity_stats.json").write_text(json.dumps(capacity_stats, indent=2))

    # Vol-match diagnostic
    vol_diag = vol_match_diagnostic(vqm.returns, spy_d)
    (tables / "vol_match_diagnostic.json").write_text(json.dumps(vol_diag, indent=2))

    # Charts
    plt.figure(figsize=(10, 5))
    for k in ["A_universe_cap", "B_universe_sector_equal", "C_momentum_only", "D_value_only", "E_quality_only", "F_VQM_equal"]:
        cumulative_returns(results[k].returns).plot(label=k)
    cumulative_returns(spy_d.fillna(0)).plot(label="SPY", color="black", linewidth=2)
    plt.legend(fontsize=8)
    plt.title("A–F comparison (after 5bps/side approx costs; Yahoo exploratory)")
    plt.ylabel("Cumulative return")
    save_fig(figures / "AF_comparison_cumret.png")
    # same figure for design_cumret alias (save_fig closes the figure)
    import shutil
    shutil.copyfile(figures / "AF_comparison_cumret.png", figures / "design_cumret.png")

    plt.figure(figsize=(10, 5))
    ((1 + vqm.returns.fillna(0)).cumprod() * 10000).plot(label="F VQM after costs")
    ((1 + results["C_momentum_only"].returns.fillna(0)).cumprod() * 10000).plot(label="C momentum after costs")
    ((1 + spy_d.fillna(0)).cumprod() * 10000).plot(label="SPY")
    plt.legend()
    plt.title("Growth of $10,000 — VQM vs momentum vs SPY (design; exploratory)")
    save_fig(figures / "growth_of_10000.png")

    wealth = pd.concat([pd.Series([1.0]), (1 + vqm.returns.fillna(0)).cumprod()])
    dd = wealth / wealth.cummax() - 1
    plt.figure(figsize=(10, 3))
    dd.iloc[1:].plot(color="firebrick")
    plt.title("VQM after-costs drawdown")
    save_fig(figures / "vqm_drawdown.png")

    # Previously examined 2026
    print("Previously examined 2026 slice...")
    full = run_backtest(
        name="VQM_full",
        **{**common, "end": holdout_end, "cost_bps_per_side": 5.0, "mgmt_fee_bps_annual": 0.0},
    )
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
    plt.axvline(pd.Timestamp(holdout_start), color="gray", linestyle="--", label="prev-examined start")
    plt.legend()
    plt.title("Full sample; 2026 previously examined — not untouched OOS")
    save_fig(figures / "full_cumret_holdout.png")

    # --- Economic decision (honest, not threshold-based) ---
    def g(name, key):
        return float(summary_df.loc[name, key]) if name in summary_df.index and pd.notna(summary_df.loc[name, key]) else np.nan

    vqm_cagr = g("F_VQM_equal", "cagr")
    mom_cagr = g("C_momentum_only", "cagr")
    univ_cagr = g("A_universe_cap", "cagr")
    spy_cagr = g("SPY", "cagr")
    vqm_fee = g("F_VQM_after_fee", "cagr")
    mom_fee = g("C_mom_after_fee", "cagr")
    vqm_sharpe = g("F_VQM_equal", "sharpe")
    mom_sharpe = g("C_momentum_only", "sharpe")
    vqm_to = g("F_VQM_equal", "avg_turnover_one_way")
    mom_to = g("C_momentum_only", "avg_turnover_one_way")
    vqm_dd = g("F_VQM_equal", "max_drawdown")
    mom_dd = g("C_momentum_only", "max_drawdown")

    # Annual dominance check
    ann_v = annual_returns(vqm.returns)
    ann_m = annual_returns(results["C_momentum_only"].returns)
    ann_spread = (ann_v - ann_m).dropna()
    dominant_year = None
    if len(ann_spread):
        dominant_year = int(ann_spread.abs().idxmax())
        year_share = float(ann_spread.loc[dominant_year] / ann_spread.sum()) if ann_spread.sum() != 0 else np.nan

    combo_helps = (
        pd.notna(vqm_cagr)
        and pd.notna(mom_cagr)
        and (vqm_cagr > mom_cagr + 0.005 or (vqm_sharpe > mom_sharpe + 0.05 and vqm_dd > mom_dd - 0.02))
    )
    # "Meaningful" after fee vs simpler alternatives
    beats_univ_after_fee = pd.notna(vqm_fee) and pd.notna(univ_cagr) and vqm_fee > univ_cagr
    beats_mom_after_fee = pd.notna(vqm_fee) and pd.notna(mom_fee) and vqm_fee > mom_fee
    beats_spy_after_fee = pd.notna(vqm_fee) and pd.notna(spy_cagr) and vqm_fee > spy_cagr

    data_too_weak = coverage.get("n_shares_usable_non_constant", 0) < 100 or coverage.get("n_fund_tickers", 0) < 200

    if data_too_weak and not (beats_mom_after_fee and combo_helps):
        verdict = "SIMPLIFY"
    elif beats_mom_after_fee and combo_helps and beats_univ_after_fee:
        # Still Yahoo-biased — CONTINUE RESEARCH not claim success
        verdict = "CONTINUE RESEARCH"
    elif not beats_mom_after_fee and not beats_univ_after_fee:
        verdict = "REJECT THE CURRENT INVESTMENT CLAIM"
    else:
        verdict = "SIMPLIFY"

    factor_combo = (
        f"After corrected accounting on the Yahoo exploratory panel, VQM after-cost CAGR={vqm_cagr:.2%} "
        f"vs momentum-only={mom_cagr:.2%}, universe-cap={univ_cagr:.2%}, SPY={spy_cagr:.2%}. "
        f"Sharpes: VQM={vqm_sharpe:.2f}, momentum={mom_sharpe:.2f}. "
        f"Avg one-way turnover: VQM={vqm_to:.2%}, momentum={mom_to:.2%}. "
    )
    if dominant_year is not None:
        factor_combo += (
            f"Largest calendar-year VQM−momentum spread is in {dominant_year} "
            f"(spread={float(ann_spread.loc[dominant_year]):.2%}); treat single-year dominance as a risk to the claim. "
        )
    if not combo_helps:
        factor_combo += (
            "On this sample, adding value and quality does **not** clearly improve the portfolio enough "
            "to justify the extra fundamental data and implementation complexity versus momentum-only "
            "or the eligible-universe benchmarks."
        )
    else:
        factor_combo += (
            "Point estimates favor the composite on this biased sample, but the edge is not clean enough "
            "to treat as a durable fee-justifying result without stronger point-in-time data."
        )

    if verdict == "REJECT THE CURRENT INVESTMENT CLAIM":
        fee_claim = (
            f"After 5bps/side approx costs and 75bps illustrative management fee, VQM CAGR={vqm_fee:.2%}. "
            "Results do not support charging for the proposed stock strategy versus simpler comparators "
            "once costs, risk, and Yahoo data limitations are considered."
        )
        decision_detail = (
            "Do not pitch VQM as a fee-earning stock-selection product on this evidence. "
            "For the assignment, use an honest illustrative framing with full bias disclosure, "
            "or switch the investable narrative to a labelled ETF allocation (different product)."
        )
        next_step = (
            "Minimum dataset to reopen the stock claim: licensed Sharadar (or equivalent) with "
            "(1) historical prices including delistings, (2) as-reported fundamentals with availability dates, "
            "(3) historical shares/market-cap inputs, (4) historical universe membership — then rebuild PIT "
            "and re-run this same A–F table. Subscription alone does not make the pipeline point-in-time."
        )
        para = (
            f"**REJECT THE CURRENT INVESTMENT CLAIM.** Corrected Yahoo-panel results do not support "
            f"charging a management fee for long-only VQM: after costs/fees the strategy does not "
            f"convincingly beat momentum-only and/or the eligible-universe benchmarks, and the dataset "
            f"cannot support a point-in-time stock claim. Prefer a simplified assignment framing "
            f"(disclosed exploratory study or labelled VLUE/QUAL/MTUM ETF sleeve) rather than a paid "
            f"stock-selection proposition."
        )
    elif verdict == "CONTINUE RESEARCH":
        fee_claim = (
            f"After-fee VQM CAGR={vqm_fee:.2%} exceeds some simpler benchmarks on this sample, "
            "but Yahoo bias means this is **not** a capacity or fee proof. Continue only with better data."
        )
        decision_detail = (
            "Economic benefit appears in corrected point estimates, but stronger PIT data or prospective "
            "evidence is required before any paid claim."
        )
        next_step = (
            "Obtain Sharadar (or peer) historical prices + as-reported fundamentals + membership; "
            "rebuild availability-dated pipeline; re-run frozen A–F comparison unchanged."
        )
        para = (
            f"**CONTINUE RESEARCH.** Corrected calculations show a possible economic benefit for VQM "
            f"versus simpler sleeves on this exploratory panel, but survivorship/restatement bias remain "
            f"binding. Do not claim durable alpha or capacity; escalate data quality before any fee pitch."
        )
    else:  # SIMPLIFY
        fee_claim = (
            f"After-fee VQM CAGR={vqm_fee:.2%} vs momentum-after-fee={mom_fee:.2%}, "
            f"universe-cap (after cost)={univ_cagr:.2%}, SPY={spy_cagr:.2%}. "
            "The combination does not clearly earn a stock-level management fee; simplify the product "
            "definition for the assignment."
        )
        decision_detail = (
            "Evidence supports simplifying toward (a) momentum-only within the same rules, or "
            "(b) the eligible-universe sector-equal/cap benchmarks as the honest baseline, or "
            "(c) a separately labelled monthly VLUE/QUAL/MTUM ETF allocation for the pitch — "
            "not as a substitute track record for the stock strategy. "
            "Do not claim the in-sample winner will keep winning."
        )
        next_step = (
            "If keeping stocks: licensed historical membership + as-reported fundamentals with "
            "availability dates. If assignment-only: freeze a VLUE/QUAL/MTUM equal-weight monthly "
            "rebalance ETF sleeve with after-inception histories, one-sided costs, and no double-counting of ER."
        )
        para = (
            f"**SIMPLIFY.** After correctness fixes, combining value and quality with momentum does not "
            f"add enough (on this biased Yahoo panel) to justify the extra data and complexity versus "
            f"simpler comparators. Drop the paid stock-selection claim; present an illustrative study "
            f"with full disclosure, or redefine the assignment around a labelled factor-ETF allocation."
        )

    capacity_txt = (
        f"At illustrative $10mm AUM, median position/ADV={capacity_stats.get('median_position_pct_adv')}, "
        f"p95={capacity_stats.get('p95_position_pct_adv')}, max={capacity_stats.get('max_position_pct_adv')}. "
        "Operational feasibility of small AUM is separate from whether a standalone firm can charge for alpha "
        "that has not been established on credible PIT data."
    )

    corrections = [
        "Missing held-stock returns are halt-zero-flagged (weight reported), not silent price fills.",
        "Daily returns use explicit pct_change(fill_method=None).",
        "Balance-sheet shares enter at period_end + lag (availability), not period_end.",
        "constant_latest share counts are audit-only and excluded from market-cap eligibility.",
        "Annual income uses vendor-labelled annual only (no gap→annual misclassification).",
        "Average book equity is matched to income-window period ends, not row positions.",
        "ADV requires all 20 session observations.",
        "Strategy/ETF returns recorded only from first execution close (no pre-trade SPY-like accrual).",
        "Cost accounting labelled as proportional approximation in meta and reports.",
    ]

    evidence = {
        "verdict": verdict,
        "verdict_paragraph": para,
        "factor_combo": factor_combo,
        "fee_claim": fee_claim,
        "decision_detail": decision_detail,
        "next_step": next_step,
        "capacity": capacity_txt,
        "design_start": summaries.get("F_VQM_equal", {}).get("sample_start"),
        "design_end": summaries.get("F_VQM_equal", {}).get("sample_end"),
        "metrics": {
            "vqm_cagr": vqm_cagr,
            "mom_cagr": mom_cagr,
            "univ_cagr": univ_cagr,
            "spy_cagr": spy_cagr,
            "vqm_fee_cagr": vqm_fee,
            "mom_fee_cagr": mom_fee,
        },
    }
    (tables / "decision_evidence.json").write_text(json.dumps(evidence, indent=2, default=str))

    write_strategy_decision(reports / "STRATEGY_DECISION.md", summary_df, freeze, corrections, evidence)

    meta = {
        "pipeline": "run_decision_study.py",
        "baseline_freeze": freeze["definition"],
        "coverage": coverage,
        "verdict": verdict,
        "data_label": "BIASED_EXPLORATORY_YAHOO_CURRENT_CONSTITUENT_PANEL",
        "cost_model": "PROPORTIONAL_APPROXIMATION",
        "prev_examined_start": holdout_start,
        "superseded_numbers": [
            "Do not cite pre-correction ~43.5% / ~81.6% / ~14.7% figures",
        ],
        "sharadar": "Not purchased; set SHARADAR_API_KEY only if already licensed — subscription ≠ PIT pipeline",
        "reproduction": {
            "fresh_download": "python scripts/run_research.py",
            "cached_reproduction": "python scripts/run_decision_study.py  # uses data/raw cache",
            "tests": "pytest tests/test_accounting.py -q",
        },
    }
    (tables / "run_meta.json").write_text(json.dumps(meta, indent=2))
    (logs / "decision_study_log.txt").write_text(
        f"verdict={verdict}\n" + summary_df.to_string() + "\n"
    )
    print("VERDICT:", verdict)
    print(summary_df[["cagr", "sharpe", "max_drawdown", "avg_turnover_one_way", "cost_fee_layer"]].to_string())
    print("Wrote", reports / "STRATEGY_DECISION.md")


if __name__ == "__main__":
    main()
