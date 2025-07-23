"""Outliers & Volume Anomalies page."""

import streamlit as st
import pandas as pd
from src import eda_utils as eu

st.title("🚨 Outliers & Volume Anomalies")

df: pd.DataFrame = st.session_state.get("data") if "data" in st.session_state else eu.load_data()

pct_outliers = eu.pct_change_outliers(df)
abs_outliers = eu.iqr_price_outliers(df)
zero_vol_move, extreme_vol = eu.volume_anomalies(df)

st.metric("Day-over-day % outliers", len(pct_outliers))
st.metric("IQR price outliers", len(abs_outliers))
st.metric("Zero volume but price moved", len(zero_vol_move))
st.metric("Extreme volume spikes", len(extreme_vol))

if st.checkbox("Show top 10 pct-change outliers"):
    st.dataframe(pct_outliers.head(10)) 