"""
Data ingestion package for FPL Optimizer
"""

from .fetch_fpl import FPLDataFetcher
from .fetch_understat import UnderstatDataFetcher
from .fetch_fbref import FBRefDataFetcher

__all__ = [
    "FPLDataFetcher",
    "UnderstatDataFetcher", 
    "FBRefDataFetcher"
]
