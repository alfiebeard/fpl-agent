"""
FPL API data fetcher
"""

import requests
import json
import time
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..core.models import Player, Team, Fixture, Gameweek, Position
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
    
    def get_bootstrap_data(self) -> Dict[str, Any]:
        """Get bootstrap static data (players, teams, events)"""
        logger.info("Fetching FPL bootstrap data...")
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
                    name=player_data['first_name'] + ' ' + player_data['second_name'],
                    team_id=team_id,
                    position=position,
                    price=player_data['now_cost'] / 10.0,  # Convert from tenths
                    total_points=player_data['total_points'],
                    form=float(player_data.get('form', 0)),
                    points_per_game=float(player_data.get('points_per_game', 0)),
                    minutes_played=player_data.get('minutes', 0),
                    selected_by_pct=float(player_data.get('selected_by_percent', 0)),
                    price_change=(player_data.get('cost_change_start', 0) / 10.0),
                    is_injured=player_data.get('status') == 'i',
                    injury_type=player_data.get('news', ''),
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
    
    def parse_fixtures(self, fixtures_data: List[Dict[str, Any]], teams: List[Team]) -> List[Fixture]:
        """Parse fixtures from fixtures data"""
        fixtures = []
        
        # Create team ID to name mapping
        team_mapping = {team.id: team.name for team in teams}
        
        for fixture_data in fixtures_data:
            try:
                kickoff_time = None
                if fixture_data.get('kickoff_time'):
                    kickoff_time = datetime.fromisoformat(
                        fixture_data['kickoff_time'].replace('Z', '+00:00')
                    )
                
                # Get team names from mapping
                home_team_name = team_mapping.get(fixture_data['team_h'], 'Unknown Team')
                away_team_name = team_mapping.get(fixture_data['team_a'], 'Unknown Team')
                
                fixture = Fixture(
                    id=fixture_data['id'],
                    gameweek=fixture_data['event'],
                    home_team_id=fixture_data['team_h'],
                    away_team_id=fixture_data['team_a'],
                    home_team_name=home_team_name,
                    away_team_name=away_team_name,
                    difficulty=fixture_data.get('difficulty', 3),
                    home_difficulty=fixture_data.get('team_h_difficulty', 3),
                    away_difficulty=fixture_data.get('team_a_difficulty', 3),
                    kickoff_time=kickoff_time,
                    is_finished=fixture_data.get('finished', False),
                    home_score=fixture_data.get('team_h_score'),
                    away_score=fixture_data.get('team_a_score')
                )
                fixtures.append(fixture)
            except Exception as e:
                logger.warning(f"Failed to parse fixture {fixture_data.get('id')}: {e}")
                continue
        
        return fixtures
    
    def parse_gameweeks(self, bootstrap_data: Dict[str, Any]) -> List[Gameweek]:
        """Parse gameweeks from bootstrap data"""
        gameweeks = []
        
        for event_data in bootstrap_data.get('events', []):
            try:
                deadline_time = datetime.fromisoformat(
                    event_data['deadline_time'].replace('Z', '+00:00')
                )
                
                gameweek = Gameweek(
                    id=event_data['id'],
                    name=event_data['name'],
                    deadline_time=deadline_time,
                    is_finished=event_data.get('finished', False),
                    is_current=event_data.get('is_current', False),
                    is_next=event_data.get('is_next', False)
                )
                gameweeks.append(gameweek)
            except Exception as e:
                logger.warning(f"Failed to parse gameweek {event_data.get('id')}: {e}")
                continue
        
        return gameweeks
    
    def get_current_gameweek(self) -> Optional[int]:
        """Get the current gameweek number"""
        try:
            bootstrap_data = self.get_bootstrap_data()
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
            bootstrap_data = self.get_bootstrap_data()
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
        """Get all FPL data in one call"""
        logger.info("Fetching all FPL data...")
        
        try:
            bootstrap_data = self.get_bootstrap_data()
            fixtures_data = self.get_fixtures()
            
            # Parse teams first so we can use them for fixture parsing
            teams = self.parse_teams(bootstrap_data)
            
            return {
                'players': self.parse_players(bootstrap_data),
                'teams': teams,
                'fixtures': self.parse_fixtures(fixtures_data, teams),
                'gameweeks': self.parse_gameweeks(bootstrap_data),
                'current_gameweek': self.get_current_gameweek(),
                'next_deadline': self.get_next_deadline(),
                'raw_bootstrap': bootstrap_data,
                'raw_fixtures': fixtures_data
            }
        except Exception as e:
            logger.error(f"Failed to fetch all FPL data: {e}")
            raise
