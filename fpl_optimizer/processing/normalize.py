"""
Data normalization and cleaning
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta

from ..models import Player, Team, Fixture, Gameweek
from ..config import Config


logger = logging.getLogger(__name__)


class DataNormalizer:
    """Normalizes and cleans data from different sources"""
    
    def __init__(self, config: Config):
        self.config = config
        
    def normalize_players(self, players: List[Player]) -> List[Player]:
        """Normalize player data"""
        logger.info("Normalizing player data...")
        
        normalized_players = []
        
        for player in players:
            try:
                # Clean player name
                player.name = self._clean_player_name(player.name)
                
                # Normalize team names
                player.team_name = self._normalize_team_name(player.team_name)
                player.team_short_name = self._normalize_team_short_name(player.team_short_name)
                
                # Normalize numeric fields
                player.price = self._normalize_price(player.price)
                player.form = self._normalize_form(player.form)
                player.points_per_game = self._normalize_points_per_game(player.points_per_game)
                player.xG = self._normalize_xg_xa(player.xG)
                player.xA = self._normalize_xg_xa(player.xA)
                player.xGC = self._normalize_xg_xa(player.xGC)
                player.xMins_pct = self._normalize_playing_time(player.xMins_pct)
                player.selected_by_pct = self._normalize_percentage(player.selected_by_pct)
                
                # Handle injury data
                player = self._normalize_injury_data(player)
                
                # Validate data
                if self._validate_player(player):
                    normalized_players.append(player)
                else:
                    logger.warning(f"Player {player.name} failed validation, skipping")
                    
            except Exception as e:
                logger.warning(f"Failed to normalize player {player.name}: {e}")
                continue
        
        logger.info(f"Normalized {len(normalized_players)} players")
        return normalized_players
    
    def normalize_teams(self, teams: List[Team]) -> List[Team]:
        """Normalize team data"""
        logger.info("Normalizing team data...")
        
        normalized_teams = []
        
        for team in teams:
            try:
                # Clean team names
                team.name = self._clean_team_name(team.name)
                team.short_name = self._normalize_team_short_name(team.short_name)
                
                # Normalize numeric fields
                team.strength = self._normalize_strength(team.strength)
                team.form = self._normalize_form(team.form)
                team.xG = self._normalize_xg_xa(team.xG)
                team.xGA = self._normalize_xg_xa(team.xGA)
                
                # Provide realistic defaults for missing team stats
                team.xG = self._get_default_team_xg(team.name) if team.xG == 0.0 else team.xG
                team.xGA = self._get_default_team_xga(team.name) if team.xGA == 0.0 else team.xGA
                
                # Validate data
                if self._validate_team(team):
                    normalized_teams.append(team)
                else:
                    logger.warning(f"Team {team.name} failed validation, skipping")
                    
            except Exception as e:
                logger.warning(f"Failed to normalize team {team.name}: {e}")
                continue
        
        logger.info(f"Normalized {len(normalized_teams)} teams")
        return normalized_teams
    
    def normalize_fixtures(self, fixtures: List[Fixture]) -> List[Fixture]:
        """Normalize fixture data"""
        logger.info("Normalizing fixture data...")
        
        normalized_fixtures = []
        
        for fixture in fixtures:
            try:
                # Normalize team names
                fixture.home_team_name = self._normalize_team_name(fixture.home_team_name)
                fixture.away_team_name = self._normalize_team_name(fixture.away_team_name)
                
                # Normalize difficulty ratings
                fixture.difficulty = self._normalize_difficulty(fixture.difficulty)
                fixture.home_difficulty = self._normalize_difficulty(fixture.home_difficulty)
                fixture.away_difficulty = self._normalize_difficulty(fixture.away_difficulty)
                
                # Normalize expected stats
                fixture.expected_goals = self._normalize_expected_goals(fixture.expected_goals)
                fixture.home_win_prob = self._normalize_probability(fixture.home_win_prob)
                fixture.draw_prob = self._normalize_probability(fixture.draw_prob)
                fixture.away_win_prob = self._normalize_probability(fixture.away_win_prob)
                
                # Validate data
                if self._validate_fixture(fixture):
                    normalized_fixtures.append(fixture)
                else:
                    logger.warning(f"Fixture {fixture.id} failed validation, skipping")
                    
            except Exception as e:
                logger.warning(f"Failed to normalize fixture {fixture.id}: {e}")
                continue
        
        logger.info(f"Normalized {len(normalized_fixtures)} fixtures")
        return normalized_fixtures
    
    def _clean_player_name(self, name: str) -> str:
        """Clean player name"""
        if not name:
            return "Unknown Player"
        
        # Remove extra whitespace
        name = " ".join(name.split())
        
        # Handle common name variations
        name_mappings = {
            "Mohamed Salah": "Mohamed Salah",
            "Mo Salah": "Mohamed Salah",
            "Kevin De Bruyne": "Kevin De Bruyne",
            "KDB": "Kevin De Bruyne",
            "Erling Haaland": "Erling Haaland",
            "Harry Kane": "Harry Kane",
            "Son Heung-min": "Son Heung-min",
            "Heung-min Son": "Son Heung-min",
            "Bruno Fernandes": "Bruno Fernandes",
            "Bukayo Saka": "Bukayo Saka",
            "Marcus Rashford": "Marcus Rashford"
        }
        
        return name_mappings.get(name, name)
    
    def _clean_team_name(self, name: str) -> str:
        """Clean team name"""
        if not name:
            return "Unknown Team"
        
        # Remove extra whitespace
        name = " ".join(name.split())
        
        # Handle common team name variations
        team_mappings = {
            "Manchester United": "Man Utd",
            "Manchester City": "Man City",
            "Tottenham Hotspur": "Spurs",
            "Nottingham Forest": "Nott'm Forest",
            "Sheffield United": "Sheffield Utd"
        }
        
        return team_mappings.get(name, name)
    
    def _normalize_team_name(self, name: str) -> str:
        """Normalize team name to standard format"""
        return self._clean_team_name(name)
    
    def _normalize_team_short_name(self, name: str) -> str:
        """Normalize team short name"""
        if not name:
            return ""
        
        # Remove extra whitespace
        name = " ".join(name.split())
        
        # Handle common short name variations
        short_name_mappings = {
            "MUN": "Man Utd",
            "MCI": "Man City",
            "TOT": "Spurs",
            "NFO": "Nott'm Forest",
            "SHU": "Sheffield Utd"
        }
        
        return short_name_mappings.get(name, name)
    
    def _normalize_price(self, price: float) -> float:
        """Normalize player price"""
        if not isinstance(price, (int, float)) or price < 0:
            return 4.5  # Default minimum price
        
        # Ensure price is within reasonable bounds
        return max(4.0, min(15.0, price))
    
    def _normalize_form(self, form: float) -> float:
        """Normalize form rating"""
        if not isinstance(form, (int, float)):
            return 0.0
        
        # Ensure form is within reasonable bounds
        return max(-10.0, min(10.0, form))
    
    def _normalize_points_per_game(self, ppg: float) -> float:
        """Normalize points per game"""
        if not isinstance(ppg, (int, float)) or ppg < 0:
            return 0.0
        
        # Ensure PPG is within reasonable bounds
        return max(0.0, min(10.0, ppg))
    
    def _normalize_xg_xa(self, value: float) -> float:
        """Normalize xG/xA values"""
        if not isinstance(value, (int, float)) or value < 0:
            return 0.0
        
        # Ensure xG/xA is within reasonable bounds
        return max(0.0, min(2.0, value))
    
    def _normalize_playing_time(self, pct: float) -> float:
        """Normalize playing time percentage"""
        if not isinstance(pct, (int, float)) or pct < 0:
            return 1.0
        
        # Ensure percentage is between 0 and 1
        return max(0.0, min(1.0, pct))
    
    def _normalize_percentage(self, pct: float) -> float:
        """Normalize percentage values"""
        if not isinstance(pct, (int, float)) or pct < 0:
            return 0.0
        
        # Ensure percentage is within reasonable bounds
        return max(0.0, min(100.0, pct))
    
    def _normalize_strength(self, strength: int) -> int:
        """Normalize team strength"""
        if not isinstance(strength, int) or strength < 0:
            return 1000  # Default strength
        
        # Ensure strength is within reasonable bounds
        return max(800, min(1200, strength))
    
    def _normalize_difficulty(self, difficulty: int) -> int:
        """Normalize fixture difficulty"""
        if not isinstance(difficulty, int) or difficulty < 1:
            return 3  # Default difficulty
        
        # Ensure difficulty is between 1 and 5
        return max(1, min(5, difficulty))
    
    def _normalize_expected_goals(self, goals: float) -> float:
        """Normalize expected goals"""
        if not isinstance(goals, (int, float)) or goals < 0:
            return 2.5  # Default expected goals
        
        # Ensure expected goals is within reasonable bounds
        return max(0.0, min(5.0, goals))
    
    def _normalize_probability(self, prob: float) -> float:
        """Normalize probability values"""
        if not isinstance(prob, (int, float)) or prob < 0:
            return 0.33  # Default probability
        
        # Ensure probability is between 0 and 1
        return max(0.0, min(1.0, prob))
    
    def _normalize_injury_data(self, player: Player) -> Player:
        """Normalize injury data"""
        # Handle injury status
        if player.is_injured:
            # If injured but no return date, set a default
            if player.injury_expected_return is None:
                # Default to 2 weeks from now
                player.injury_expected_return = datetime.now() + timedelta(weeks=2)
            
            # Adjust playing time based on injury
            if player.injury_expected_return > datetime.now() + timedelta(weeks=1):
                player.xMins_pct = 0.0  # Out for more than a week
            else:
                player.xMins_pct = 0.5  # Doubtful
        
        return player
    
    def _validate_player(self, player: Player) -> bool:
        """Validate player data"""
        # Check required fields
        if not player.name or not player.team_name:
            return False
        
        # Note: Removed team filtering as we don't know the exact teams for 2025-26 season
        
        # Check numeric fields are reasonable
        if player.price < 4.0 or player.price > 15.0:
            return False
        
        if player.form < -10.0 or player.form > 10.0:
            return False
        
        if player.points_per_game < 0.0 or player.points_per_game > 10.0:
            return False
        
        return True
    
    def _validate_team(self, team: Team) -> bool:
        """Validate team data"""
        # Check required fields
        if not team.name:
            return False
        
        # Check numeric fields are reasonable
        if team.strength < 800 or team.strength > 1200:
            return False
        
        return True
    
    def _validate_fixture(self, fixture: Fixture) -> bool:
        """Validate fixture data"""
        # Check required fields
        if not fixture.home_team_name or not fixture.away_team_name:
            return False
        
        # Check difficulty is valid
        if fixture.difficulty < 1 or fixture.difficulty > 5:
            return False
        
        # Check probabilities sum to approximately 1
        prob_sum = fixture.home_win_prob + fixture.draw_prob + fixture.away_win_prob
        if abs(prob_sum - 1.0) > 0.1:
            return False
        
        return True
    
    def _get_default_team_xg(self, team_name: str) -> float:
        """Get default xG for a team based on historical performance"""
        # Realistic xG values based on typical Premier League team performance
        team_xg_defaults = {
            # Top teams (high scoring)
            'Man City': 2.1,
            'Arsenal': 1.9,
            'Liverpool': 1.8,
            'Spurs': 1.7,
            'Man Utd': 1.6,
            'Newcastle': 1.5,
            'Aston Villa': 1.4,
            'Chelsea': 1.4,
            'Brighton': 1.3,
            'Brentford': 1.2,
            # Mid-table teams
            'West Ham': 1.1,
            'Crystal Palace': 1.0,
            'Fulham': 1.0,
            'Wolves': 0.9,
            'Everton': 0.9,
            'Bournemouth': 0.8,
            'Burnley': 0.8,
            'Nott\'m Forest': 0.8,
            'Sunderland': 0.7,  # Newly promoted
            'Leeds': 0.7,  # Newly promoted
        }
        
        return team_xg_defaults.get(team_name, 1.0)  # Default to 1.0
    
    def _get_default_team_xga(self, team_name: str) -> float:
        """Get default xGA for a team based on historical performance"""
        # Realistic xGA values based on typical Premier League team performance
        team_xga_defaults = {
            # Top teams (good defense)
            'Man City': 0.8,
            'Arsenal': 0.9,
            'Liverpool': 1.0,
            'Spurs': 1.1,
            'Man Utd': 1.2,
            'Newcastle': 1.1,
            'Aston Villa': 1.2,
            'Chelsea': 1.3,
            'Brighton': 1.2,
            'Brentford': 1.3,
            # Mid-table teams
            'West Ham': 1.4,
            'Crystal Palace': 1.4,
            'Fulham': 1.5,
            'Wolves': 1.4,
            'Everton': 1.5,
            'Bournemouth': 1.6,
            'Burnley': 1.7,
            'Nott\'m Forest': 1.6,
            'Sunderland': 1.8,  # Newly promoted
            'Leeds': 1.8,  # Newly promoted
        }
        
        return team_xga_defaults.get(team_name, 1.4)  # Default to 1.4
