"""
Fixture difficulty calculation functionality for FPL Optimizer
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from ..models import Team, Fixture


class FixtureDifficultyCalculator:
    """Calculates fixture difficulty ratings"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.difficulty_weights = config.get("difficulty_weights", {
            "team_strength": 0.4,
            "home_advantage": 0.2,
            "recent_form": 0.3,
            "head_to_head": 0.1
        })
    
    def calculate_fixture_difficulty(self, fixture: Fixture, home_team: Team, 
                                   away_team: Team, team_forms: Dict[int, float]) -> float:
        """Calculate difficulty rating for a fixture (1-5 scale)"""
        # Base difficulty from team strength difference
        strength_diff = away_team.strength - home_team.strength
        
        # Home advantage (reduces difficulty for home team)
        home_advantage = -0.5
        
        # Recent form difference
        home_form = team_forms.get(home_team.id, 0.0)
        away_form = team_forms.get(away_team.id, 0.0)
        form_diff = away_form - home_form
        
        # Calculate weighted difficulty
        difficulty = (
            strength_diff * self.difficulty_weights["team_strength"] +
            home_advantage * self.difficulty_weights["home_advantage"] +
            form_diff * self.difficulty_weights["recent_form"]
        )
        
        # Convert to 1-5 scale
        difficulty_rating = max(1.0, min(5.0, 3.0 + difficulty * 2.0))
        
        return difficulty_rating
    
    def calculate_all_fixtures_difficulty(self, fixtures: List[Fixture], 
                                        teams: List[Team],
                                        team_forms: Dict[int, float]) -> Dict[int, float]:
        """Calculate difficulty for all fixtures"""
        team_dict = {team.id: team for team in teams}
        difficulties = {}
        
        for fixture in fixtures:
            home_team = team_dict.get(fixture.home_team_id)
            away_team = team_dict.get(fixture.away_team_id)
            
            if home_team and away_team:
                difficulties[fixture.id] = self.calculate_fixture_difficulty(
                    fixture, home_team, away_team, team_forms
                )
            else:
                difficulties[fixture.id] = 3.0  # Default medium difficulty
        
        return difficulties
