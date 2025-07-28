"""
Chip strategy optimization functionality for FPL Optimizer
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from ..models import Player, FPLTeam, ChipType


class ChipStrategyOptimizer:
    """Optimizes chip usage strategy"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.chip_rules = config.get("chip_rules", {})
    
    def should_use_wildcard(self, current_team: FPLTeam, available_players: List[Player],
                          player_xpts: Dict[int, float], gameweek: int) -> bool:
        """Determine if wildcard should be used"""
        if not self.chip_rules.get("wildcard_available", False):
            return False
        
        # Calculate current team strength
        current_strength = sum(player_xpts.get(p.id, 0) for p in current_team.players)
        
        # Calculate potential team strength with wildcard
        potential_players = sorted(available_players, 
                                 key=lambda p: player_xpts.get(p.id, 0), reverse=True)
        
        # Simulate optimal wildcard team (simplified)
        optimal_strength = sum(player_xpts.get(p.id, 0) for p in potential_players[:15])
        
        # Use wildcard if improvement is significant
        improvement_threshold = self.chip_rules.get("wildcard_improvement_threshold", 50.0)
        return (optimal_strength - current_strength) > improvement_threshold
    
    def should_use_triple_captain(self, current_team: FPLTeam, player_xpts: Dict[int, float],
                                gameweek: int) -> Optional[int]:
        """Determine if triple captain should be used and on which player"""
        if not self.chip_rules.get("triple_captain_available", False):
            return None
        
        # Find player with highest expected points
        best_player = max(current_team.players, key=lambda p: player_xpts.get(p.id, 0))
        best_xpts = player_xpts.get(best_player.id, 0)
        
        # Use triple captain if expected points are very high
        threshold = self.chip_rules.get("triple_captain_threshold", 15.0)
        if best_xpts > threshold:
            return best_player.id
        
        return None
    
    def should_use_bench_boost(self, current_team: FPLTeam, player_xpts: Dict[int, float],
                             gameweek: int) -> bool:
        """Determine if bench boost should be used"""
        if not self.chip_rules.get("bench_boost_available", False):
            return False
        
        # Calculate bench strength
        bench_players = current_team.players[11:]  # Assuming first 11 are starting
        bench_strength = sum(player_xpts.get(p.id, 0) for p in bench_players)
        
        # Use bench boost if bench is strong
        threshold = self.chip_rules.get("bench_boost_threshold", 20.0)
        return bench_strength > threshold
    
    def should_use_free_hit(self, current_team: FPLTeam, available_players: List[Player],
                          player_xpts: Dict[int, float], gameweek: int) -> bool:
        """Determine if free hit should be used"""
        if not self.chip_rules.get("free_hit_available", False):
            return False
        
        # Check if current team has many issues (injuries, suspensions, etc.)
        problematic_players = [p for p in current_team.players if p.is_injured or p.xMins_pct < 0.5]
        
        # Use free hit if too many problems
        problem_threshold = self.chip_rules.get("free_hit_problem_threshold", 5)
        return len(problematic_players) >= problem_threshold
    
    def get_chip_recommendations(self, current_team: FPLTeam, available_players: List[Player],
                               player_xpts: Dict[int, float], gameweek: int) -> Dict[str, Any]:
        """Get comprehensive chip usage recommendations"""
        recommendations = {
            "wildcard": self.should_use_wildcard(current_team, available_players, player_xpts, gameweek),
            "triple_captain": self.should_use_triple_captain(current_team, player_xpts, gameweek),
            "bench_boost": self.should_use_bench_boost(current_team, player_xpts, gameweek),
            "free_hit": self.should_use_free_hit(current_team, available_players, player_xpts, gameweek)
        }
        
        return recommendations
