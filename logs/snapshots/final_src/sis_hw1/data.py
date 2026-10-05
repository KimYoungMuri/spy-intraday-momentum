"""Data ingestion and audit for the instructor SPY workbook.

Observations in Section 4A of the assignment prompt (ChatGPT-supplied audit)
are re-verified here and recorded as such in the anomaly report.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HALF_DAYS = {date(2025, 7, 3), date(2025, 11, 28)}
FULL_BAR_LABELS = [
    time(9, 30), time(10, 0), time(10, 30), time(11, 0), time(11, 30),
    time(12, 0), time(12, 30), time(13, 0), time(13, 30), time(14, 0),
    time(14, 30), time(15, 0), time(15, 30),
]
HALF_BAR_LABELS = [
    time(9, 30), time(10, 0), time(10, 30), time(11, 0), time(11, 30),
    time(12, 0), time(12, 30),
]


@dataclass
class Anomaly:
    date: str
    time: str | None
    issue: str
    evidence: str
    resolution: str
    impact: str
    severity: str = "info"  # info | warning | critical


@dataclass
class AuditReport:
    anomalies: list[Anomaly] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    chatgpt_supplied_checks: dict[str, Any] = field(default_factory=dict)

    def add(self, **kwargs: Any) -> None:
        self.anomalies.append(Anomaly(**kwargs))

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "chatgpt_supplied_checks": self.chatgpt_supplied_checks,
            "anomalies": [asdict(a) for a in self.anomalies],
        }


def _excel_to_dt(series: pd.Series) -> pd.Series:
    """Convert Excel serials or datetime objects to timezone-naive America/New_York wall times."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series)
    # Excel serial day count since 1899-12-30
    return pd.to_datetime(series, unit="D", origin="1899-12-30")


def load_raw_sheets(workbook: Path) -> dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(workbook)
    out: dict[str, pd.DataFrame] = {}
    for name in xl.sheet_names:
        df = pd.read_excel(workbook, sheet_name=name)
        # Drop fully empty columns
        df = df.dropna(axis=1, how="all")
        out[name] = df
    return out


def _normalize_intraday(df: pd.DataFrame, volume_col: str) -> pd.DataFrame:
    cols = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=cols)
    # Find columns flexibly
    ts_col = [c for c in df.columns if "time" in c.lower() or "stamp" in c.lower()][0]
    px_col = [c for c in df.columns if "last" in c.lower() or "price" in c.lower()][0]
    vol_candidates = [c for c in df.columns if "volume" in c.lower()]
    if volume_col and volume_col in df.columns:
        vcol = volume_col
    else:
        vcol = vol_candidates[0]

    out = pd.DataFrame({
        "timestamp_raw": _excel_to_dt(df[ts_col]),
        "last_price": pd.to_numeric(df[px_col], errors="coerce"),
        "volume": pd.to_numeric(df[vcol], errors="coerce"),
    })
    out = out.dropna(subset=["timestamp_raw", "last_price"]).copy()
    out["session_date"] = out["timestamp_raw"].dt.date
    out["clock_label"] = out["timestamp_raw"].dt.time
    out = out.sort_values("timestamp_raw").reset_index(drop=True)
    out["source_row"] = out.index
    return out


def _normalize_daily(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=cols)
    ts_col = [c for c in df.columns if "time" in c.lower() or "stamp" in c.lower()][0]
    px_col = [c for c in df.columns if "last" in c.lower() or "price" in c.lower()][0]
    vol_col = [c for c in df.columns if "volume" in c.lower()][0]
    out = pd.DataFrame({
        "session_date": _excel_to_dt(df[ts_col]).dt.date,
        "close": pd.to_numeric(df[px_col], errors="coerce"),
        "volume": pd.to_numeric(df[vol_col], errors="coerce"),
    })
    out = out.dropna(subset=["session_date", "close"]).sort_values("session_date").reset_index(drop=True)
    return out


