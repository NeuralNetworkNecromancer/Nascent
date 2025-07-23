"""OHLC Integrity page."""

import streamlit as st
import pandas as pd
from src import eda_utils as eu

st.title("📉 OHLC Integrity Checks")

df: pd.DataFrame = st.session_state.get("data") if "data" in st.session_state else eu.load_data()

viol = eu.ohlc_integrity_violations(df)

st.write(f"Rows failing OHLC logical ordering: {len(viol)}")
if st.checkbox("Show sample of violations"):
    st.dataframe(viol.head()) 