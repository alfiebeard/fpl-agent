"""
Understat data fetcher for xG/xA statistics
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..core.models import Player
from ..core.config import Config


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
            # TODO: Implement actual Understat API call
            # For now, raise error as mock data is not allowed
            raise NotImplementedError(f"Understat API not implemented. Cannot fetch team stats for {team_name}")
        except Exception as e:
            logger.error(f"Failed to get team stats for {team_name}: {e}")
            raise
    
    def get_player_stats(self, player_name: str, team_name: str, season: int = 2024) -> Dict[str, Any]:
        """Get player statistics for a season"""
        logger.info(f"Fetching Understat player stats for {player_name} ({team_name}) season {season}")
        
        try:
            # TODO: Implement actual Understat API call
            # For now, raise error as mock data is not allowed
            raise NotImplementedError(f"Understat API not implemented. Cannot fetch player stats for {player_name}")
        except Exception as e:
            logger.error(f"Failed to get player stats for {player_name}: {e}")
            raise
    
    def get_league_stats(self, season: int = 2024) -> Dict[str, Any]:
        """Get Premier League statistics for a season"""
        logger.info(f"Fetching Understat league stats for season {season}")
        
        try:
            # TODO: Implement actual Understat API call
            # For now, raise error as mock data is not allowed
            raise NotImplementedError(f"Understat API not implemented. Cannot fetch league stats for season {season}")
        except Exception as e:
            logger.error(f"Failed to get league stats for season {season}: {e}")
            raise
    
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
    

