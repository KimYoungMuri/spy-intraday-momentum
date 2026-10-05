"""Simple tabular I/O without requiring pyarrow."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_frame(df: pd.DataFrame, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".csv":
        df.to_csv(path, index=False)
    else:
        # pickle is dependency-free and preserves dtypes
        if path.suffix == ".parquet":
            path = path.with_suffix(".pkl")
        df.to_pickle(path)
    return path


def load_frame(path: Path) -> pd.DataFrame:
    path = Path(path)
    if path.exists():
        if path.suffix == ".csv":
            return pd.read_csv(path, parse_dates=["date"] if "date" in pd.read_csv(path, nrows=0).columns else None)
        return pd.read_pickle(path)
    # try alternate suffixes
    for alt in [path.with_suffix(".pkl"), path.with_suffix(".csv"), path.with_suffix(".parquet")]:
        if alt.exists():
            if alt.suffix == ".csv":
                return pd.read_csv(alt)
            if alt.suffix == ".parquet":
                return pd.read_parquet(alt)
            return pd.read_pickle(alt)
    raise FileNotFoundError(path)
