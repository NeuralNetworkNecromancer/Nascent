"""Flatlines & Stale Prices page."""

import streamlit as st
import pandas as pd
from src import eda_utils as eu

st.title("🟰 Flatlines & Stale Prices")

df: pd.DataFrame = st.session_state.get("data") if "data" in st.session_state else eu.load_data()

flat_zero, flat_vol = eu.flatline_rows(df)

st.metric("Flatline rows volume=0", len(flat_zero))
st.metric("Flatline rows volume>0", len(flat_vol))

if st.checkbox("Show flatlines (volume>0)"):
    st.dataframe(flat_vol.head()) 