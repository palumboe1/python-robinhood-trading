"""A small, pandas-friendly Robinhood trading toolkit."""
from __future__ import annotations

import logging

from .config import Config
from .client import RobinhoodClient
from .trader import Trader

__all__ = ["Trader", "Config", "RobinhoodClient"]
__version__ = "0.1.0"

# Library code should not configure logging handlers; leave that to the app.
logging.getLogger(__name__).addHandler(logging.NullHandler())
