"""Coverage and Duplicates page."""

import streamlit as st
import pandas as pd
from src import eda_utils as eu
from app.components.heatmaps import missing_symbol_heatmap

st.title("🗃️ Coverage & Duplicates")

df: pd.DataFrame = st.session_state.get("data") if "data" in st.session_state else eu.load_data()

coverage = eu.symbol_coverage(df)

st.subheader("Symbol coverage per trading day")
missing_symbol_heatmap(df)

missing_days = coverage[coverage["symbol_count"] < 10]

st.write(f"Days with <10 symbols: {len(missing_days)}")
if st.checkbox("Show missing-day table"):
    st.dataframe(missing_days.head(50))

st.subheader("Duplicate (Date, Symbol) records")
dups = eu.duplicated_rows(df)
st.write(f"Total duplicates: {len(dups)}")
if st.checkbox("Show duplicate rows"):
    st.dataframe(dups.head()) 