"""
FPL Optimizer - Fully Automated Fantasy Premier League Manager
"""

__version__ = "1.0.0"
__author__ = "FPL Optimizer Team"

from .core.config import Config
from .core.models import Player, Team, FPLTeam, OptimizationResult, Transfer
from .main import FPLOptimizer

__all__ = [
    "Config",
    "Player", 
    "Team",
    "FPLTeam",
    "OptimizationResult",
    "Transfer",
    "FPLOptimizer"
] 