"""
Minutes prediction functionality for FPL Optimizer
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from ..models import Player, Team


class MinutesPredictor:
    """Predicts expected minutes for players"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def predict_player_minutes(self, player: Player, recent_minutes: List[int], 
                             team_form: float, is_home: bool) -> float:
        """Predict expected minutes for a player"""
        if player.is_injured:
            return 0.0
        
        # Base minutes from recent history
        if recent_minutes:
            base_minutes = sum(recent_minutes) / len(recent_minutes)
        else:
            base_minutes = 90.0  # Default to full match
        
        # Adjust for team form (better form = more minutes)
        form_adjustment = team_form * 0.1
        
        # Adjust for home/away (slight home advantage)
        venue_adjustment = 5.0 if is_home else 0.0
        
        # Apply player's expected minutes percentage
        adjusted_minutes = (base_minutes + form_adjustment + venue_adjustment) * player.xMins_pct
        
        return max(0.0, min(90.0, adjusted_minutes))
    
    def predict_all_players_minutes(self, players: List[Player], 
                                  minutes_data: Dict[int, List[int]],
                                  team_forms: Dict[int, float],
                                  is_home: bool) -> Dict[int, float]:
        """Predict minutes for all players"""
        minutes_predictions = {}
        for player in players:
            recent_minutes = minutes_data.get(player.id, [])
            team_form = team_forms.get(player.team_id, 0.0)
            minutes_predictions[player.id] = self.predict_player_minutes(
                player, recent_minutes, team_form, is_home
            )
        return minutes_predictions
