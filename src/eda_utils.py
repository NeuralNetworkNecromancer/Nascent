"""eda_utils.py
Utility functions to load the futures dataset and compute data-quality diagnostics.

All functions are pure (no Streamlit imports) so they can be unit-tested.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

DEFAULT_LOCATIONS = [
    Path("app/data/raw/futures_dataset.csv"),
]


def load_data(csv_path: str | Path | None = None) -> pd.DataFrame:
    """Load dataset from *csv_path* or the default raw data location."""
    if csv_path:
        path = Path(csv_path)
        return pd.read_csv(path)

    # try default locations
    for candidate in DEFAULT_LOCATIONS:
        if candidate.exists():
            return pd.read_csv(candidate)

    raise FileNotFoundError("futures_dataset.csv not found in default locations.")


# === Coverage & duplicates ===

def symbol_coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Return per-date count of unique symbols."""
    return (
        df.groupby("Date", as_index=False)["Symbol"]
        .nunique()
        .rename(columns={"Symbol": "symbol_count"})
    )


def duplicated_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Return duplicated (Date, Symbol) rows."""
    mask = df.duplicated(subset=["Date", "Symbol"], keep=False)
    return df.loc[mask].copy()


# === OHLC integrity ===

def ohlc_integrity_violations(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows where OHLC logical relationships are violated."""
    violations = df[
        (df["Low"] > df["High"]) |
        (df["Close"] > df["High"]) |
        (df["Close"] < df["Low"]) |
        (df["Open"] > df["High"]) |
        (df["Open"] < df["Low"])
    ].copy()
    return violations


# === Flatlines ===

def flatline_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return two DataFrames: (volume == 0, volume > 0) where OHLC are identical."""
    flat_mask = (
        (df["Open"] == df["High"]) &
        (df["Open"] == df["Low"]) &
        (df["Open"] == df["Close"])
    )
    flat = df[flat_mask].copy()
    return flat[flat["Volume"] == 0], flat[flat["Volume"] > 0]


# === Outliers ===

def pct_change_outliers(df: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """Flag rows where absolute day-over-day close change exceeds *threshold* (50% default)."""
    df_sorted = df.sort_values(["Symbol", "Date"]).copy()
    df_sorted["close_pct_change"] = df_sorted.groupby("Symbol")["Close"].pct_change()
    mask = df_sorted["close_pct_change"].abs() > threshold
    return df_sorted.loc[mask]


def iqr_price_outliers(df: pd.DataFrame, multiplier: float = 3.0) -> pd.DataFrame:
    """Flag absolute price outliers per symbol via IQR method."""
    outlier_rows = []
    for symbol, grp in df.groupby("Symbol"):
        q1 = grp["Close"].quantile(0.25)
        q3 = grp["Close"].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr
        outlier_rows.append(grp[(grp["Close"] < lower) | (grp["Close"] > upper)])
    return pd.concat(outlier_rows) if outlier_rows else pd.DataFrame(columns=df.columns)


# === Volume anomalies ===

def volume_anomalies(df: pd.DataFrame, factor: float = 10.0) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return (zero_volume_price_moved, extreme_volume_rows)."""
    df_sorted = df.sort_values(["Symbol", "Date"]).copy()
    df_sorted["close_diff"] = df_sorted.groupby("Symbol")["Close"].diff().abs()

    zero_vol_price_move = df_sorted[(df_sorted["Volume"] == 0) & (df_sorted["close_diff"] > 0)]

    extreme_volume_rows = []
    for symbol, grp in df.groupby("Symbol"):
        threshold = grp["Volume"].median() * factor
        extreme_volume_rows.append(grp[grp["Volume"] > threshold])
    extreme_volume_rows_df = (
        pd.concat(extreme_volume_rows) if extreme_volume_rows else pd.DataFrame(columns=df.columns)
    )

    return zero_vol_price_move, extreme_volume_rows_df 