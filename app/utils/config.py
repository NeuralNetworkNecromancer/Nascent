"""Shared configuration for data-quality thresholds.
Stored in st.session_state['dq_config'] for global access.
"""

from typing import Dict
import streamlit as st

_DEFAULTS: Dict[str, float] = {
    "volume_factor": 10.0,
    "pct_change_threshold": 0.5,  # 50%
    "iqr_multiplier": 3.0,
    "flat_price_min_volume": 1,
}


def get_config() -> Dict[str, float]:
    """Return current config, initialising defaults if missing."""
    if "dq_config" not in st.session_state:
        st.session_state["dq_config"] = _DEFAULTS.copy()
    return st.session_state["dq_config"]


def set_config(**kwargs):
    cfg = get_config()
    cfg.update({k: v for k, v in kwargs.items() if v is not None})
    st.session_state["dq_config"] = cfg 


DEFAULT_SEVERITIES = {
    "Duplicate row": "critical",
    "Missing date": "major",
    "OHLC range violation": "critical",
    "Stagnant price": "minor",
    "Flat price anomaly": "major",
    "Zero-volume with move": "critical",
    "Extreme volume outlier": "minor",
    "Day-over-day jump": "minor",
    "Absolute price bounds (IQR)": "minor",
    "High < Low inversion": "critical",
    "Negative numeric": "critical",
    "Schema": "critical",
    "Open interest": "minor",
}