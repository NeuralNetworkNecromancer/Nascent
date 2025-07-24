"""Shared configuration for data-quality thresholds.
Stored in st.session_state['dq_config'] for global access.
"""

from typing import Dict

import streamlit as st

# Import canonical severities from core library (avoids duplication)
from src.quality_checks import DEFAULT_SEVERITIES  # re-exported below

# ---------------------------------------------------------------------------
# Threshold configuration (volume multiplier, IQR, etc.)
# ---------------------------------------------------------------------------

_DEFAULTS: Dict[str, float] = {
    "volume_factor": 10.0,
    "pct_change_threshold": 0.05,
    "iqr_multiplier": 1.0,
    "flat_price_min_volume": 1,
}


def get_config() -> Dict[str, float]:
    """Return current config, initialising defaults if missing."""
    if "dq_config" not in st.session_state:
        st.session_state["dq_config"] = _DEFAULTS.copy()
    return st.session_state["dq_config"]


def set_config(**kwargs):
    """Update selected keys of the global DQ config held in ``st.session_state``."""
    cfg = get_config()
    cfg.update({k: v for k, v in kwargs.items() if v is not None})
    st.session_state["dq_config"] = cfg
