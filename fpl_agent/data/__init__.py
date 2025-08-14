"""
Data management module for FPL Agent.

This module provides a clean, organized pipeline for:
- Data ingestion from FPL API
- Data storage and persistence
- Data processing and enrichment
- Data access and caching
"""

from .data_service import DataService
from .data_store import DataStore
from .data_processor import DataProcessor

__all__ = [
    'DataService',
    'DataStore', 
    'DataProcessor'
]
