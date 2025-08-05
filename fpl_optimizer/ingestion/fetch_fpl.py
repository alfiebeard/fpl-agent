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
        """Get all FPL data (bootstrap, fixtures, etc.)"""
        logger.info("Fetching all FPL data...")
        
        bootstrap_data = self.get_bootstrap_data()
        fixtures_data = self.get_fixtures()
        
        return {
            'bootstrap': bootstrap_data,
            'fixtures': fixtures_data
        }
    
    def calculate_player_additional_stats(self, player: Player, fixtures: List[Fixture], 
                                        current_gameweek: int) -> Dict[str, Any]:
        """
        Calculate additional statistics for a player including upcoming fixture difficulty.
        
        Args:
            player: Player object
            fixtures: List of all fixtures
            current_gameweek: Current gameweek number
            
        Returns:
            Dictionary with additional player statistics
        """
        # Get basic stats that are already available
        stats = {
            "ppg": player.points_per_game,
            "form": player.form,
            "minutes_played": player.minutes_played,
            "ownership_percent": player.selected_by_pct
        }
        
        # Calculate upcoming fixture difficulty
        upcoming_fixture_difficulty = self._calculate_upcoming_fixture_difficulty(
            player, fixtures, current_gameweek
        )
        stats["upcoming_fixture_difficulty"] = upcoming_fixture_difficulty
        
        return stats
    
    def _calculate_upcoming_fixture_difficulty(self, player: Player, fixtures: List[Fixture], 
                                             current_gameweek: int) -> float:
        """
        Calculate weighted upcoming fixture difficulty for the next 5 gameweeks.
        
        Args:
            player: Player object
            fixtures: List of all fixtures
            current_gameweek: Current gameweek number
            
        Returns:
            Weighted average fixture difficulty (1-5 scale, lower is easier)
        """
        # Get upcoming fixtures for the player's team (next 5 gameweeks)
        upcoming_fixtures = []
        
        for fixture in fixtures:
            # Check if fixture is in the next 5 gameweeks and involves player's team
            if (fixture.gameweek > current_gameweek and 
                fixture.gameweek <= current_gameweek + 5 and
                (fixture.home_team_id == player.team_id or fixture.away_team_id == player.team_id)):
                
                upcoming_fixtures.append(fixture)
        
        if not upcoming_fixtures:
            # If no upcoming fixtures found, return neutral difficulty
            return 3.0
        
        # Sort fixtures by gameweek
        upcoming_fixtures.sort(key=lambda f: f.gameweek)
        
        # Calculate weighted difficulty
        # Weights: [0.4, 0.25, 0.2, 0.1, 0.05] for next 5 gameweeks
        weights = [0.4, 0.25, 0.2, 0.1, 0.05]
        total_weighted_difficulty = 0.0
        total_weight = 0.0
        
        for i, fixture in enumerate(upcoming_fixtures[:5]):  # Limit to 5 fixtures
            if i < len(weights):
                # Determine if player's team is home or away
                if fixture.home_team_id == player.team_id:
                    difficulty = fixture.home_difficulty
                else:
                    difficulty = fixture.away_difficulty
                
                weight = weights[i]
                total_weighted_difficulty += difficulty * weight
                total_weight += weight
        
        if total_weight == 0:
            return 3.0
        
        return round(total_weighted_difficulty / total_weight, 1)
    
    def get_players_with_additional_stats(self, bootstrap_data: Dict[str, Any], 
                                        fixtures_data: List[Dict[str, Any]]) -> List[Player]:
        """
        Get all players with additional statistics calculated.
        
        Args:
            bootstrap_data: Bootstrap data from FPL API
            fixtures_data: Fixtures data from FPL API
            
        Returns:
            List of Player objects with additional stats in custom_data
        """
        # Parse basic player data
        players = self.parse_players(bootstrap_data)
        fixtures = self.parse_fixtures(fixtures_data, self.parse_teams(bootstrap_data))
        current_gameweek = self.get_current_gameweek() or 1
        
        # Calculate additional stats for each player
        for player in players:
            additional_stats = self.calculate_player_additional_stats(
                player, fixtures, current_gameweek
            )
            player.custom_data.update(additional_stats)
        
        return players
    
    def get_all_data_with_additional_stats(self) -> Dict[str, Any]:
        """Get all FPL data with additional player statistics calculated"""
        logger.info("Fetching all FPL data with additional player statistics...")
        
        try:
            bootstrap_data = self.get_bootstrap_data()
            fixtures_data = self.get_fixtures()
            
            # Parse teams first so we can use them for fixture parsing
            teams = self.parse_teams(bootstrap_data)
            
            # Get players with additional stats
            players = self.get_players_with_additional_stats(bootstrap_data, fixtures_data)
            
            return {
                'players': players,
                'teams': teams,
                'fixtures': self.parse_fixtures(fixtures_data, teams),
                'gameweeks': self.parse_gameweeks(bootstrap_data),
                'current_gameweek': self.get_current_gameweek(),
                'next_deadline': self.get_next_deadline(),
                'raw_bootstrap': bootstrap_data,
                'raw_fixtures': fixtures_data
            }
        except Exception as e:
            logger.error(f"Failed to fetch all FPL data with additional stats: {e}")
            raise
