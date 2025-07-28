"""
FBRef data fetcher for additional statistics
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..models import Player, Team
from ..config import Config


logger = logging.getLogger(__name__)


class FBRefDataFetcher:
    """Fetches additional data from FBRef"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.get('api.fbref_base_url', 'https://fbref.com')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Team name mappings from FPL to FBRef
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
            'Spurs': 'Tottenham Hotspur',
            'West Ham': 'West Ham United',
            'Wolves': 'Wolves'
        }
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> str:
        """Make a request to FBRef"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            raise
    
    def get_team_stats(self, team_name: str, season: int = 2024) -> Dict[str, Any]:
        """Get team statistics for a season"""
        logger.info(f"Fetching FBRef team stats for {team_name} season {season}")
        
        # Map FPL team name to FBRef team name
        fbref_team_name = self.team_mappings.get(team_name, team_name)
        
        try:
            # This would require parsing the FBRef HTML
            # For now, return mock data
            return self._get_mock_team_stats(fbref_team_name, season)
        except Exception as e:
            logger.error(f"Failed to get team stats for {team_name}: {e}")
            return {}
    
    def get_player_stats(self, player_name: str, team_name: str, season: int = 2024) -> Dict[str, Any]:
        """Get player statistics for a season"""
        logger.info(f"Fetching FBRef player stats for {player_name} ({team_name}) season {season}")
        
        try:
            # This would require parsing the FBRef HTML
            # For now, return mock data
            return self._get_mock_player_stats(player_name, team_name, season)
        except Exception as e:
            logger.error(f"Failed to get player stats for {player_name}: {e}")
            return {}
    
    def get_injury_data(self, team_name: str) -> List[Dict[str, Any]]:
        """Get injury data for a team"""
        logger.info(f"Fetching FBRef injury data for {team_name}")
        
        try:
            # This would require parsing the FBRef injury page
            # For now, return mock data
            return self._get_mock_injury_data(team_name)
        except Exception as e:
            logger.error(f"Failed to get injury data for {team_name}: {e}")
            return []
    
    def update_players_with_fbref_data(self, players: List[Player], season: int = 2024) -> List[Player]:
        """Update players with additional data from FBRef"""
        logger.info("Updating players with FBRef data...")
        
        updated_players = []
        
        for player in players:
            try:
                # Get player stats from FBRef
                stats = self.get_player_stats(player.name, player.team_name, season)
                
                if stats:
                    # Update player with additional data
                    player.custom_data.update({
                        'passes_completed': stats.get('passes_completed', 0),
                        'passes_attempted': stats.get('passes_attempted', 0),
                        'key_passes': stats.get('key_passes', 0),
                        'dribbles_completed': stats.get('dribbles_completed', 0),
                        'tackles': stats.get('tackles', 0),
                        'interceptions': stats.get('interceptions', 0),
                        'clearances': stats.get('clearances', 0),
                        'blocks': stats.get('blocks', 0),
                        'fouls_committed': stats.get('fouls_committed', 0),
                        'fouls_drawn': stats.get('fouls_drawn', 0),
                        'yellow_cards': stats.get('yellow_cards', 0),
                        'red_cards': stats.get('red_cards', 0)
                    })
                
                updated_players.append(player)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to update {player.name} with FBRef data: {e}")
                updated_players.append(player)
                continue
        
        return updated_players
    
    def update_teams_with_fbref_data(self, teams: List[Team], season: int = 2024) -> List[Team]:
        """Update teams with additional data from FBRef"""
        logger.info("Updating teams with FBRef data...")
        
        updated_teams = []
        
        for team in teams:
            try:
                # Get team stats from FBRef
                stats = self.get_team_stats(team.name, season)
                
                if stats:
                    # Update team with additional data
                    team.custom_data.update({
                        'possession': stats.get('possession', 50.0),
                        'passes_completed': stats.get('passes_completed', 0),
                        'passes_attempted': stats.get('passes_attempted', 0),
                        'shots': stats.get('shots', 0),
                        'shots_on_target': stats.get('shots_on_target', 0),
                        'corners': stats.get('corners', 0),
                        'fouls_committed': stats.get('fouls_committed', 0),
                        'yellow_cards': stats.get('yellow_cards', 0),
                        'red_cards': stats.get('red_cards', 0)
                    })
                
                updated_teams.append(team)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to update {team.name} with FBRef data: {e}")
                updated_teams.append(team)
                continue
        
        return updated_teams
    
    def _get_mock_team_stats(self, team_name: str, season: int) -> Dict[str, Any]:
        """Get mock team statistics (placeholder for actual scraping)"""
        import hashlib
        
        # Use team name hash to generate consistent mock data
        name_hash = int(hashlib.md5(team_name.encode()).hexdigest()[:8], 16)
        
        return {
            'team': team_name,
            'season': season,
            'possession': 50.0 + (name_hash % 200) / 10.0,
            'passes_completed': 8000 + (name_hash % 4000),
            'passes_attempted': 9000 + (name_hash % 5000),
            'shots': 300 + (name_hash % 200),
            'shots_on_target': 100 + (name_hash % 100),
            'corners': 150 + (name_hash % 100),
            'fouls_committed': 200 + (name_hash % 100),
            'yellow_cards': 40 + (name_hash % 30),
            'red_cards': 1 + (name_hash % 3)
        }
    
    def _get_mock_player_stats(self, player_name: str, team_name: str, season: int) -> Dict[str, Any]:
        """Get mock player statistics (placeholder for actual scraping)"""
        import hashlib
        
        # Use player name hash to generate consistent mock data
        name_hash = int(hashlib.md5(player_name.encode()).hexdigest()[:8], 16)
        
        return {
            'player': player_name,
            'team': team_name,
            'season': season,
            'passes_completed': 500 + (name_hash % 300),
            'passes_attempted': 600 + (name_hash % 400),
            'key_passes': 20 + (name_hash % 30),
            'dribbles_completed': 30 + (name_hash % 50),
            'tackles': 40 + (name_hash % 60),
            'interceptions': 30 + (name_hash % 40),
            'clearances': 50 + (name_hash % 80),
            'blocks': 10 + (name_hash % 20),
            'fouls_committed': 15 + (name_hash % 25),
            'fouls_drawn': 20 + (name_hash % 30),
            'yellow_cards': 3 + (name_hash % 5),
            'red_cards': name_hash % 2
        }
    
    def _get_mock_injury_data(self, team_name: str) -> List[Dict[str, Any]]:
        """Get mock injury data (placeholder for actual scraping)"""
        import hashlib
        import random
        from datetime import datetime, timedelta
        
        # Use team name hash to generate consistent mock data
        name_hash = int(hashlib.md5(team_name.encode()).hexdigest()[:8], 16)
        
        # Generate 0-3 injuries per team
        num_injuries = name_hash % 4
        
        injuries = []
        for i in range(num_injuries):
            # Generate random injury duration (1-8 weeks)
            weeks_out = 1 + (name_hash + i) % 8
            expected_return = datetime.now() + timedelta(weeks=weeks_out)
            
            injury_types = ['Hamstring', 'Knee', 'Ankle', 'Groin', 'Calf', 'Shoulder']
            injury_type = injury_types[(name_hash + i) % len(injury_types)]
            
            injuries.append({
                'player_name': f"Player {i+1}",
                'team': team_name,
                'injury_type': injury_type,
                'expected_return': expected_return,
                'weeks_out': weeks_out,
                'status': 'Out' if weeks_out > 2 else 'Doubtful'
            })
        
        return injuries
