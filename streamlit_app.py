"""Streamlit Cloud entrypoint.

Simply re-exports the main dashboard defined in `app.main` so that Cloud
picks up the correct page.
"""

import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)

# Launch the actual dashboard
from app import main as _main  # noqa: F401
