"""quality_checks.py – thin wrapper re-exporting everything from eda_utils.
Eventually eda_utils will be fully renamed; both names work during transition."""

from . import eda_utils as _base  # noqa: F401
from .eda_utils import load_data as load_data  # type: ignore

# Re-export all symbols
globals().update(_base.__dict__)

del _base 