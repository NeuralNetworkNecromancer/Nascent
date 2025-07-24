"""Caching utilities for Streamlit app.

Thin wrapper around :pyfunc:`src.quality_checks.load_data` providing
`st.cache_data` memoisation so repeated uploads or dashboard reloads
do not re-parse the CSV."""

from pathlib import Path
import pandas as pd
import streamlit as st

from src.quality_checks import load_data as _load_data


@st.cache_data(show_spinner="Loading dataset...")
def load_data(path: str | Path | None = None) -> pd.DataFrame:
    """Cached wrapper around :pyfunc:`src.quality_checks.load_data`."""
    try:
        return _load_data(path)
    except FileNotFoundError as exc:
        st.warning("Dataset not found – using empty DataFrame. Upload a CSV via sidebar or place data/raw/futures_dataset.csv.")
        import pandas as pd

        return pd.DataFrame() 