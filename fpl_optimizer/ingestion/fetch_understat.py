"""
Understat data fetcher for xG/xA statistics
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..models import Player
from ..config import Config


logger = logging.getLogger(__name__)


class UnderstatDataFetcher:
    """Fetches xG/xA data from Understat"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.get('api.understat_base_url', 'https://understat.com')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Team name mappings from FPL to Understat
        self.team_mappings = {
            'Arsenal': 'Arsenal',
            'Aston Villa': 'Aston Villa',
            'Bournemouth': 'Bournemouth',
            'Brentford': 'Brentford',
            'Brighton': 'Brighton',
            'Burnley': 'Burnley',
            'Chelsea': 'Chelsea',
            'Crystal Palace': 'Crystal Palace',
            'Everton': 'Everton',
            'Fulham': 'Fulham',
            'Liverpool': 'Liverpool',
            'Luton': 'Luton',
            'Man City': 'Manchester City',
            'Man Utd': 'Manchester United',
            'Newcastle': 'Newcastle United',
            'Nott\'m Forest': 'Nottingham Forest',
            'Sheffield Utd': 'Sheffield United',
            'Spurs': 'Tottenham',
            'West Ham': 'West Ham',
            'Wolves': 'Wolves'
        }
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to Understat API"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            raise
    
    def get_team_stats(self, team_name: str, season: int = 2024) -> Dict[str, Any]:
        """Get team statistics for a season"""
        logger.info(f"Fetching Understat team stats for {team_name} season {season}")
        
        # Map FPL team name to Understat team name
        understat_team_name = self.team_mappings.get(team_name, team_name)
        
        try:
            # This would require the actual Understat API endpoint
            # For now, return mock data
            return self._get_mock_team_stats(understat_team_name, season)
        except Exception as e:
            logger.error(f"Failed to get team stats for {team_name}: {e}")
            return {}
    
    def get_player_stats(self, player_name: str, team_name: str, season: int = 2024) -> Dict[str, Any]:
        """Get player statistics for a season"""
        logger.info(f"Fetching Understat player stats for {player_name} ({team_name}) season {season}")
        
        try:
            # This would require the actual Understat API endpoint
            # For now, return mock data
            return self._get_mock_player_stats(player_name, team_name, season)
        except Exception as e:
            logger.error(f"Failed to get player stats for {player_name}: {e}")
            return {}
    
    def get_league_stats(self, season: int = 2024) -> Dict[str, Any]:
        """Get Premier League statistics for a season"""
        logger.info(f"Fetching Understat league stats for season {season}")
        
        try:
            # This would require the actual Understat API endpoint
            # For now, return mock data
            return self._get_mock_league_stats(season)
        except Exception as e:
            logger.error(f"Failed to get league stats for season {season}: {e}")
            return {}
    
    def update_players_with_xg_xa(self, players: List[Player], season: int = 2024) -> List[Player]:
        """Update players with xG and xA data from Understat"""
        logger.info("Updating players with xG/xA data from Understat...")
        
        updated_players = []
        
        for player in players:
            try:
                # Get player stats from Understat
                stats = self.get_player_stats(player.name, player.team_name, season)
                
                if stats:
                    # Update player with xG/xA data
                    player.xG = stats.get('xG', 0.0)
                    player.xA = stats.get('xA', 0.0)
                    player.xGC = stats.get('xGC', 0.0)  # For defenders/GKs
                
                updated_players.append(player)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to update {player.name} with xG/xA data: {e}")
                updated_players.append(player)
                continue
        
        return updated_players
    
    def _get_mock_team_stats(self, team_name: str, season: int) -> Dict[str, Any]:
        """Get mock team statistics (placeholder for actual API)"""
        # This would be replaced with actual Understat API calls
        return {
            'team': team_name,
            'season': season,
            'xG': 45.2,
            'xGA': 35.8,
            'goals': 42,
            'goals_conceded': 38,
            'matches': 20
        }
    
    def _get_mock_player_stats(self, player_name: str, team_name: str, season: int) -> Dict[str, Any]:
        """Get mock player statistics (placeholder for actual API)"""
        # This would be replaced with actual Understat API calls
        # Generate some realistic mock data based on player name
        import hashlib
        
        # Use player name hash to generate consistent mock data
        name_hash = int(hashlib.md5(player_name.encode()).hexdigest()[:8], 16)
        
        # Generate realistic xG/xA based on position (would need actual position data)
        if any(name in player_name.lower() for name in ['kane', 'haaland', 'salah', 'son']):
            # Striker/attacker
            xG = 0.4 + (name_hash % 100) / 1000.0
            xA = 0.1 + (name_hash % 50) / 1000.0
        elif any(name in player_name.lower() for name in ['de bruyne', 'bruno', 'saka', 'rashford']):
            # Midfielder
            xG = 0.2 + (name_hash % 80) / 1000.0
            xA = 0.3 + (name_hash % 100) / 1000.0
        elif any(name in player_name.lower() for name in ['trent', 'robertson', 'cancelo']):
            # Attacking defender
            xG = 0.1 + (name_hash % 40) / 1000.0
            xA = 0.2 + (name_hash % 80) / 1000.0
        else:
            # Default
            xG = 0.05 + (name_hash % 30) / 1000.0
            xA = 0.05 + (name_hash % 30) / 1000.0
        
        return {
            'player': player_name,
            'team': team_name,
            'season': season,
            'xG': round(xG, 3),
            'xA': round(xA, 3),
            'xGC': 0.0,  # Would be calculated for defenders/GKs
            'goals': int(xG * 20),  # Rough conversion
            'assists': int(xA * 20),  # Rough conversion
            'matches': 15 + (name_hash % 10)
        }
    
    def _get_mock_league_stats(self, season: int) -> Dict[str, Any]:
        """Get mock league statistics (placeholder for actual API)"""
        return {
            'season': season,
            'league': 'Premier League',
            'teams': 20,
            'matches': 380,
            'avg_xG_per_match': 2.8,
            'avg_xGA_per_match': 2.8
        }
