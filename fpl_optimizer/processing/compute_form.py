"""
Form computation functionality for FPL Optimizer
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from ..models import Player, Team


class FormCalculator:
    """Calculates form metrics for players and teams"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.form_window = config.get("form_window", 5)  # Default 5 gameweeks
    
    def calculate_player_form(self, player: Player, recent_performances: List[Dict]) -> float:
        """Calculate player form based on recent performances"""
        if not recent_performances:
            return 0.0
        
        # Simple average of recent points
        recent_points = [p.get("points", 0) for p in recent_performances[-self.form_window:]]
        return sum(recent_points) / len(recent_points)
    
    def calculate_team_form(self, team: Team, recent_results: List[Dict]) -> float:
        """Calculate team form based on recent results"""
        if not recent_results:
            return 0.0
        
        # Simple average of recent results (wins=3, draws=1, losses=0)
        recent_scores = []
        for result in recent_results[-self.form_window:]:
            if result.get("result") == "W":
                recent_scores.append(3)
            elif result.get("result") == "D":
                recent_scores.append(1)
            else:
                recent_scores.append(0)
        
        return sum(recent_scores) / len(recent_scores)
    
    def calculate_all_players_form(self, players: List[Player], 
                                 performance_data: Dict[int, List[Dict]]) -> Dict[int, float]:
        """Calculate form for all players"""
        form_scores = {}
        for player in players:
            recent_performances = performance_data.get(player.id, [])
            form_scores[player.id] = self.calculate_player_form(player, recent_performances)
        return form_scores
    
    def calculate_all_teams_form(self, teams: List[Team], 
                               results_data: Dict[int, List[Dict]]) -> Dict[int, float]:
        """Calculate form for all teams"""
        form_scores = {}
        for team in teams:
            recent_results = results_data.get(team.id, [])
            form_scores[team.id] = self.calculate_team_form(team, recent_results)
        return form_scores
