"""
Data ingestion package for FPL Optimizer
"""

from .fetch_fpl import FPLDataFetcher
from .fetch_understat import UnderstatDataFetcher
from .fetch_fbref import FBRefDataFetcher
from .test_data_fetcher import TestDataFetcher, get_test_data

__all__ = [
    "FPLDataFetcher",
    "UnderstatDataFetcher", 
    "FBRefDataFetcher",
    "TestDataFetcher",
    "get_test_data"
]
