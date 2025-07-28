"""
FPL Optimizer - Fully Automated Fantasy Premier League Manager
"""

__version__ = "1.0.0"
__author__ = "FPL Optimizer Team"

from .config import Config
from .models import Player, Team, Fixture, Gameweek, FPLTeam, OptimizationResult, Transfer
from .main import FPLOptimizer

__all__ = [
    "Config",
    "Player", 
    "Team",
    "Fixture",
    "Gameweek",
    "FPLTeam",
    "OptimizationResult",
    "Transfer",
    "FPLOptimizer"
] 