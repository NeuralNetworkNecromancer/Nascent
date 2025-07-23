"""Main entry for Streamlit dashboard (moved from root)."""

import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from app.utils.caching import load_data
from src import eda_utils as eu

st.set_page_config(page_title="Daily Futures – Data Quality Dashboard", layout="wide")


def get_data() -> pd.DataFrame:
    """Load data (cached) from default path or user upload."""
    uploaded = st.sidebar.file_uploader("Upload CSV with same schema", type="csv")
    if uploaded is not None:
        return load_data(uploaded)
    st.sidebar.info("Using bundled sample dataset.")
    return load_data()


def main() -> None:
    st.title("📈 Daily Futures Data-Quality Dashboard")
    df = get_data()
    st.session_state["data"] = df

    st.subheader("Dataset Overview")
    st.write(f"Rows: {len(df):,}  |  Columns: {df.shape[1]}")
    st.dataframe(df.head())

    with st.expander("Show descriptive statistics"):
        st.dataframe(df.describe())

    fig, ax = plt.subplots(figsize=(8, 3))
    sns.histplot(df["Close"], bins=100, ax=ax)
    ax.set_title("Distribution of Close Prices (all symbols)")
    st.pyplot(fig)

    coverage = eu.symbol_coverage(df)
    duplicates = eu.duplicated_rows(df)
    ohlc_viol = eu.ohlc_integrity_violations(df)
    flat_zero, flat_volume = eu.flatline_rows(df)
    pct_outliers = eu.pct_change_outliers(df)

    st.subheader("Quick Diagnostics")
    st.metric("Duplicate (Date, Symbol)", len(duplicates))
    st.metric("OHLC integrity violations", len(ohlc_viol))
    st.metric("Flatlines volume=0", len(flat_zero))
    st.metric("Flatlines volume>0", len(flat_volume))
    st.metric("Outlier day-over-day moves (>50%)", len(pct_outliers))

    st.info("Navigate to detailed pages via the left sidebar ➜")


if __name__ == "__main__":
    main() 