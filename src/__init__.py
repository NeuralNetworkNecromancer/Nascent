"""Nascent Daily Futures Data-Quality prototype package."""

import importlib, sys

sys.modules.setdefault(
    __name__ + ".quality_checks", importlib.import_module(__name__ + ".quality_checks")
)
