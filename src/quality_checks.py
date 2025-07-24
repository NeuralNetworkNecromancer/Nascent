"""quality_checks.py
Comprehensive data-quality rule library for daily futures datasets.

This module contains:
1. `load_data` convenience CSV loader used by Streamlit & scripts.
2. A suite of pure validation functions (one per rule) that return a
   *filtered* `pd.DataFrame` of offending rows.
3. Helper utilities (e.g. flatline detection) reused by several rules.
4. Registry dictionaries:
   • `CHECK_FUNCTIONS` maps rule name ➜ callable
   • `DESCRIPTIONS`    human-readable explanations for UI/docs
   • `DEFAULT_SEVERITIES` default criticality classification

All functions are *side-effect-free* no Streamlit/OpenAI imports so they
are unit-testable and re-usable in batch jobs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

DEFAULT_LOCATIONS = [
    Path("app/data/raw/futures_dataset.csv"),
]


def load_data(csv_path: str | Path | None = None) -> pd.DataFrame:
    """Load dataset from *csv_path* or the default raw data location.

    Parameters
    ----------
    csv_path : str | Path | None, optional
        Explicit path to a CSV file. If *None*, the loader attempts the
        canonical paths defined in ``DEFAULT_LOCATIONS``.

    Returns
    -------
    pd.DataFrame
        Parsed DataFrame containing the futures dataset.

    Raises
    ------
    FileNotFoundError
        If no CSV is found in the provided / default locations.
    """
    if csv_path:
        path = Path(csv_path)
        return pd.read_csv(path)

    # Try default locations in order
    for candidate in DEFAULT_LOCATIONS:
        if candidate.exists():
            return pd.read_csv(candidate)

    raise FileNotFoundError("futures_dataset.csv not found in default locations.")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

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
        (df["Low"] > df["High"])
        | (df["Close"] > df["High"])
        | (df["Close"] < df["Low"])
        | (df["Open"] > df["High"])
        | (df["Open"] < df["Low"])
    ].copy()
    return violations


# === Flatlines ===


def flatline_rows(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return two DataFrames: (volume == 0, volume > 0) where OHLC are identical."""
    flat_mask = (
        (df["Open"] == df["High"])
        & (df["Open"] == df["Low"])
        & (df["Open"] == df["Close"])
    )
    flat = df[flat_mask].copy()
    return flat[flat["Volume"] == 0], flat[flat["Volume"] > 0]


# --- New flat price helpers ---


def stagnant_price(df: pd.DataFrame) -> pd.DataFrame:
    """Flat price rows where Volume == 0 (likely non-trading day)."""
    return flatline_rows(df)[0]


def flat_price_anomaly(df: pd.DataFrame, min_volume: int = 1) -> pd.DataFrame:
    """Flat price rows where Volume ≥ *min_volume* (suspicious)."""
    vol_rows = flatline_rows(df)[1]
    return vol_rows[vol_rows["Volume"] >= min_volume]


# === Missing dates ===


def missing_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows representing (Symbol, Date) combinations that are missing.

    Output columns: ``Symbol`` and ``MissingDate`` (ISO date).
    """
    symbols = df["Symbol"].unique()
    full_dates = pd.date_range(df["Date"].min(), df["Date"].max(), freq="D")

    records = []
    for sym in symbols:
        dates_present = pd.to_datetime(df[df["Symbol"] == sym]["Date"].unique())
        missing = set(full_dates) - set(dates_present)
        for d in missing:
            records.append({"Symbol": sym, "MissingDate": d.date()})

    return pd.DataFrame(records)


# === High < Low inversion ===


def high_low_inversion(df: pd.DataFrame) -> pd.DataFrame:
    """Rows where High < Low (explicit inversion check)."""
    return df[df["High"] < df["Low"]].copy()


# === Negative numeric ===


def negative_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Rows where any numeric field is negative."""
    numeric_cols = df.select_dtypes("number").columns
    mask = (df[numeric_cols] < 0).any(axis=1)
    return df[mask].copy()


# === Outliers ===


