"""
FPL Agent - AI-Powered Fantasy Premier League Manager
"""

__version__ = "1.0.0"
__author__ = "FPL Agent Team"

from .core.config import Config
from .core.models import FPLTeam

__all__ = [
    "Config",
    "FPLTeam"
] 