def _availability_time(clock: time, is_half: bool) -> time | None:
    """Map bar-start label to availability time under main timing assumption."""
    if is_half:
        # Regular half-day bars: 09:30..12:30 available at 10:00..13:00
        if clock in HALF_BAR_LABELS:
            dt = datetime.combine(date(2000, 1, 1), clock) + timedelta(minutes=30)
            return dt.time()
        return None  # stale post-close labels not tradable
    # Full day: 09:30..15:30 available at 10:00..16:00
    if clock in FULL_BAR_LABELS:
        dt = datetime.combine(date(2000, 1, 1), clock) + timedelta(minutes=30)
        return dt.time()
    return None


def audit_and_clean(
    workbook: Path,
    processed_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, AuditReport]:
    """Load workbook, audit, produce cleaned tradable bars and daily series."""
    report = AuditReport()
    sheets = load_raw_sheets(workbook)

    clean_raw = sheets["AV.Clean"]
    bbrg_intra = sheets["BBRG.Intraday"]
    bbrg_daily = sheets["BBRG.Daily"]

    # Volume column name in AV.Clean is "Volume, AV"
    vol_col = "Volume, AV" if "Volume, AV" in clean_raw.columns else None
    intra = _normalize_intraday(clean_raw, vol_col or "")
    daily = _normalize_daily(bbrg_daily)
    raw_intra = _normalize_intraday(bbrg_intra, "")

    # ---- Coverage summary ----
    sessions = sorted(intra["session_date"].unique())
    report.summary = {
        "sheets": list(sheets.keys()),
        "intraday_rows": int(len(intra)),
        "intraday_first": str(sessions[0]),
        "intraday_last": str(sessions[-1]),
        "n_sessions": len(sessions),
        "daily_rows": int(len(daily)),
        "daily_first": str(daily["session_date"].iloc[0]),
        "daily_last": str(daily["session_date"].iloc[-1]),
        "timing_convention": "bar_start_shifted (inferred, not authoritative Bloomberg metadata)",
        "open_source": "first_bar_endpoint_proxy (workbook has no true open field)",
        "volume_interpretation": "per-interval (not cumulative); evidence: frequent within-session decreases",
    }

    # Re-verify ChatGPT-supplied audit claims
    chatgpt = {}
    bars_per = intra.groupby("session_date").size()
    chatgpt["bars_per_day_counts"] = {str(k): int(v) for k, v in bars_per.value_counts().sort_index().items()}
    chatgpt["half_day_bar_counts"] = {
        str(d): int(bars_per.get(d, 0)) for d in HALF_DAYS
    }
    chatgpt["n_duplicate_timestamps"] = int(intra.duplicated(subset=["timestamp_raw"]).sum())
    chatgpt["n_nonpositive_prices"] = int((intra["last_price"] <= 0).sum())
    chatgpt["n_negative_volumes"] = int((intra["volume"] < 0).sum())

    # Within-session volume decreases
    def _n_decreases(g: pd.DataFrame) -> int:
        v = g.sort_values("timestamp_raw")["volume"].to_numpy()
        return int(np.sum(np.diff(v) < 0))

    n_decr = int(intra.groupby("session_date", group_keys=False).apply(_n_decreases, include_groups=False).sum())
    chatgpt["within_session_volume_decreases"] = n_decr

    # Volume reconciliation vs daily
    # Exclude 16:00 residual from "earlier" sum check as described
    recon_rows = []
    for d, g in intra.groupby("session_date"):
        g = g.sort_values("timestamp_raw")
        sum_vol = float(g["volume"].sum())
        daily_row = daily.loc[daily["session_date"] == d]
        daily_vol = float(daily_row["volume"].iloc[0]) if len(daily_row) else np.nan
        recon_rows.append({
            "session_date": d,
            "sum_av_clean": sum_vol,
            "daily_volume": daily_vol,
            "diff": sum_vol - daily_vol if np.isfinite(daily_vol) else np.nan,
        })
    recon = pd.DataFrame(recon_rows)
    fail = recon[recon["diff"].abs() > 1.0].copy()
    chatgpt["volume_recon_fail_dates"] = [
        {
            "date": str(r.session_date),
            "sum_av_clean": r.sum_av_clean,
            "daily_volume": r.daily_volume,
            "diff": r.diff,
        }
        for r in fail.itertuples()
    ]

    # Close agreement
    close_compare = []
    for d, g in intra.groupby("session_date"):
        g16 = g[g["clock_label"] == time(16, 0)]
        if g16.empty:
            continue
        px = float(g16["last_price"].iloc[-1])
        drow = daily.loc[daily["session_date"] == d]
        if drow.empty:
            continue
        dpx = float(drow["close"].iloc[0])
        close_compare.append(abs(px - dpx))
    chatgpt["close_abs_diff_max"] = float(max(close_compare)) if close_compare else None
    chatgpt["close_exact_matches"] = int(sum(1 for x in close_compare if x == 0.0))
    chatgpt["close_within_0003"] = int(sum(1 for x in close_compare if x <= 0.0003))
    chatgpt["n_close_comparisons"] = len(close_compare)

    # 15:30 vs 16:00 equality rate
    eq1530 = 0
    n1530 = 0
    for d, g in intra.groupby("session_date"):
        a = g[g["clock_label"] == time(15, 30)]
        b = g[g["clock_label"] == time(16, 0)]
        if len(a) and len(b):
            n1530 += 1
            if float(a["last_price"].iloc[-1]) == float(b["last_price"].iloc[-1]):
                eq1530 += 1
    chatgpt["pct_1530_equals_1600"] = eq1530 / n1530 if n1530 else None
    chatgpt["n_1530_1600_pairs"] = n1530

    report.chatgpt_supplied_checks = chatgpt

    # Anomalies from half-days
    for hd in sorted(HALF_DAYS):
        g = intra[intra["session_date"] == hd].sort_values("timestamp_raw")
        labels = [str(t) for t in g["clock_label"].tolist()]
        post = g[g["clock_label"] > time(13, 0)]
        report.add(
            date=str(hd),
            time=None,
            issue="early_close_stale_afternoon_labels",
            evidence=f"labels={labels}; post-13:00 volumes={post['volume'].tolist()}; prices={g['last_price'].tolist()}",
            resolution="Remove labels after real 13:00 close from tradable/band-history; flatten at 13:00 using closing print",
            impact="Prevents phantom afternoon returns and trades on half-days",
            severity="critical",
        )

    for r in fail.itertuples():
        report.add(
            date=str(r.session_date),
            time=None,
            issue="volume_reconciliation_mismatch",
            evidence=f"sum_AV.Clean={r.sum_av_clean:.0f}, BBRG.Daily={r.daily_volume:.0f}, diff={r.diff:.0f}",
            resolution="Keep price history; do not back-allocate residual; document only",
            impact="May affect closing residual audit; pre-close VWAP uses interval volumes only",
            severity="warning",
        )

    report.add(
        date="all",
        time=None,
        issue="no_true_open_field",
        evidence="All price columns are Last Price; no Open column in any sheet",
        resolution="Workbook-only fallback: first regular bar endpoint as open proxy; first entry at next endpoint",
        impact="Adaptation of paper open-anchor rule; not exact replication",
        severity="critical",
    )

    report.add(
        date="all",
        time=None,
        issue="timestamp_bar_convention_inferred",
        evidence=f"15:30 equals 16:00 on {eq1530}/{n1530} days; large 09:30 volumes; separate close rows",
        resolution="Treat labels as bar-start; availability = label+30m for regular bars",
        impact="Signals evaluated at availability times 10:00..16:00 (or 13:00 half-day)",
        severity="warning",
    )

    # Build cleaned tradable frame
    records = []
    for d, g in intra.groupby("session_date"):
        g = g.sort_values("timestamp_raw").copy()
        is_half = d in HALF_DAYS
        session_close_t = time(13, 0) if is_half else time(16, 0)

        # Closing print: prefer exact session close label; half-day may use 13:00 or 16:00 stale
        if is_half:
            close_rows = g[g["clock_label"] == time(13, 0)]
            if close_rows.empty:
                close_rows = g[g["clock_label"] == time(16, 0)]
            # Prefer last price at 13:00 if present
            close_px = float(close_rows["last_price"].iloc[0]) if len(close_rows) else float(g["last_price"].iloc[-1])
        else:
            close_rows = g[g["clock_label"] == time(16, 0)]
            close_px = float(close_rows["last_price"].iloc[-1]) if len(close_rows) else float(g["last_price"].iloc[-1])

        daily_row = daily.loc[daily["session_date"] == d]
        daily_close = float(daily_row["close"].iloc[0]) if len(daily_row) else close_px
        # Prefer daily close within tolerance for consistency
        if abs(close_px - daily_close) <= 0.0003:
            close_px_used = daily_close
        else:
            close_px_used = close_px
            report.add(
                date=str(d),
                time=str(session_close_t),
                issue="close_price_tolerance_exceeded",
                evidence=f"intraday_close={close_px}, daily_close={daily_close}",
                resolution="Use intraday close print",
                impact="Minor series inconsistency",
                severity="info",
            )

        # Regular bars only
        if is_half:
            regular = g[g["clock_label"].isin(HALF_BAR_LABELS)].copy()
        else:
            regular = g[g["clock_label"].isin(FULL_BAR_LABELS)].copy()

        # Interval volumes: already interval; do not difference
        # Exclude 16:00 residual rows (already excluded by FULL_BAR_LABELS)
        # For VWAP, use regular bar volumes only

        for _, row in regular.iterrows():
            avail = _availability_time(row["clock_label"], is_half)
            if avail is None:
                continue
            records.append({
                "session_date": d,
                "clock_label": row["clock_label"],
                "available_at": avail,
                "price": float(row["last_price"]),
                "interval_volume": float(row["volume"]) if pd.notna(row["volume"]) else 0.0,
                "is_half_day": is_half,
                "is_session_close_bar": avail == session_close_t,
                "session_close_time": session_close_t,
                "session_close_price": close_px_used,
                "source_timestamp": row["timestamp_raw"],
            })

        # Ensure a dedicated close liquidation marker exists at session_close_t
        # If last regular bar availability already equals close, its price is the bar end;
        # we still attach session_close_price for liquidation.

    clean = pd.DataFrame(records)
    clean = clean.sort_values(["session_date", "available_at"]).reset_index(drop=True)

    # Open proxy = first regular bar endpoint price of the day
    opens = (
        clean.sort_values(["session_date", "available_at"])
        .groupby("session_date", as_index=False)
        .first()[["session_date", "price"]]
        .rename(columns={"price": "open_proxy"})
    )
    clean = clean.merge(opens, on="session_date", how="left")

    # Prior close from daily series
    daily = daily.sort_values("session_date").reset_index(drop=True)
    daily["prior_close"] = daily["close"].shift(1)
    daily["daily_return"] = daily["close"] / daily["prior_close"] - 1.0

    processed_dir.mkdir(parents=True, exist_ok=True)
    clean.to_csv(processed_dir / "clean_intraday_bars.csv", index=False)
    daily.to_csv(processed_dir / "daily_series.csv", index=False)
    recon.to_csv(processed_dir / "volume_reconciliation.csv", index=False)

    with open(processed_dir / "audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, default=str)

    # Data dictionary
    dd = pd.DataFrame([
        {"field": "session_date", "definition": "US equity session calendar date (America/New_York wall date)"},
        {"field": "clock_label", "definition": "Original workbook time label (inferred bar-start)"},
        {"field": "available_at", "definition": "Information availability time = clock_label + 30 minutes for regular bars"},
        {"field": "price", "definition": "Last Price at bar endpoint (workbook Last Price)"},
        {"field": "interval_volume", "definition": "Per-record volume from Volume, AV; NOT differenced"},
        {"field": "open_proxy", "definition": "First regular bar endpoint price; NOT a verified 09:30 open"},
        {"field": "session_close_price", "definition": "Liquidation price at actual session close (13:00 half-day / 16:00 full)"},
        {"field": "is_half_day", "definition": "True for 2025-07-03 and 2025-11-28"},
    ])
    dd.to_csv(processed_dir / "data_dictionary.csv", index=False)

    return clean, daily, report
