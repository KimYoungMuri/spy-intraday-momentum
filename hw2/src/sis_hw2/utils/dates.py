"""Datetime helpers that tolerate mixed tz-aware / tz-naive values."""

from __future__ import annotations

import pandas as pd


def to_naive_timestamp(series: pd.Series) -> pd.Series:
    """Convert a Series to timezone-naive timestamps without mixing errors."""
    out = []
    for v in series:
        if pd.isna(v):
            out.append(pd.NaT)
            continue
        ts = pd.Timestamp(v)
        if ts.tzinfo is not None:
            ts = ts.tz_convert("UTC").tz_localize(None)
        out.append(ts)
    return pd.Series(out, index=series.index, dtype="datetime64[ns]")


def to_naive_scalar(v) -> pd.Timestamp:
    if pd.isna(v):
        return pd.NaT
    ts = pd.Timestamp(v)
    if ts.tzinfo is not None:
        return ts.tz_convert("UTC").tz_localize(None)
    return ts
