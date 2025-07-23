"""Heatmap chart helpers using seaborn."""

from __future__ import annotations

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st


def missing_symbol_heatmap(df: pd.DataFrame) -> None:
    """Display a calendar-style heatmap of symbol counts per day."""
    pivot = (
        df.groupby(["Date", "Symbol"], as_index=False)["Close"].size()
        .assign(present=1)
        .pivot_table(index="Date", columns="Symbol", values="present", fill_value=0)
    )
    plt.figure(figsize=(12, 4))
    sns.heatmap(pivot.T, cmap="viridis", cbar=False)
    plt.xlabel("Date")
    plt.ylabel("Symbol")
    plt.title("Symbol presence by date (1=present, 0=missing)")
    st.pyplot(plt.gcf()) 