def pct_change_outliers(df: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """Flag rows where absolute day-over-day close change exceeds *threshold* (50 % default)."""
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


def volume_anomalies(
    df: pd.DataFrame, factor: float = 10.0
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return (zero_volume_price_moved, extreme_volume_rows)."""
    df_sorted = df.sort_values(["Symbol", "Date"]).copy()
    df_sorted["close_diff"] = df_sorted.groupby("Symbol")["Close"].diff().abs()

    zero_vol_price_move = df_sorted[
        (df_sorted["Volume"] == 0) & (df_sorted["close_diff"] > 0)
    ]

    extreme_volume_rows = []
    for symbol, grp in df.groupby("Symbol"):
        # Use median of *non-zero* volumes to avoid threshold always zero when volumes are sparse
        median_vol = grp.loc[grp["Volume"] > 0, "Volume"].median()
        # Fallback to 0 if all volumes are zero for that symbol
        if pd.isna(median_vol) or median_vol == 0:
            continue
        threshold = median_vol * factor
        extreme_volume_rows.append(grp[grp["Volume"] > threshold])
    extreme_volume_rows_df = (
        pd.concat(extreme_volume_rows)
        if extreme_volume_rows
        else pd.DataFrame(columns=df.columns)
    )

    return zero_vol_price_move, extreme_volume_rows_df


# === Schema check ===

EXPECTED_COLUMNS: Dict[str, str] = {
    "Date": "int64",
    "Symbol": "object",
    "Open": "int64",
    "High": "int64",
    "Low": "int64",
    "Close": "int64",
    "Volume": "int64",
    "Open Interest": "int64",
}


def check_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Return DataFrame describing schema mismatches (empty if ok).

    Output columns: ``field, expected_dtype, found_dtype, note``
    """
    issues = []
    for col, dtype in EXPECTED_COLUMNS.items():
        if col not in df.columns:
            issues.append(
                {
                    "field": col,
                    "expected": dtype,
                    "found": "<missing>",
                    "note": "column missing",
                }
            )
        else:
            found = str(df[col].dtype)
            if found != dtype:
                issues.append(
                    {
                        "field": col,
                        "expected": dtype,
                        "found": found,
                        "note": "dtype mismatch",
                    }
                )
    return pd.DataFrame(issues)


# === Open interest check ===


def check_oi(df: pd.DataFrame, spike_factor: float = 10.0) -> pd.DataFrame:
    """Flag rows where Open Interest is negative or extreme spike (>factor×median)."""
    if "Open Interest" not in df.columns:
        return pd.DataFrame()
    oi_series = df["Open Interest"]
    median = oi_series.median() if not oi_series.empty else 0
    mask = (oi_series < 0) | (oi_series > median * spike_factor)
    return df[mask].copy()


# ---------------------------------------------------------------------------
# Registry – descriptions, severities, function mapping
# ---------------------------------------------------------------------------

DESCRIPTIONS: Dict[str, str] = {
    "Duplicate row": "Ensure each (Date, Symbol) appears only once.",
    "Missing date": "Compare a symbol's dates to the calendar to flag gaps.",
    "OHLC range violation": "Flag rows where High < Low or Open/Close lie outside [Low, High].",
    "Stagnant price": "Price flat and Volume = 0 (likely closed or no trades).",
    "Flat price anomaly": "Price flat while Volume ≥ threshold (configurable).",
    "Zero-volume with move": "Alert when price changes but Volume = 0.",
    "Extreme volume outlier": "Volume exceeds N × median for a symbol (configurable).",
    "Day-over-day jump": "Close changes more than threshold % between consecutive days.",
    "Absolute price bounds (IQR)": "Prices that are unusually high or low for the symbol.",
    "High < Low inversion": "Explicit test where reported High is less than Low.",
    "Negative numeric": "Any negative price, volume, or open-interest fields.",
    "Schema": "Assert expected columns & dtypes.",
    "Open interest": "Flag negative OI or extreme spikes.",
}

DEFAULT_SEVERITIES: Dict[str, str] = {
    "Duplicate row": "major",
    "Missing date": "minor",
    "OHLC range violation": "critical",
    "Stagnant price": "major",
    "Flat price anomaly": "minor",
    "Zero-volume with move": "major",
    "Extreme volume outlier": "minor",
    "Day-over-day jump": "minor",
    "Absolute price bounds (IQR)": "minor",
    "High < Low inversion": "critical",
    "Negative numeric": "critical",
    "Schema": "critical",
    "Open interest": "minor",
}

CHECK_FUNCTIONS: Dict[str, callable] = {
    "Duplicate row": duplicated_rows,
    "Missing date": missing_dates,
    "OHLC range violation": ohlc_integrity_violations,
    "Stagnant price": stagnant_price,
    "Flat price anomaly": flat_price_anomaly,
    "Zero-volume with move": lambda d: volume_anomalies(d)[0],
    "Extreme volume outlier": lambda d: volume_anomalies(d)[1],
    "Day-over-day jump": pct_change_outliers,
    "Absolute price bounds (IQR)": iqr_price_outliers,
    "High < Low inversion": high_low_inversion,
    "Negative numeric": negative_numeric,
    "Schema": check_schema,
    "Open interest": check_oi,
}

# ---------------------------------------------------------------------------
# Public export list (helps static analysers & ``from … import *`` hygiene)
# ---------------------------------------------------------------------------

__all__ = [
    "load_data",
    # helper / core rules
    "symbol_coverage",
    "duplicated_rows",
    "ohlc_integrity_violations",
    "stagnant_price",
    "flat_price_anomaly",
    "missing_dates",
    "high_low_inversion",
    "negative_numeric",
    "pct_change_outliers",
    "iqr_price_outliers",
    "volume_anomalies",
    "check_schema",
    "check_oi",
    # registries
    "DESCRIPTIONS",
    "DEFAULT_SEVERITIES",
    "CHECK_FUNCTIONS",
]
