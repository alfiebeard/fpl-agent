"""
FPL API data fetcher
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..core.models import Player, Team, Position
from ..core.config import Config


logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when FPL authentication fails"""
    pass


class FPLDataFetcher:
    """Fetches data from the FPL API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.get('api.fpl_base_url', 'https://fantasy.premierleague.com/api')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the FPL API"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data from {url}: {e}")
            raise
    
    def get_fpl_static_data(self) -> Dict[str, Any]:
        """Get FPL static reference data (players, teams, events)"""
        logger.info("Fetching FPL static data...")
        return self._make_request("bootstrap-static/")
    
    def get_fixtures(self) -> List[Dict[str, Any]]:
        """Get all fixtures"""
        logger.info("Fetching FPL fixtures...")
        return self._make_request("fixtures/")
    
    def get_gameweek_data(self, gameweek: int) -> Dict[str, Any]:
        """Get data for a specific gameweek"""
        logger.info(f"Fetching FPL gameweek {gameweek} data...")
        return self._make_request(f"event/{gameweek}/live/")
     
    def parse_players(self, bootstrap_data: Dict[str, Any]) -> List[Player]:
        """Parse players from bootstrap data"""
        players = []
        
        # Create team ID to name mapping
        team_mapping = {}
        for team_data in bootstrap_data.get('teams', []):
            team_mapping[team_data['id']] = {
                'name': team_data['name'],
                'short_name': team_data['short_name']
            }
        
        for player_data in bootstrap_data.get('elements', []):
            try:
                # Map FPL position IDs to our Position enum
                position_map = {1: Position.GK, 2: Position.DEF, 3: Position.MID, 4: Position.FWD}
                position = position_map.get(player_data['element_type'])
                if position is None:
                    logger.warning(f"Unknown position type {player_data['element_type']} for player {player_data['id']}")
                    continue
                
                # Get team info
                team_id = player_data['team']
                team_info = team_mapping.get(team_id, {'name': 'Unknown Team', 'short_name': 'UNK'})
                
                player = Player(
                    id=player_data['id'],
                    first_name=player_data['first_name'],
                    second_name=player_data['second_name'],
                    team_id=team_id,
                    element_type=player_data['element_type'],
                    now_cost=player_data['now_cost'],
                    total_points=player_data['total_points'],
                    form=player_data.get('form', '0.0'),
                    points_per_game=player_data.get('points_per_game', '0.0'),
                    minutes=player_data.get('minutes', 0),
                    selected_by_percent=player_data.get('selected_by_percent', '0.0'),
                    xG=player_data.get('xG', '0.00'),
                    xA=player_data.get('xA', '0.00'),
                    xGC=player_data.get('xGC', '0.00'),
                    xMins_pct=player_data.get('xMins_pct', 1.0),
                    status=player_data.get('status', 'a'),
                    news=player_data.get('news', ''),
                    news_added=player_data.get('news_added'),
                    chance_of_playing_next_round=player_data.get('chance_of_playing_next_round'),
                    chance_of_playing_this_round=player_data.get('chance_of_playing_this_round'),
                    cost_change_start=player_data.get('cost_change_start', 0),
                    cost_change_event=player_data.get('cost_change_event', 0),
                    team_name=team_info['name'],
                    team_short_name=team_info['short_name']
                )
                players.append(player)
            except Exception as e:
                logger.warning(f"Failed to parse player {player_data.get('id')}: {e}")
                continue
        
        return players
    
    def parse_teams(self, bootstrap_data: Dict[str, Any]) -> List[Team]:
        """Parse teams from bootstrap data"""
        teams = []
        
        for team_data in bootstrap_data.get('teams', []):
            try:
                team = Team(
                    id=team_data['id'],
                    name=team_data['name'],
                    short_name=team_data['short_name'],
                    strength=int(team_data.get('strength', 0) or 0),
                    form=float(team_data.get('form', 0) or 0)
                )
                teams.append(team)
            except Exception as e:
                logger.warning(f"Failed to parse team {team_data.get('id')}: {e}")
                continue
        
        return teams
    

    

    
    def get_current_gameweek(self) -> Optional[int]:
        """Get the current gameweek number"""
        try:
            bootstrap_data = self.get_fpl_static_data()
            events = bootstrap_data.get('events', [])
            
            for event in events:
                if event.get('is_current', False):
                    return event['id']
            
            # If no current gameweek found, return the first gameweek
            if events:
                return events[0]['id']
            
            return None
        except Exception as e:
            logger.error(f"Failed to get current gameweek: {e}")
            return None
    
    def get_next_deadline(self) -> Optional[datetime]:
        """Get the next deadline time"""
        try:
            bootstrap_data = self.get_fpl_static_data()
            events = bootstrap_data.get('events', [])
            
            for event in events:
                if event.get('is_next', False):
                    return datetime.fromisoformat(
                        event['deadline_time'].replace('Z', '+00:00')
                    )
            
            return None
        except Exception as e:
            logger.error(f"Failed to get next deadline: {e}")
            return None
    
    def get_all_data(self) -> Dict[str, Any]:
        """Get all FPL data (static data, fixtures, etc.)"""
        logger.info("Fetching all FPL data...")
        
        bootstrap_data = self.get_fpl_static_data()
        fixtures_data = self.get_fixtures()
        
        return {
            'fpl_static_data': bootstrap_data,
            'fixtures': fixtures_data
        }
    

    

